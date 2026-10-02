"""Per-template solution blueprints — the LLM plans the steps once per
template, SymPy decides every value.

A *blueprint* is written offline, once per template (a registry structure
with ``{slot}`` parameters — see ``engine/topics/derivatives/structures.py``),
by an LLM (``scripts/generate_blueprints.py``). It is the template's
marking scheme: which sub-expressions to name (``definitions``: u, v, the
inner function, ...) and which intermediate results a student is expected
to write (``checkpoints``), in order, each with a label.

The LLM never supplies a value that is trusted. Every checkpoint declares a
*relation* — "the derivative of u", "the outer derivative t**n evaluated at
u", "the combination u_p*v - u*v_p" — and at grading time SymPy computes the
checkpoint's value from that relation on the question's own numbers. The
LLM's own worked value (``expr``) is only a cross-check used when the
blueprint is validated; a blueprint is accepted only if, on several random
instances of its template, SymPy agrees with every value the LLM wrote (see
`validate`). The final checkpoint is never from the blueprint at all: it is
the topic solver's own answer.

Expressions use SymPy syntax with ``x`` (the question's variable), the
template's slot names as bare symbols, and, inside a checkpoint's relation,
the names of definitions / earlier checkpoints / ``y`` (the given function).

Graded checkpoints must have *distinct values*: the grader and the points
rubric (``engine/core/rubric.py``) match a student's line to a checkpoint by
value, so a checkpoint equal to ``y``, to the final answer, or to another
checkpoint could never be told apart from it (a correct final line would be
claimed by the earlier step). `resolve` drops any that coincide on a given
instance; `validate` rejects a blueprint where they coincide structurally.

A template may have several *methods* — alternative valid solution paths
(splitting a log vs. the chain rule on it; expanding first vs. the product
rule), each a complete blueprint, the standard textbook method first. The
grader scores a student's whole work against every method and uses the one
it follows best (the topic's ``rubric.select_method``); lines no method predicts are
still judged true/false on their own (``grading._ClaimChecker``).

Relation handlers live in ``RELATIONS``: the calculus ones (derivative,
outer derivative), and the generic ones every topic can use — ``combination``
(an expression in what came before), ``substitute`` (evaluate an expression
at x = a point) and ``solve`` (solve equations for unknowns). A topic needing
another kind (an antiderivative, a limit, ...) registers it with `register`.

A topic whose question isn't one function ``y`` of ``x`` passes its givens as
a dict of names (``given={"A": ..., "B": ...}``, or ``{}``), and the extra
symbols its expressions may contain — an ODE's arbitrary constants ``C1``,
``C2`` and undetermined coefficients ``A``, ``B`` — as ``symbols``. A
checkpoint whose value still contains such a symbol (a general solution) is
flagged ``free_constants`` so the grader accepts the student's own constant
names (``A e^{2x} + B e^{3x}`` for ``C1 e^{2x} + C2 e^{3x}``).
"""
from __future__ import annotations

import json
import os
import random
import re
from typing import Callable

from sympy import Integral, Symbol, diff, integrate, latex, simplify, solve, sympify

_TOPICS_DIR = os.path.join(os.path.dirname(__file__), "..", "topics")
_T = Symbol("t")  # the outer function's variable in an outer_derivative relation

_CACHE: dict[str, dict] = {}


def blueprints_path(topic: str) -> str:
    return os.path.normpath(os.path.join(_TOPICS_DIR, topic, "data", "blueprints.json"))


def _normalize(entry) -> dict:
    """File entry -> {"methods": [blueprint, ...]}. A template has one or
    more *methods* (alternative valid solution paths, each a complete
    blueprint); the first is the standard textbook method. Single-method
    entries written before methods existed are read as a one-method list."""
    if "methods" in entry:
        return entry
    return {"methods": [{"method_id": "primary", "name_en": "Standard method", **entry}]}


def load(topic: str, force: bool = False) -> dict:
    """{template_id: {"methods": [blueprint, ...]}} for a topic ({} when it
    has none yet)."""
    if force or topic not in _CACHE:
        try:
            with open(blueprints_path(topic), encoding="utf-8") as f:
                _CACHE[topic] = {tid: _normalize(e) for tid, e in json.load(f).items()}
        except (OSError, json.JSONDecodeError):
            _CACHE[topic] = {}
    return _CACHE[topic]


def methods(topic: str, template_id: str | None) -> list[dict]:
    """The template's blueprints, standard method first ([] if none)."""
    entry = load(topic).get(template_id) if template_id else None
    return entry["methods"] if entry else []


