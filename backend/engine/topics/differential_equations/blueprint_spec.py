"""What an LLM needs to write, and SymPy needs to check, a differential-
equations blueprint (see ``engine/core/blueprints.py`` for the format and the
validation gate). Consumed by ``scripts/generate_blueprints.py``.

An ODE's marking scheme is a chain — characteristic roots, the particular
solution, the general solution, the constants from the initial conditions —
and every link can be checked for what it *means*, not only for agreeing
with the LLM's own arithmetic. So each checkpoint declares a ``role`` and
`required` verifies it on every sampled instance:

  root                  a root of the characteristic polynomial
  discriminant          b^2 - 4c
  alpha / beta          the real part / |imaginary part| of the complex roots
  coefficient           an undetermined coefficient of the particular
                        solution (solved, so a plain number)
  particular_solution   satisfies the full equation, no arbitrary constant
  homogeneous_solution  solves L[y] = 0 with as many constants as the order
  general_solution      solves L[y] = rhs with as many constants as the order
  constant              an arbitrary constant's value; substituting them all
                        into the general solution must give the final answer
  derived               a derivative / a substitution of earlier steps

The final answer is never the blueprint's: it is ``dsolve``'s
(`solver.ode_answer`).
"""
import re

from sympy import Symbol, diff, roots as poly_roots, simplify, sympify

from ...core.shared import _calc_locals
from .solver import ARBITRARY_CONSTANTS, SYMBOLS, ode_answer
from .structures import instantiate, slot_names

TOPIC = "differential_equations"
FORMULA = "solve_ode"

_ROLES = ("root", "discriminant", "alpha", "beta", "coefficient", "particular_solution",
          "homogeneous_solution", "general_solution", "constant", "derived")


def truth(struct, params, x):
    """The final answer — dsolve's, never the blueprint's."""
    return ode_answer(params)


def given_env(struct, params):
    """An ODE has no given expression a step could restate: the slots are
    the whole question."""
    return {}


def _operator(params, x):
    """(L, order, characteristic polynomial, right-hand side) of the equation."""
    loc = _calc_locals("x")
    rhs = sympify(params.get("rhs", "0"), locals=loc)
    if params["kind"].startswith("first"):
        a = sympify(params["a"], locals=loc)
        return (lambda f: diff(f, x) + a * f), 1, (lambda r: r + a), rhs
    b, c = sympify(params["b"], locals=loc), sympify(params["c"], locals=loc)
    return (lambda f: diff(f, x, 2) + b * diff(f, x) + c * f), 2, (lambda r: r**2 + b * r + c), rhs


def _zero(expr):
    try:
        return simplify(expr) == 0
    except Exception:  # noqa: BLE001
        return False


