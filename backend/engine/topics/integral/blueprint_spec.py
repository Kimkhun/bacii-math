"""What an LLM needs to write, and SymPy needs to check, an integral
blueprint (see ``engine/core/blueprints.py`` for the format and the
validation gate). Consumed by ``scripts/generate_blueprints.py``.

The givens are the integrand ``y`` and, for a definite integral, the bounds
``lo`` and ``hi`` (a template's bounds are drawn per question from a list, so
a blueprint names them rather than writing numbers). A substitution or an
integration by parts is declared as definitions (u; u and dv) whose
``compose`` must rebuild the integrand — the proof that the substitution
really applies. Each checkpoint has a ``role`` that `required` verifies on
every sampled instance:

  antiderivative        F with F' = the integrand
  term_antiderivative   an antiderivative of one term; together the term
                        steps must cover the whole integrand
  bound_value           F(hi) or F(lo) for the blueprint's own F
  new_bound             a substitution's u at lo or hi
  derived               a derivative / antiderivative / substitution of an
                        earlier step, or arithmetic of earlier steps only
                        (u*v - w), never a free-form expression

The final answer is never the blueprint's: it is the solver's own.
"""
import re

from sympy import Symbol, diff, simplify, sympify

from .solver import _solve_definite_integral, _solve_indefinite_integral
from .structures import _LOCALS, _SLOT_NAMES, instantiate, slot_names

TOPIC = "integral"
FORMULA = "fundamental_theorem"

_ROLES = ("antiderivative", "term_antiderivative", "bound_value", "new_bound", "derived")
_DEF = "definite_integral"

#: Validation samples draw the bounds too, so F(lo) = 0 on the questions
#: whose lower bound is 0 — only a step that is 0 on nearly all is useless.
MAX_ZERO_SHARE = 0.8


def _sym(text, var):
    return sympify(str(text), locals={var: Symbol(var), **_LOCALS})


def truth(struct, params, x):
    """The final answer — the solver's own, never the blueprint's."""
    solve = _solve_definite_integral if struct["question_type"] == _DEF else _solve_indefinite_integral
    return solve(params)["answer_exact"]


def given_env(struct, params):
    var = params["var"]
    env = {"y": _sym(params["expr"], var)}
    if struct["question_type"] == _DEF:
        env["lo"] = _sym(params["lower"], var)
        env["hi"] = _sym(params["upper"], var)
    return env


def _zero(expr):
    try:
        return simplify(expr) == 0
    except Exception:  # noqa: BLE001
        return False


_NAME = re.compile(r"[A-Za-z_]\w*")


def required(struct, bp, values, x, params, final):
    """Every checkpoint means what its role says, on this instance."""
    env = given_env(struct, params)
    y = env["y"]
    definite = struct["question_type"] == _DEF
    defs = values["definitions"]
    problems, antiderivatives, terms, earlier = [], [], [], set(defs)
    pending_bounds = []
    for cp, value in values["checkpoints"]:
        role, cid = cp.get("role"), cp.get("id")
        if role not in _ROLES:
            problems.append(f"checkpoint {cid}: unknown role {role!r}")
        elif role == "antiderivative":
            if not _zero(diff(value, x) - y):
                problems.append(f"checkpoint {cid} = {value} is not an antiderivative of the integrand "
                                f"(its derivative is {simplify(diff(value, x))})")
            antiderivatives.append(value)
        elif role == "term_antiderivative":
            terms.append((cid, value))
        elif role == "bound_value":
            if not definite:
                problems.append(f"checkpoint {cid}: bound_value in an indefinite integral")
            else:
                pending_bounds.append((cid, value))
        elif role == "new_bound":
            if not definite or not any(_zero(value - d.subs(x, b)) for d in defs.values()
                                       for b in (env["lo"], env["hi"])):
                problems.append(f"checkpoint {cid} = {value} is not a definition (u) at lo or hi")
        elif role == "derived":
            relation = cp.get("relation")
            if relation == "combination":
                names = set(_NAME.findall(str(cp.get("equals", ""))))
                stray = names - earlier
                if stray or re.search(r"\d", str(cp.get("equals", ""))):
                    problems.append(f"checkpoint {cid}: a 'derived' combination may only combine earlier steps "
                                    f"and definitions by name (found {sorted(stray) or 'a number'})")
            elif relation not in ("derivative", "antiderivative", "substitute"):
                problems.append(f"checkpoint {cid}: a 'derived' step is a derivative, an antiderivative, a "
                                f"substitution or a combination of earlier steps")
        earlier.add(cid)
    if problems:
        return problems
    if terms:
        total = sum(v for _, v in terms)
        if not _zero(diff(total, x) - y):
            problems.append(f"the term antiderivatives {[c for c, _ in terms]} don't add up to an antiderivative "
                            f"of the integrand (their derivatives sum to {simplify(diff(total, x))})")
        antiderivatives.append(total)
    for cid, value in pending_bounds:
        if not any(_zero(value - F.subs(x, b)) for F in antiderivatives for b in (env["lo"], env["hi"])):
            problems.append(f"checkpoint {cid} = {value} is not the blueprint's antiderivative at lo or hi"
                            + ("" if antiderivatives else " (grade the antiderivative F itself first)"))
    if definite and not antiderivatives:
        problems.append("a definite-integral blueprint must grade the antiderivative (role antiderivative, or "
                        "term antiderivatives covering the integrand)")
    return problems