# ---------------------------------------------------------------------------
# Relations: how a checkpoint's value is computed from what came before.
# ---------------------------------------------------------------------------

def _rel_derivative(cp, env, x, symbols):
    return diff(_parse(cp["of"], env, x, symbols), x)


def _rel_outer_derivative(cp, env, x, symbols):
    outer = _parse(cp["outer"], env, x, extra={**symbols, "t": _T})
    return diff(outer, _T).subs(_T, _parse(cp["at"], env, x, symbols))


def _rel_combination(cp, env, x, symbols):
    return _parse(cp["equals"], env, x, symbols)


def _rel_antiderivative(cp, env, x, symbols):
    """An antiderivative of `of` (no constant): SymPy's, or its rules-based
    integrator's when the default leaves an unevaluated integral."""
    integrand = _parse(cp["of"], env, x, symbols)
    value = integrate(integrand, x)
    if value.has(Integral):
        value = integrate(integrand, x, manual=True)
    if value.has(Integral):
        raise BlueprintError(f"no closed-form antiderivative of {integrand}")
    return value


def _rel_substitute(cp, env, x, symbols):
    """`of` evaluated at x = `at` (y(0), a general solution at x0, ...)."""
    return _parse(cp["of"], env, x, symbols).subs(x, _parse(cp["at"], env, x, symbols))


def _equation(text, env, x, symbols):
    lhs, eq, rhs = text.partition("=")
    left = _parse(lhs, env, x, symbols)
    return left - _parse(rhs, env, x, symbols) if eq else left


def _rel_solve(cp, env, x, symbols):
    """The value of the unknown `of` (one of the topic's symbols) from the
    equations in `equals` (";"-separated, each "lhs = rhs" or an expression
    = 0), solved together for every topic symbol they contain. An equation
    that must hold for every x (matching coefficients) is split into one
    equation per power of x / independent term."""
    unknown = symbols.get(str(cp.get("of", "")).strip())
    if unknown is None:
        raise BlueprintError(f"solve: {cp.get('of')!r} is not one of the unknowns {sorted(symbols)}")
    equations = []
    for part in str(cp.get("equals", "")).split(";"):
        if part.strip():
            equations.extend(_identity_equations(_equation(part, env, x, symbols), x))
    unknowns = sorted(set().union(*(e.free_symbols for e in equations)) & set(symbols.values()), key=str)
    if unknown not in unknowns:
        raise BlueprintError(f"solve: no equation contains {unknown}")
    solutions = solve(equations, unknowns, dict=True)
    if len(solutions) != 1 or unknown not in solutions[0]:
        raise BlueprintError(f"solve: {len(solutions)} solution(s) for {unknowns} from {cp.get('equals')!r}")
    value = simplify(solutions[0][unknown])
    if value.free_symbols & set(symbols.values()):
        raise BlueprintError(f"solve: {unknown} = {value} is not determined by the equations")
    return value


def _identity_equations(expr, x):
    """`expr = 0` for every x -> the equations on its independent parts (the
    coefficient of each power of x, of each cos/sin/exp term); a plain
    equation (no x) is itself."""
    # expand, never simplify: simplify may fold 2 sin x + 2 cos x into
    # 2*sqrt(2)*sin(x + pi/4), whose parts no longer separate.
    expr = expr.expand()
    if x not in expr.free_symbols:
        return [expr]
    terms = {}
    for term in expr.as_ordered_terms():
        coeff, rest = term.as_independent(x, as_Add=False)
        terms[rest] = terms.get(rest, 0) + coeff
    return [c for c in terms.values() if c != 0]


#: relation name -> handler(checkpoint, env, x, symbols) -> SymPy value.
#: "combination", "substitute" and "solve" are generic; the calculus
#: relations suit any topic whose steps are derivatives (derivatives,
#: function study, tangent lines, ...).
RELATIONS: dict[str, Callable] = {
    "derivative": _rel_derivative,
    "outer_derivative": _rel_outer_derivative,
    "antiderivative": _rel_antiderivative,
    "combination": _rel_combination,
    "substitute": _rel_substitute,
    "solve": _rel_solve,
}


def register(name: str, handler: Callable) -> None:
    """Add a topic's own relation kind: handler(checkpoint, env, x, symbols)."""
    RELATIONS[name] = handler


# ---------------------------------------------------------------------------
# Parsing an expression in a blueprint's own namespace.
# ---------------------------------------------------------------------------