def required(struct, bp, values, x, params, final):
    """Every checkpoint means what its role says, on this instance."""
    from ...core.grading import _equivalent_exact

    L, order, P, rhs = _operator(params, x)
    constants = {SYMBOLS[n] for n in ARBITRARY_CONSTANTS}
    coefficients = set(SYMBOLS.values()) - constants
    r = Symbol("r")
    roots = list(poly_roots(P(r), r))
    problems, found_constants, generals = [], {}, []
    has = {role: False for role in _ROLES}
    for cp, value in values["checkpoints"]:
        role, cid = cp.get("role"), cp.get("id")
        if role not in _ROLES:
            problems.append(f"checkpoint {cid}: unknown role {role!r}")
            continue
        has[role] = True
        free = getattr(value, "free_symbols", set()) - {x}
        if free & coefficients:
            problems.append(f"checkpoint {cid} = {value} still contains an unsolved coefficient "
                            f"{sorted(map(str, free & coefficients))} — solve it first")
            continue
        uses = free & constants
        if uses and x not in getattr(value, "free_symbols", set()):
            problems.append(f"checkpoint {cid} = {value} has arbitrary constants but no x (an initial-condition "
                            f"expression like C1 + C2) — a student never writes it as a value; use it only "
                            f"inside a solve step's equations")
            continue
        if role in ("root", "discriminant", "alpha", "beta", "coefficient", "constant") and free:
            problems.append(f"checkpoint {cid} ({role}) = {value} must be a number")
        elif role == "root" and not _zero(P(value)):
            problems.append(f"checkpoint {cid} = {value} is not a root of {P(r)}")
        elif role == "discriminant" and (order != 2 or not _zero(value - (P(r).coeff(r, 1) ** 2 - 4 * P(r).subs(r, 0)))):
            problems.append(f"checkpoint {cid} = {value} is not the discriminant of {P(r)}")
        elif role == "alpha" and not any(_zero(value - root.as_real_imag()[0]) for root in roots if not root.is_real):
            problems.append(f"checkpoint {cid} = {value} is not the real part of a complex root of {P(r)}")
        elif role == "beta" and not any(_zero(value - abs(root.as_real_imag()[1])) for root in roots if not root.is_real):
            problems.append(f"checkpoint {cid} = {value} is not |imaginary part| of a complex root of {P(r)}")
        elif role == "particular_solution" and (uses or not _zero(L(value) - rhs)):
            problems.append(f"checkpoint {cid} = {value} is not a particular solution (L[y] - rhs = "
                            f"{simplify(L(value) - rhs)})")
        elif role in ("homogeneous_solution", "general_solution"):
            target = 0 if role == "homogeneous_solution" else rhs
            if len(uses) != order:
                problems.append(f"checkpoint {cid} ({role}) = {value} must have {order} arbitrary constant(s), "
                                f"has {sorted(map(str, uses))}")
            elif not _zero(L(value) - target):
                problems.append(f"checkpoint {cid} = {value} does not solve the "
                                f"{'homogeneous' if target == 0 else 'full'} equation")
            elif role == "general_solution":
                generals.append(value)
        elif role == "constant":
            name = str(cp.get("of", "")).strip()
            if cp.get("relation") != "solve" or name not in ARBITRARY_CONSTANTS:
                problems.append(f"checkpoint {cid}: a constant is a 'solve' step whose 'of' is one of "
                                f"{list(ARBITRARY_CONSTANTS)}")
            else:
                found_constants[SYMBOLS[name]] = value
        elif role == "coefficient" and cp.get("relation") != "solve":
            problems.append(f"checkpoint {cid}: a coefficient is a 'solve' step")
        elif role == "derived" and cp.get("relation") not in ("derivative", "substitute"):
            problems.append(f"checkpoint {cid}: a 'derived' step must be a derivative or a substitution")
    if problems:
        return problems
    if order == 2 and not (has["root"] or has["alpha"] or has["beta"]):
        problems.append("a second-order blueprint must grade the characteristic roots (role root, or alpha/beta)")
    if not generals:
        problems.append("no general_solution checkpoint")
    if "nonhomogeneous" in params["kind"] and not has["particular_solution"]:
        problems.append("a non-homogeneous blueprint must grade the particular solution")
    if has["coefficient"] and not has["particular_solution"]:
        problems.append("coefficients without the particular solution they build")
    if params.get("ics"):
        for g in generals:
            names = getattr(g, "free_symbols", set()) & constants
            missing = sorted(str(n) for n in names if n not in found_constants)
            if missing:
                problems.append(f"the initial conditions fix {missing}, but no constant checkpoint solves for them")
            elif not _equivalent_exact(g.subs(found_constants), final, x):
                problems.append(f"the general solution with the constants substituted is "
                                f"{simplify(g.subs(found_constants))}, but the solution is {final}")
    return problems


def validate(bp, struct, samples=6, seed=0):
    from ...core import blueprints

    return blueprints.validate(bp, struct, instantiate, truth, samples=samples, seed=seed, required=required,
                               symbols=SYMBOLS, given_env=given_env, expr_optional=True)


def _symbolic_params(struct):
    return instantiate(struct, {n: Symbol(n) for n in slot_names(struct)})