def validate(bp, struct, samples=6, seed=0):
    from ...core import blueprints

    return blueprints.validate(bp, struct, instantiate, truth, samples=samples, seed=seed, required=required,
                               given_env=given_env, max_zero_share=MAX_ZERO_SHARE)


def _slot_text(text, var="x"):
    out = text.replace("{v}", var)
    for slot in _SLOT_NAMES:
        out = out.replace("{" + slot + "}", slot)
    return out


def template_brief(struct):
    """How one template is presented to the LLM (always in the variable x)."""
    brief = {
        "template_id": struct["id"],
        "integrand": "y = " + _slot_text(struct["pattern"]),
        "slots": slot_names(struct),
        "technique": struct["variant"],
    }
    if struct["question_type"] == _DEF:
        brief["integral"] = "definite, from x = lo to x = hi"
        brief["bounds"] = sorted({f"lo = {_slot_text(lo)}, hi = {_slot_text(hi)}" for lo, hi in struct["bounds"]})
    else:
        brief["integral"] = "indefinite (the final answer F + C is graded automatically)"
    return brief


_STRING = {"type": "STRING"}

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "templates": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "template_id": _STRING,
                    "definitions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {"name": _STRING, "expr": _STRING},
                            "required": ["name", "expr"],
                        },
                    },
                    "compose": _STRING,
                    "checkpoints": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "id": _STRING,
                                "role": {"type": "STRING", "enum": list(_ROLES)},
                                "relation": {"type": "STRING",
                                             "enum": ["antiderivative", "derivative", "substitute", "combination"]},
                                "of": _STRING,
                                "at": _STRING,
                                "equals": _STRING,
                                "expr": _STRING,
                                "label_en": _STRING,
                                "label_km": _STRING,
                            },
                            "required": ["id", "role", "relation", "of", "at", "equals", "expr", "label_en",
                                         "label_km"],
                        },
                    },
                },
                "required": ["template_id", "definitions", "compose", "checkpoints"],
            },
        }
    },
    "required": ["templates"],
}