class BlueprintError(ValueError):
    pass


def _parse(text, env, x, extra=None):
    """Parse `text` where every name must be x, a slot, a definition, an
    earlier checkpoint id or a given (all bound in `env`, already
    substituted), or one of the `extra` symbols (the topic's unknowns /
    arbitrary constants) — an unknown name is an error, never a
    silently-created free symbol."""
    if not isinstance(text, str) or not text.strip():
        raise BlueprintError("empty expression")
    local = {"x": x, **env, **(extra or {})}
    try:
        expr = sympify(text, locals=local)
    except Exception as e:  # noqa: BLE001 - any parse failure is a bad blueprint
        raise BlueprintError(f"cannot parse {text!r}: {e}") from e
    allowed = {x, *(v for v in (extra or {}).values() if isinstance(v, Symbol))}
    unknown = {s for s in expr.free_symbols if s not in allowed}
    if unknown:
        raise BlueprintError(f"unknown names {sorted(map(str, unknown))} in {text!r}")
    return expr


def _same_up_to_constant(a, b, x):
    from .grading import _equivalent_const

    return _equivalent_const(a, b, x)


def _same(a, b, x):
    # Lazy: grading -> dispatch -> topic solvers -> this module.
    from .grading import _equivalent_exact

    return a == b or _equivalent_exact(a, b, x)


# ---------------------------------------------------------------------------
# Instantiating a blueprint for one question.
# ---------------------------------------------------------------------------

def _given_env(given) -> dict:
    """The givens as names: a dict as is, one expression as ``y``."""
    if given is None:
        return {}
    return dict(given) if isinstance(given, dict) else {"y": given}


def evaluate(bp: dict, slot_values: dict, given, x, symbols=None) -> dict:
    """SymPy values of every definition and checkpoint for one instance.
    Returns {"definitions": {name: value}, "checkpoints": [(cp, value)],
    "labels": {cp id: LaTeX label with this instance's numbers},
    "subjects": {cp id: the expression it differentiates}} — labels and
    subjects only for derivative checkpoints (``(e^{-2 x})'``, ``y'``,
    ``y''``); the others keep the blueprint's generic label."""
    symbols = symbols or {}
    env = {name: sympify(val) for name, val in slot_values.items()}
    env.update(_given_env(given))
    given_y = env.get("y")
    definitions = {}
    for d in bp.get("definitions", []):
        value = _parse(d["expr"], env, x, symbols)
        definitions[d["name"]] = value
        env[d["name"]] = value
    checkpoints, labels, subjects = [], {"y": "y"}, {}
    for cp in bp.get("checkpoints", []):
        handler = RELATIONS.get(cp.get("relation"))
        if handler is None:
            raise BlueprintError(f"unknown relation {cp.get('relation')!r} in {cp.get('id')}")
        value = handler(cp, env, x, symbols)
        checkpoints.append((cp, value))
        env[cp["id"]] = value
        if cp.get("relation") == "derivative":
            of = str(cp.get("of", "")).strip()
            subjects[cp["id"]] = _parse(of, env, x, symbols)
            if of in labels:
                labels[cp["id"]] = labels[of] + "'"
            else:
                subject = subjects[cp["id"]]
                labels[cp["id"]] = "y'" if subject == given_y else rf"\left({latex(subject)}\right)'"
    labels.pop("y")
    return {"definitions": definitions, "checkpoints": checkpoints, "labels": labels, "subjects": subjects}


def _plan(bp, slot_values, given, final, x, formula, symbols, checkpoint_flags=None, final_flags=None):
    values = evaluate(bp, slot_values, given, x, symbols)
    seen = [*_given_env(given).values(), final]
    constants = set((symbols or {}).values())
    checkpoints = []
    for cp, value in values["checkpoints"]:
        if value == 0 or any(_same(value, s, x) for s in seen):
            continue  # 0, or coincides on this instance: can't be graded by value
        seen.append(value)
        free = sorted(str(s) for s in getattr(value, "free_symbols", set()) & constants)
        checkpoints.append({"label": cp.get("label_en") or cp["id"], "value": value, "formula": formula,
                            **({"label_latex": values["labels"][cp["id"]]} if cp["id"] in values["labels"] else {}),
                            **({"subject": values["subjects"][cp["id"]]} if cp["id"] in values["subjects"] else {}),
                            **({"free_constants": free} if free else {}),
                            **({"role": cp["role"]} if cp.get("role") else {}),
                            **(checkpoint_flags(cp) if checkpoint_flags else {})})
    # Aux: lines that are right wherever they appear without advancing the
    # step pointer — the definitions (u = ..., never flagged, never scored)
    # and the intermediate checkpoints again, since independent steps (u'
    # and v') are legitimately written in either order.
    aux = [{"label": name, "value": value, "formula": None}
           for name, value in values["definitions"].items()
           if not any(_same(value, s, x) for s in seen)]
    aux += [dict(cp) for cp in checkpoints]
    checkpoints.append({"label": "final answer", "value": final, "formula": formula, **(final_flags or {})})
    return {"checkpoints": checkpoints, "aux_checkpoints": aux}


