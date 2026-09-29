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

Relation handlers are registered per topic (``RELATIONS``), so a new topic
adds its own relation kinds (an antiderivative, a limit, ...) without
touching this module.
"""
from __future__ import annotations

import json
import os
import random
import re
from typing import Callable

from sympy import Symbol, diff, sympify

_TOPICS_DIR = os.path.join(os.path.dirname(__file__), "..", "topics")
_T = Symbol("t")  # the outer function's variable in an outer_derivative relation

_CACHE: dict[str, dict] = {}


def blueprints_path(topic: str) -> str:
    return os.path.normpath(os.path.join(_TOPICS_DIR, topic, "data", "blueprints.json"))


def load(topic: str, force: bool = False) -> dict:
    """{template_id: blueprint} for a topic ({} when it has none yet)."""
    if force or topic not in _CACHE:
        try:
            with open(blueprints_path(topic), encoding="utf-8") as f:
                _CACHE[topic] = json.load(f)
        except (OSError, json.JSONDecodeError):
            _CACHE[topic] = {}
    return _CACHE[topic]


def get(topic: str, template_id: str | None) -> dict | None:
    return load(topic).get(template_id) if template_id else None


# ---------------------------------------------------------------------------
# Relations: how a checkpoint's value is computed from what came before.
# ---------------------------------------------------------------------------

def _rel_derivative(cp, env, x):
    return diff(_parse(cp["of"], env, x), x)


def _rel_outer_derivative(cp, env, x):
    outer = _parse(cp["outer"], env, x, extra={"t": _T})
    return diff(outer, _T).subs(_T, _parse(cp["at"], env, x))


def _rel_combination(cp, env, x):
    return _parse(cp["equals"], env, x)


#: relation name -> handler(checkpoint, env, x) -> SymPy value.
#: "combination" is generic; the calculus relations suit any topic whose
#: steps are derivatives (derivatives, function study, tangent lines, ...).
RELATIONS: dict[str, Callable] = {
    "derivative": _rel_derivative,
    "outer_derivative": _rel_outer_derivative,
    "combination": _rel_combination,
}


# ---------------------------------------------------------------------------
# Parsing an expression in a blueprint's own namespace.
# ---------------------------------------------------------------------------

class BlueprintError(ValueError):
    pass


def _parse(text, env, x, extra=None):
    """Parse `text` where every name must be x, a slot, a definition, an
    earlier checkpoint id or y (all bound in `env`, already substituted) —
    an unknown name is an error, never a silently-created free symbol."""
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


def _same(a, b, x):
    # Lazy: grading -> dispatch -> topic solvers -> this module.
    from .grading import _equivalent_exact

    return a == b or _equivalent_exact(a, b, x)


# ---------------------------------------------------------------------------
# Instantiating a blueprint for one question.
# ---------------------------------------------------------------------------

def evaluate(bp: dict, slot_values: dict, given, x) -> dict:
    """SymPy values of every definition and checkpoint for one instance.
    Returns {"definitions": {name: value}, "checkpoints": [(cp, value)]}."""
    env = {name: sympify(val) for name, val in slot_values.items()}
    env["y"] = given
    definitions = {}
    for d in bp.get("definitions", []):
        value = _parse(d["expr"], env, x)
        definitions[d["name"]] = value
        env[d["name"]] = value
    checkpoints = []
    for cp in bp.get("checkpoints", []):
        handler = RELATIONS.get(cp.get("relation"))
        if handler is None:
            raise BlueprintError(f"unknown relation {cp.get('relation')!r} in {cp.get('id')}")
        value = handler(cp, env, x)
        checkpoints.append((cp, value))
        env[cp["id"]] = value
    return {"definitions": definitions, "checkpoints": checkpoints}


def resolve(topic, template_id, slot_values, given, final, x, formula=None):
    """Grading data for one question from its template's blueprint, or None
    when there is no (usable) blueprint — the caller keeps its own
    checkpoints then. Returns {"checkpoints": [...], "aux_checkpoints":
    [...]} in the shape ``analyze_work``/``build_rubric`` consume; the last
    checkpoint is always `final` (the solver's own answer)."""
    bp = get(topic, template_id)
    if not bp or slot_values is None:
        return None
    try:
        values = evaluate(bp, slot_values, given, x)
    except Exception:  # noqa: BLE001 - a bad blueprint must never break grading
        return None
    seen = [given, final]
    checkpoints = []
    for cp, value in values["checkpoints"]:
        if any(_same(value, s, x) for s in seen):
            continue  # coincides on this instance: can't be graded by value
        seen.append(value)
        checkpoints.append({"label": cp.get("label_en") or cp["id"], "value": value, "formula": formula})
    # Aux: lines that are right wherever they appear without advancing the
    # step pointer — the definitions (u = ..., never flagged, never scored)
    # and the intermediate checkpoints again, since independent steps (u'
    # and v') are legitimately written in either order.
    aux = [{"label": name, "value": value, "formula": None}
           for name, value in values["definitions"].items()
           if not any(_same(value, s, x) for s in seen)]
    aux += [dict(cp) for cp in checkpoints]
    checkpoints.append({"label": "final answer", "value": final, "formula": formula})
    return {"checkpoints": checkpoints, "aux_checkpoints": aux}


# ---------------------------------------------------------------------------
# Validation — the gate every LLM-written blueprint must pass.
# ---------------------------------------------------------------------------

def validate(bp: dict, struct: dict, instantiate: Callable, truth: Callable,
             samples: int = 6, seed: int = 0, required: Callable | None = None) -> list[str]:
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

    `instantiate(struct, slots)` builds y; `truth(struct, y, x)` is the
    topic's own final answer (never the blueprint's)."""
    problems: list[str] = []
    slots = set(_slot_names(struct))
    reserved = slots | {"x", "y", "t", "E"}
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
    rng = random.Random(seed)
    for i in range(samples):
        _, slot_values = struct["sampler"](rng)
        where = f"sample {i} {slot_values}"
        y = instantiate(struct, slot_values)
        final = truth(struct, y, x)
        try:
            values = evaluate(bp, slot_values, y, x)
        except Exception as e:  # noqa: BLE001
            return [f"{where}: {e}"]
        if values["definitions"]:
            try:
                composed = _parse(bp.get("compose", ""), {**_slot_env(slot_values), **values["definitions"]}, x)
            except BlueprintError as e:
                return [f"{where}: compose: {e}"]
            if not _same(composed, y, x):
                return [f"{where}: compose {bp.get('compose')!r} = {composed}, but y = {y}"]
        seen = [y, final]
        for j, (cp, value) in enumerate(values["checkpoints"]):
            try:
                claimed = _parse(cp.get("expr", ""), _slot_env(slot_values), x)
            except BlueprintError as e:
                return [f"{where}: checkpoint {cp['id']}: expr: {e}"]
            if not _same(claimed, value, x):
                return [f"{where}: checkpoint {cp['id']} ({cp.get('relation')}): "
                        f"LLM wrote {claimed}, SymPy gives {value}"]
            if any(_same(value, s, x) for s in seen):
                collisions[j] += 1
            seen.append(value)
        if required:
            extra = required(struct, bp, values, x, y, final)
            if extra:
                return [f"{where}: {p}" for p in extra]
    for j, n in enumerate(collisions):
        if n * 2 > samples:
            cp = bp["checkpoints"][j]
            problems.append(f"checkpoint {cp['id']} equals y, the final answer or an earlier "
                            f"checkpoint on {n}/{samples} samples — not gradable by value")
    return problems


def _slot_names(struct):
    return list(dict.fromkeys(re.findall(r"\{(\w+)\}", struct["pattern"])))


def _slot_env(slot_values):
    return {k: sympify(v) for k, v in slot_values.items()}


def save(topic: str, blueprints: dict) -> None:
    path = blueprints_path(topic)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(blueprints.items())), f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    _CACHE[topic] = blueprints