PROMPT = r"""You are a senior Grade 12 Cambodian BAC II mathematics examiner writing the official
MARKING SCHEME for integration exercises. Each exercise below is a TEMPLATE: an integrand y in x
whose numbers are positive parameters (slots), integrated indefinitely or from x = lo to x = hi
(the bounds are given by NAME, lo and hi, because each question draws them from the list shown).
Write one blueprint per template that works for ANY slot values and any listed bounds.

A blueprint lists the results a marker awards points for (checkpoints), in the order a student
writes them. You are NOT computing a numeric answer; a computer algebra system recomputes every
value from your relations on each question's own numbers, and checks that each checkpoint really
is what its role says.

EXPRESSION SYNTAX (strict, SymPy):
- x is the variable. Slots are plain symbols. Use * for every product, ** for powers.
- exp(...) (never e**...), log(...) for ln, sqrt(...), sin, cos, tan, pi.
- y is the integrand; lo and hi are the bounds (definite integrals only).
- diff(E, x) is E'; E.subs(x, lo) is E at x = lo.

DEFINITIONS: named pieces of the method, never graded on their own.
- u-substitution: {"name": "u", "expr": <inner function>}, and "compose" rebuilds y from u, e.g.
  "diff(u, x)*u**n" or "a/(2*b)*diff(u, x)*u**n" (constant factors as needed).
- integration by parts: {"name": "u", ...} and {"name": "dv", ...} with compose "u*dv".
- Names: u, dv, w, g, h (never a slot name, x, y, t, lo, hi). No definitions: [] and compose "".

CHECKPOINTS: each has an id (short identifier), a role, a relation, expr and labels.
Relations (unused fields are ""):
- "antiderivative": an antiderivative (no +C) of `of` (an expression in x, slots, definition names,
  earlier checkpoint ids, y).
- "derivative": the derivative of `of`.
- "substitute": `of` evaluated at x = `at` (e.g. at "lo" or "hi").
- "combination": `equals`, an expression in slots, x, definitions, earlier checkpoint ids.
Roles:
- "term_antiderivative": the antiderivative of ONE term of the (expanded or split) integrand.
  Together, the term steps must add up to an antiderivative of the whole integrand.
- "antiderivative": F, an antiderivative of the whole integrand (definite integrals).
- "bound_value": F(hi) or F(lo) — relation "substitute" of your F checkpoint (or of the sum of the
  term steps, written as a combination of their ids) at "hi"/"lo".
- "new_bound": in a substitution, u at lo or hi (relation "substitute", of "u").
- "derived": du (derivative of u), v (antiderivative of dv), v*du's antiderivative, or
  arithmetic of earlier step ids only (e.g. "uv - w"; no slots, numbers or x in it).
expr: YOUR explicit value of the checkpoint written ONLY in x, the slots, lo and hi.
label_en / label_km: short labels, e.g. "∫3x² dx", "u", "du", "F(x)", "F(hi)", "u(lo)", "v";
label_km in Khmer keeping the math (e.g. "ព្រីមីទីវ F(x)", "តម្លៃ F ត្រង់ hi").

MARKING RULES:
1. Never include the final answer: for an indefinite integral the whole antiderivative IS the
   final answer (only its separate terms are steps); for a definite one, F(hi) - F(lo) is.
2. Every checkpoint must have a different value. No checkpoint equal to the integrand y.
3. Rewriting steps (expanding a product, splitting a fraction) equal the integrand, so they are
   NOT checkpoints: grade the antiderivative of each resulting term instead.
4. A sum of terms: one term_antiderivative per term (a constant term k gives k*x).
5. Definite integrals: grade F (or the term steps), F(hi), and F(lo) — but leave out a value that
   is 0 for almost every listed bound (F(lo) when lo is always 0 and F(0) = 0; then F(hi) equals
   the final answer, so leave it out too).
6. Write F in the form a student writes it: for a substitution, F = an expression in u (relation
   "combination", e.g. "u**(n + 1)/(n + 1)", "log(u)"), not the expanded antiderivative; for by
   parts, "uv - w". Relation "antiderivative" is for a single simple term or piece (v from dv).
7. u-substitution: define u (compose rebuilds y), grade du, and for a definite integral the new
   bounds u(lo), u(hi), then F and its bound values. Integration by parts: define u and dv,
   grade du, v, u*v, the antiderivative of v*du, then F = u*v - that antiderivative.
8. A single basic term (an indefinite a*sin(k*x)) may have [] checkpoints.

EXAMPLES:

Template: y = (a*x + b)*(c*x - d), indefinite, slots [a, b, c, d]
{"template_id": "integral:expand_3",
 "definitions": [], "compose": "",
 "checkpoints": [
  {"id": "t3", "role": "term_antiderivative", "relation": "antiderivative", "of": "a*c*x**2", "at": "", "equals": "", "expr": "a*c*x**3/3", "label_en": "∫acx² dx", "label_km": "∫acx² dx"},
  {"id": "t2", "role": "term_antiderivative", "relation": "antiderivative", "of": "(b*c - a*d)*x", "at": "", "equals": "", "expr": "(b*c - a*d)*x**2/2", "label_en": "∫(bc - ad)x dx", "label_km": "∫(bc - ad)x dx"},
  {"id": "t1", "role": "term_antiderivative", "relation": "antiderivative", "of": "-b*d", "at": "", "equals": "", "expr": "-b*d*x", "label_en": "∫-bd dx", "label_km": "∫-bd dx"}]}

Template: y = 2*x*(x**2 + c)**n, definite from lo to hi, bounds [lo = 0, hi = 1], slots [c, n]
{"template_id": "integral:def_usub_power2",
 "definitions": [{"name": "u", "expr": "x**2 + c"}], "compose": "diff(u, x)*u**n",
 "checkpoints": [
  {"id": "du", "role": "derived", "relation": "derivative", "of": "u", "at": "", "equals": "", "expr": "2*x", "label_en": "du/dx", "label_km": "du/dx"},
  {"id": "u_lo", "role": "new_bound", "relation": "substitute", "of": "u", "at": "lo", "equals": "", "expr": "lo**2 + c", "label_en": "u(lo)", "label_km": "u ត្រង់ lo"},
  {"id": "u_hi", "role": "new_bound", "relation": "substitute", "of": "u", "at": "hi", "equals": "", "expr": "hi**2 + c", "label_en": "u(hi)", "label_km": "u ត្រង់ hi"},
  {"id": "F", "role": "antiderivative", "relation": "combination", "of": "", "at": "", "equals": "u**(n + 1)/(n + 1)", "expr": "(x**2 + c)**(n + 1)/(n + 1)", "label_en": "F(x)", "label_km": "ព្រីមីទីវ F(x)"},
  {"id": "F_hi", "role": "bound_value", "relation": "substitute", "of": "F", "at": "hi", "equals": "", "expr": "(hi**2 + c)**(n + 1)/(n + 1)", "label_en": "F(hi)", "label_km": "F(hi)"},
  {"id": "F_lo", "role": "bound_value", "relation": "substitute", "of": "F", "at": "lo", "equals": "", "expr": "(lo**2 + c)**(n + 1)/(n + 1)", "label_en": "F(lo)", "label_km": "F(lo)"}]}

Template: y = a*x*sin(k*x), definite from lo to hi, bounds [lo = 0, hi = pi/(2*k)], slots [a, k]
{"template_id": "integral:def_byparts_x_sin",
 "definitions": [{"name": "u", "expr": "a*x"}, {"name": "dv", "expr": "sin(k*x)"}], "compose": "u*dv",
 "checkpoints": [
  {"id": "du", "role": "derived", "relation": "derivative", "of": "u", "at": "", "equals": "", "expr": "a", "label_en": "du/dx", "label_km": "du/dx"},
  {"id": "v", "role": "derived", "relation": "antiderivative", "of": "dv", "at": "", "equals": "", "expr": "-cos(k*x)/k", "label_en": "v", "label_km": "v"},
  {"id": "uv", "role": "derived", "relation": "combination", "of": "", "at": "", "equals": "u*v", "expr": "-a*x*cos(k*x)/k", "label_en": "uv", "label_km": "uv"},
  {"id": "w", "role": "derived", "relation": "antiderivative", "of": "v*du", "at": "", "equals": "", "expr": "-a*sin(k*x)/k**2", "label_en": "∫v du", "label_km": "∫v du"},
  {"id": "F", "role": "antiderivative", "relation": "combination", "of": "", "at": "", "equals": "uv - w", "expr": "-a*x*cos(k*x)/k + a*sin(k*x)/k**2", "label_en": "F(x)", "label_km": "ព្រីមីទីវ F(x)"}]}
(Here F(lo) = F(0) = 0 for every listed bound, so F(hi) IS the final answer: neither is a step.)

Return JSON {"templates": [...]} with exactly one blueprint per template below, same template_id.

TEMPLATES:
"""