def template_brief(struct):
    """How one template is presented to the LLM: the equation and the
    initial conditions written in the slots."""
    p = _symbolic_params(struct)
    if struct["category"].startswith("second"):
        lhs = f"y'' + ({p['b']})*y' + ({p['c']})*y"
        conditions = f"y({p['ics']['x0']}) = {p['ics']['y0']}, y'({p['ics']['x0']}) = {p['ics']['yp0']}"
    else:
        lhs = f"y' + ({p['a']})*y"
        conditions = f"y({p['ics']['x0']}) = {p['ics']['y0']}"
    return {
        "template_id": struct["id"],
        "equation": f"{lhs} = {p.get('rhs', '0')}",
        "initial_conditions": conditions,
        "slots": slot_names(struct),
        "slot_notes": struct["slot_notes"],
        "kind": struct["category"],
    }


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
                                             "enum": ["combination", "solve", "derivative", "substitute"]},
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
MARKING SCHEME for linear differential equations with constant coefficients. Each exercise below
is a TEMPLATE: an equation in y(x) whose numbers are integer parameters (slots), with initial
conditions. Write one blueprint per template that works for ANY slot values.

A blueprint lists the results a marker awards points for (checkpoints), in the order a student
writes them. You are NOT computing a numeric answer; a computer algebra system recomputes every
value from your relations on each question's own numbers, and checks that each checkpoint really
is what its role says.

EXPRESSION SYNTAX (strict, SymPy):
- x is the variable. Slots are plain symbols. Use * for every product, ** for powers.
- exp(...), log(...), sqrt(...), sin, cos, pi. I is the imaginary unit. Never write e as a number.
- diff(E, x) and diff(E, x, 2) are E' and E''; E.subs(x, 0) is E at x = 0.
- Arbitrary constants: C (first order), C1 and C2 (second order).
- Undetermined coefficients of a trial particular solution: A, B, D.

DEFINITIONS (optional): named helper expressions, never graded, e.g. a trial particular solution
{"name": "Y", "expr": "A*x + B"}. Names: Y, Z (never a slot name, x, y, t, C, C1, C2, A, B, D).
Set "compose" to "".

CHECKPOINTS: each has an id (short identifier), a role, a relation, expr and labels.
Relations (unused fields are ""):
- "combination": `equals` is an expression in slots, x, definitions, earlier checkpoint ids,
  C/C1/C2.
- "solve": `equals` holds one or more equations separated by ";" (each "left = right"), and `of`
  names the unknown this checkpoint is (C, C1, C2, A, B or D). All unknowns in the equations are
  solved together. An equation containing x must hold for every x (coefficients are matched).