def resolve(topic, template_id, slot_values, given, final, x, formula=None, symbols=None,
            checkpoint_flags=None, final_flags=None):
    """Grading plans for one question, one per method of its template's
    blueprint (standard method first), or [] when there is no usable
    blueprint — the caller keeps its own checkpoints then. Each plan is
    {"method", "name", "checkpoints", "aux_checkpoints"} in the shape
    ``analyze_work``/``build_rubric`` consume; every plan's last checkpoint
    is `final` (the solver's own answer). A method that fails to evaluate
    on this instance is skipped — a bad blueprint never breaks grading.
    `given`: one expression (``y``) or a dict of named givens; `symbols`:
    the topic's extra symbols ({name: Symbol}), see the module docstring.
    `checkpoint_flags(cp) -> dict` adds a topic's matching flags to a step
    (an antiderivative step is ``constant_ok``: any +C is right);
    `final_flags` likewise for the final answer."""
    if slot_values is None:
        return []
    plans = []
    for bp in methods(topic, template_id):
        try:
            plan = _plan(bp, slot_values, given, final, x, formula, symbols, checkpoint_flags, final_flags)
        except Exception:  # noqa: BLE001
            continue
        plans.append({"method": bp.get("method_id", "primary"), "name": bp.get("name_en", ""), **plan})
    return plans


# ---------------------------------------------------------------------------
# Validation — the gate every LLM-written blueprint must pass.
# ---------------------------------------------------------------------------