def alternative_brief(struct, standard):
    """A template plus its validated standard method, for --alternatives."""
    return {
        **template_brief(struct),
        "standard_method": {k: standard.get(k) for k in ("definitions", "compose", "checkpoints")},
    }


_METHOD_ITEM = {
    "type": "OBJECT",
    "properties": {
        "method_id": _STRING,
        "name_en": _STRING,
        "name_km": _STRING,
        **{k: v for k, v in RESPONSE_SCHEMA["properties"]["templates"]["items"]["properties"].items()
           if k != "template_id"},
    },
    "required": ["method_id", "name_en", "name_km", "definitions", "compose", "checkpoints"],
}

ALTERNATIVES_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "templates": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"template_id": _STRING, "methods": {"type": "ARRAY", "items": _METHOD_ITEM}},
                "required": ["template_id", "methods"],
            },
        }
    },
    "required": ["templates"],
}

ALTERNATIVES_PROMPT = PROMPT[:PROMPT.index('Return JSON {"templates": [...]}')] + r"""
TASK FOR THIS REQUEST — ALTERNATIVE METHODS:
Each template below comes with its STANDARD method's blueprint ("standard_method"). Students
don't always use it. Write 0 to 2 ALTERNATIVE methods per template: other valid ways a real
Grade 12 BAC II student solves it, each as a complete blueprint in the same format, plus
method_id (snake_case), name_en and name_km (a short name of the method).

Good alternatives: a u-substitution done by recognizing the form u'*f(u) directly (no du, no new
bounds) vs. writing the substitution out; for a definite substitution, keeping the x-bounds (F(hi),
F(lo)) vs. changing to u-bounds; expanding a product before integrating vs. a substitution;
a different choice of u and dv. An alternative must ask for DIFFERENT intermediate results than the
standard method — renaming, or the same steps in another order, is NOT an alternative. Every
marking rule above still applies. If no genuinely different method exists, return "methods": [].

Return JSON {"templates": [{"template_id": ..., "methods": [...]}, ...]}, one entry per template.

TEMPLATES:
"""


def structures():
    from .structures import all_integral_structures

    return all_integral_structures()