- "derivative": derivative with respect to x of `of` (an earlier checkpoint id).
- "substitute": `of` evaluated at x = `at`.
Roles:
- "discriminant": b**2 - 4*c of the characteristic equation r**2 + b*r + c = 0.
- "root": one root of the characteristic equation (a double root once).
- "alpha", "beta": for complex roots alpha +/- beta*I, the numbers alpha and beta (beta > 0).
- "coefficient": an undetermined coefficient's value (relation "solve", of "A"/"B"/"D").
- "particular_solution": y_p, no arbitrary constant.
- "homogeneous_solution": y_h, the general solution of the equation with right-hand side 0.
- "general_solution": y = y_h + y_p (for a homogeneous equation, y_h itself).
- "constant": the value of C/C1/C2 from the initial conditions (relation "solve", `of` the
  constant, `equals` the initial-condition equations, e.g. "yg.subs(x, 0) = y0;
  diff(yg, x).subs(x, 0) = yp0").
- "derived": a derivative or substitution of an earlier checkpoint that a student writes as a
  value (rarely needed).
expr: YOUR explicit value of the checkpoint written ONLY in x, the slots and C/C1/C2 (no
definition or checkpoint names). For "constant" and "coefficient" checkpoints you may leave expr "".
label_en / label_km: short labels, e.g. "Δ", "r_1", "y_p", "general solution", "C_1";
label_km in Khmer keeping the math (e.g. "ឫស r_1", "ចម្លើយពិសេស y_p", "ចម្លើយទូទៅ", "ថេរ C_1").

MARKING RULES:
1. Never include the final answer (the solution with the constants substituted): it is graded
   automatically. Every checkpoint must have a different value.
2. A homogeneous equation: do NOT list a separate homogeneous_solution (it equals the general
   solution). A non-homogeneous one: list y_h, y_p and the general solution.
3. Second order: grade the discriminant and the roots (complex roots: alpha and beta) — except
   a value that is always 0 for the template (the discriminant of a double root, alpha for
   y'' + w**2*y = 0): it earns no marks and any stray "= 0" line would match it, so leave it out.
   The same goes for any other checkpoint that is always 0.
4. Never make a checkpoint of an expression containing constants but no x (like C1 + C2 from
   y(0)): those go only inside a "solve" step's equations.
5. Never make a checkpoint of a trial form with unsolved A, B, D. A coefficient equal to the
   particular solution itself (a constant y_p) is not a separate checkpoint: make y_p a "solve"
   step instead.
6. Grade every constant the initial conditions fix (C, or C1 and C2).

EXAMPLES:

Template: y' + (a)*y = a*p*x + a*q + p, y(0) = y0, slots [a, p, q, y0]
{"template_id": "ode:first_nonhom:linear_rhs",
 "definitions": [{"name": "Y", "expr": "A*x + B"}], "compose": "",
 "checkpoints": [
  {"id": "yh", "role": "homogeneous_solution", "relation": "combination", "of": "", "at": "", "equals": "C*exp(-a*x)", "expr": "C*exp(-a*x)", "label_en": "y_h", "label_km": "ចម្លើយទូទៅនៃសមីការអូម៉ូសែន y_h"},
  {"id": "A_v", "role": "coefficient", "relation": "solve", "of": "A", "at": "", "equals": "diff(Y, x) + a*Y = a*p*x + a*q + p", "expr": "p", "label_en": "A", "label_km": "A"},
  {"id": "B_v", "role": "coefficient", "relation": "solve", "of": "B", "at": "", "equals": "diff(Y, x) + a*Y = a*p*x + a*q + p", "expr": "q", "label_en": "B", "label_km": "B"},
  {"id": "yp", "role": "particular_solution", "relation": "combination", "of": "", "at": "", "equals": "A_v*x + B_v", "expr": "p*x + q", "label_en": "y_p", "label_km": "ចម្លើយពិសេស y_p"},
  {"id": "yg", "role": "general_solution", "relation": "combination", "of": "", "at": "", "equals": "yh + yp", "expr": "C*exp(-a*x) + p*x + q", "label_en": "general solution", "label_km": "ចម្លើយទូទៅ"},
  {"id": "C_v", "role": "constant", "relation": "solve", "of": "C", "at": "", "equals": "yg.subs(x, 0) = y0", "expr": "y0 - q", "label_en": "C", "label_km": "ថេរ C"}]}

Template: y'' + (-r1 - r2)*y' + (r1*r2)*y = 0, y(0) = y0, y'(0) = yp0, slots [r1, r2, y0, yp0]
{"template_id": "ode:second_hom:distinct_roots",
 "definitions": [], "compose": "",
 "checkpoints": [
  {"id": "delta", "role": "discriminant", "relation": "combination", "of": "", "at": "", "equals": "(r1 + r2)**2 - 4*r1*r2", "expr": "(r1 - r2)**2", "label_en": "Δ", "label_km": "ឌីសគ្រីមីណង់ Δ"},
  {"id": "ra", "role": "root", "relation": "combination", "of": "", "at": "", "equals": "r1", "expr": "r1", "label_en": "r_1", "label_km": "ឫស r_1"},
  {"id": "rb", "role": "root", "relation": "combination", "of": "", "at": "", "equals": "r2", "expr": "r2", "label_en": "r_2", "label_km": "ឫស r_2"},
  {"id": "yg", "role": "general_solution", "relation": "combination", "of": "", "at": "", "equals": "C1*exp(ra*x) + C2*exp(rb*x)", "expr": "C1*exp(r1*x) + C2*exp(r2*x)", "label_en": "general solution", "label_km": "ចម្លើយទូទៅ"},
  {"id": "c1", "role": "constant", "relation": "solve", "of": "C1", "at": "", "equals": "yg.subs(x, 0) = y0; diff(yg, x).subs(x, 0) = yp0", "expr": "(yp0 - r2*y0)/(r1 - r2)", "label_en": "C_1", "label_km": "ថេរ C_1"},
  {"id": "c2", "role": "constant", "relation": "solve", "of": "C2", "at": "", "equals": "yg.subs(x, 0) = y0; diff(yg, x).subs(x, 0) = yp0", "expr": "(r1*y0 - yp0)/(r1 - r2)", "label_en": "C_2", "label_km": "ថេរ C_2"}]}

Template: y'' + (-2*al)*y' + (al**2 + be**2)*y = al**2*q + be**2*q, y(0) = y0, y'(0) = yp0, slots [al, be, q, y0, yp0]
{"template_id": "ode:second_nonhom:complex_roots_constant_rhs",
 "definitions": [], "compose": "",
 "checkpoints": [
  {"id": "delta", "role": "discriminant", "relation": "combination", "of": "", "at": "", "equals": "4*al**2 - 4*(al**2 + be**2)", "expr": "-4*be**2", "label_en": "Δ", "label_km": "ឌីសគ្រីមីណង់ Δ"},
  {"id": "alpha", "role": "alpha", "relation": "combination", "of": "", "at": "", "equals": "al", "expr": "al", "label_en": "α", "label_km": "α"},
  {"id": "beta", "role": "beta", "relation": "combination", "of": "", "at": "", "equals": "be", "expr": "be", "label_en": "β", "label_km": "β"},
  {"id": "yh", "role": "homogeneous_solution", "relation": "combination", "of": "", "at": "", "equals": "exp(alpha*x)*(C1*cos(beta*x) + C2*sin(beta*x))", "expr": "exp(al*x)*(C1*cos(be*x) + C2*sin(be*x))", "label_en": "y_h", "label_km": "ចម្លើយទូទៅនៃសមីការអូម៉ូសែន y_h"},
  {"id": "yp", "role": "particular_solution", "relation": "solve", "of": "A", "at": "", "equals": "(al**2 + be**2)*A = al**2*q + be**2*q", "expr": "q", "label_en": "y_p", "label_km": "ចម្លើយពិសេស y_p"},
  {"id": "yg", "role": "general_solution", "relation": "combination", "of": "", "at": "", "equals": "yh + yp", "expr": "exp(al*x)*(C1*cos(be*x) + C2*sin(be*x)) + q", "label_en": "general solution", "label_km": "ចម្លើយទូទៅ"},
  {"id": "c1", "role": "constant", "relation": "solve", "of": "C1", "at": "", "equals": "yg.subs(x, 0) = y0; diff(yg, x).subs(x, 0) = yp0", "expr": "y0 - q", "label_en": "C_1", "label_km": "ថេរ C_1"},
  {"id": "c2", "role": "constant", "relation": "solve", "of": "C2", "at": "", "equals": "yg.subs(x, 0) = y0; diff(yg, x).subs(x, 0) = yp0", "expr": "", "label_en": "C_2", "label_km": "ថេរ C_2"}]}

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

Good alternatives: finding the particular solution by undetermined coefficients written out (A, B
as their own steps) vs. stating it directly; the roots found by factoring instead of the
discriminant (no discriminant step); for complex roots, writing the roots themselves
(alpha + beta*I, alpha - beta*I as role "root") instead of alpha and beta. An alternative must
ask for DIFFERENT intermediate results than the standard method — renaming, or the same steps in
another order, is NOT an alternative. Every marking rule above still applies. If no genuinely
different method exists, return "methods": [].

Return JSON {"templates": [{"template_id": ..., "methods": [...]}, ...]}, one entry per template.

TEMPLATES:
"""


def structures():
    from .structures import all_ode_structures

    return all_ode_structures()