def validate(bp: dict, struct: dict, instantiate: Callable, truth: Callable,
             samples: int = 6, seed: int = 0, required: Callable | None = None,
             symbols: dict | None = None, given_env: Callable | None = None,
             expr_optional: bool = False, max_zero_share: float = 0.5) -> list[str]:
    """Problems with `bp` for `struct` (empty list = accepted), checked on
    `samples` random instances drawn from the structure's own sampler:

      - names: definitions/checkpoint ids are unique and never shadow a
        slot, x, y or t; every expression parses with only known names;
      - definitions: ``compose`` (an expression in the definitions)
        rebuilds y exactly;
      - checkpoints: every relation evaluates, and the LLM's own worked
        value (``expr``, written in x and the slots) equals SymPy's;
      - distinctness: no checkpoint equals y, the final answer, or an
        earlier checkpoint on most instances (it could never be graded);
      - `required(struct, bp, instance_values, x, y, final)` -> [problems], for
        topic-specific rules (e.g. a second derivative must show y').

    `instantiate(struct, slots)` builds y (or the question's params);
    `truth(struct, y, x)` is the topic's own final answer (never the
    blueprint's); `given_env(struct, y)` names the givens when they aren't
    just y (see `resolve`); `symbols` as in `resolve`. ``compose`` is only
    checked for a topic whose given is y. `expr_optional`: a checkpoint may
    leave its worked value ``expr`` empty (for a topic whose `required`
    checks what each step means, e.g. an ODE constant's value — a long
    formula an LLM easily gets wrong without the plan being wrong).
    `max_zero_share`: the share of samples a step may be 0 on (a 0 step is
    dropped on that instance; one that is 0 on most is useless) — a topic
    whose zeros depend on the instance (F(lower) with lower = 0 on some
    questions only) raises it."""
    problems: list[str] = []
    symbols = symbols or {}
    slots = set(_slot_names(struct))
    reserved = slots | {"x", "y", "t", "E"} | set(symbols)
    names = [d.get("name") for d in bp.get("definitions", [])] + [c.get("id") for c in bp.get("checkpoints", [])]
    for n in names:
        if not n or not str(n).isidentifier():
            problems.append(f"bad name {n!r}")
        elif n in reserved:
            problems.append(f"name {n!r} shadows a slot/x/y/t")
    if len(set(names)) != len(names):
        problems.append("duplicate definition/checkpoint names")
    if problems:
        return problems

    x = Symbol(struct.get("var", "x"))
    collisions = [0] * len(bp.get("checkpoints", []))
    zeros = [0] * len(bp.get("checkpoints", []))
    rng = random.Random(seed)
    for i in range(samples):
        _, slot_values = struct["sampler"](rng)
        where = f"sample {i} {slot_values}"
        y = instantiate(struct, slot_values)
        given = given_env(struct, y) if given_env else y
        final = truth(struct, y, x)
        try:
            values = evaluate(bp, slot_values, given, x, symbols)
        except Exception as e:  # noqa: BLE001
            return [f"{where}: {e}"]
        if values["definitions"] and "y" in _given_env(given):
            try:
                composed = _parse(bp.get("compose", ""), {**_slot_env(slot_values), **values["definitions"]}, x,
                                  symbols)
            except BlueprintError as e:
                return [f"{where}: compose: {e}"]
            target = _given_env(given)["y"]
            if not _same(composed, target, x):
                return [f"{where}: compose {bp.get('compose')!r} = {composed}, but y = {target}"]
        seen = [*_given_env(given).values(), final]
        for j, (cp, value) in enumerate(values["checkpoints"]):
            if expr_optional and not str(cp.get("expr") or "").strip():
                claimed = value
            else:
                try:
                    # The givens other than y (an integral's bounds lo/hi) may appear;
                    # y may not, or "expr": "y" would check nothing.
                    named = {k: v for k, v in _given_env(given).items() if k != "y"}
                    claimed = _parse(cp.get("expr", ""), {**_slot_env(slot_values), **named}, x, symbols)
                except BlueprintError as e:
                    return [f"{where}: checkpoint {cp['id']}: expr: {e}"]
            # An antiderivative is only defined up to a constant.
            if not (_same(claimed, value, x) or cp.get("relation") == "antiderivative"
                    and _same_up_to_constant(claimed, value, x)):
                return [f"{where}: checkpoint {cp['id']} ({cp.get('relation')}): "
                        f"LLM wrote {claimed}, SymPy gives {value}"]
            if value == 0:
                zeros[j] += 1
            elif any(_same(value, s, x) for s in seen):
                collisions[j] += 1
            seen.append(value)
        if required:
            extra = required(struct, bp, values, x, y, final)
            if extra:
                return [f"{where}: {p}" for p in extra]
    for j, n in enumerate(zeros):
        if n > samples * max_zero_share:
            problems.append(f"checkpoint {bp['checkpoints'][j]['id']} is 0 on {n}/{samples} samples "
                            f"(e.g. the derivative of a constant) — it earns no marks and any stray "
                            f"'= 0' line would match it")
    for j, n in enumerate(collisions):
        if n * 2 > samples:
            cp = bp["checkpoints"][j]
            problems.append(f"checkpoint {cp['id']} equals y, the final answer or an earlier "
                            f"checkpoint on {n}/{samples} samples — not gradable by value")
    return problems


def _slot_names(struct):
    """A structure's slots: its own ``slots`` list when it has one (a pattern
    may hold placeholders that aren't slots, like integral's ``{v}``), else
    every ``{name}`` in its pattern."""
    if struct.get("slots") is not None:
        return list(struct["slots"])
    return list(dict.fromkeys(re.findall(r"\{(\w+)\}", struct["pattern"])))


def _slot_env(slot_values):
    return {k: sympify(v) for k, v in slot_values.items()}


def same_plan(bp_a: dict, bp_b: dict, struct: dict, instantiate: Callable, seed: int = 7,
              symbols: dict | None = None, given_env: Callable | None = None) -> bool:
    """True when two methods ask for the same intermediate values (on a
    random instance) — i.e. one isn't really an alternative to the other."""
    x = Symbol(struct.get("var", "x"))
    _, slot_values = struct["sampler"](random.Random(seed))
    y = instantiate(struct, slot_values)
    given = given_env(struct, y) if given_env else y
    a = [v for _, v in evaluate(bp_a, slot_values, given, x, symbols)["checkpoints"]]
    b = [v for _, v in evaluate(bp_b, slot_values, given, x, symbols)["checkpoints"]]
    return all(any(_same(v, w, x) for w in a) for v in b)


def save(topic: str, blueprints: dict) -> None:
    path = blueprints_path(topic)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(blueprints.items())), f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    _CACHE[topic] = blueprints
