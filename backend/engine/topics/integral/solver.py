"""Definite and indefinite integral solvers.

The graded intermediate steps come from the question's template blueprint
(``engine/core/blueprints.py``, ``blueprint_spec.py``) when it has one — the
antiderivative of each term, the substitution's du and new bounds, the parts
u, v, du, F and its values at the bounds — each value recomputed by SymPy on
this question's numbers; otherwise from the antiderivative alone."""
from sympy import (
    Integral,
    N,
    Symbol,
    cos,
    cot,
    csc,
    exp,
    integrate,
    latex,
    meijerg,
    sec,
    simplify,
    sin,
    tan,
    sympify,
)

from ...core import blueprints
from ...core.shared import _calc_locals, _formula_tags, inline_latex


def checkpoint_flags(cp):
    """An antiderivative step is right up to any constant (F + C)."""
    if cp.get("role") in ("antiderivative", "term_antiderivative") or cp.get("relation") == "antiderivative":
        return {"constant_ok": True}
    return {}


def _bounds_env(params, var):
    loc = _calc_locals(var)
    return {"lo": sympify(params["lower"], locals=loc), "hi": sympify(params["upper"], locals=loc)}


def _blueprint_plans(params, x, expr, final, formula, definite, antiderivative):
    """The template blueprint's grading plans (one per method), [] if none.
    A blueprint writes F in the form a student does ((x**2+3)**4/4); SymPy's
    own antiderivative may differ from it by a constant (x**8/4 + ...), so
    every F(hi)/F(lo) step also accepts the value shifted by that constant."""
    given = {"y": expr, **(_bounds_env(params, params["var"]) if definite else {})}
    plans = blueprints.resolve("integral", params.get("template_id"), params.get("template_params"),
                               given=given, final=final, x=x, formula=formula,
                               checkpoint_flags=checkpoint_flags,
                               final_flags=None if definite else {"constant_ok": True})
    for plan in plans:
        forms = [cp["value"] for cp in plan["checkpoints"] if cp.get("role") == "antiderivative"]
        shifts = []
        for F in forms:
            try:
                c = simplify(antiderivative - F)
            except Exception:  # noqa: BLE001
                continue
            if c != 0 and not c.has(x):
                shifts.append(c)
        for cp in plan["checkpoints"]:
            if cp.get("role") == "bound_value" and shifts:
                cp["alternatives"] = [simplify(cp["value"] + c) for c in shifts]
    return plans


def _indefinite_term_tag(term, x):
    """Which basic antiderivative rule a single summand exercises."""
    if term.has(sin, cos, tan, cot, sec, csc):
        return "antiderivative_trig"
    if term.has(exp) and term.free_symbols:
        return "antiderivative_exponential"  # e^x (E**x is exp(x) in SymPy)
    if not term.free_symbols:
        return "antiderivative_power_rule"  # constants: ∫k dx = kx
    if (term * x).free_symbols == set():
        return "antiderivative_reciprocal"  # a constant multiple of 1/x
    return "antiderivative_power_rule"

def _solve_indefinite_integral(params):
    var = params["var"]
    x = Symbol(var)
    expr = sympify(params["expr"], locals=_calc_locals(var))
    antiderivative = integrate(expr, x)
    variant = params.get("variant")

    steps = [
        {
            "title": "Set up the indefinite integral",
            "detail": f"\\(\\int {latex(expr)}\\,d{var}\\) — find an antiderivative of each term.",
            "formula": "setup_integral",
        },
    ]
    if variant == "expand":
        steps.append({
            "title": "Expand the product",
            "detail": f"Expand {inline_latex(expr)} into a sum of terms before integrating.",
            "formula": "expand_before_integrating",
        })
    elif variant == "split":
        steps.append({
            "title": "Split the fraction",
            "detail": f"Divide each term of the numerator by the denominator: {inline_latex(expr)}.",
            "formula": "split_fraction",
        })
    elif variant == "usub":
        steps.append({
            "title": "Substitute u = g(x)",
            "detail": f"The integrand {inline_latex(expr)} has the form \\(g'(x)\\,f(g(x))\\), so set \\(u = g({var})\\), \\(du = g'({var})\\,d{var}\\).",
            "formula": "u_substitution",
        })
    elif variant == "linear_argument":
        steps.append({
            "title": "Apply the linear-argument rule",
            "detail": f"The integrand {inline_latex(expr)} is a function of a linear expression in \\({var}\\), so \\(\\int f(a{var}+b)\\,d{var} = \\frac{{1}}{{a}}F(a{var}+b) + C\\).",
            "formula": "linear_argument_rule",
        })

    terms = expr.expand().as_ordered_terms() if expr.is_Add else [expr]
    for term in terms:
        tag = _indefinite_term_tag(term, x)
        steps.append({
            "title": f"Antiderivative of {latex(term)}",
            "detail": f"Applying the rule for {inline_latex(term)} gives a term of the antiderivative.",
            "formula": tag,
        })
    steps.append({
        "title": "Combine and add the constant",
        "detail": f"The antiderivative is {inline_latex(antiderivative)} + C.",
        "formula": "setup_integral",
    })

    try:
        decimal = float(N(antiderivative.subs(x, 1), 8))
    except (TypeError, ValueError):
        decimal = None
    return {
        "answer_exact": antiderivative,
        "answer_decimal": decimal,
        "answer_latex": latex(antiderivative),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        **_with_blueprint(params, x, expr, antiderivative, "setup_integral", False, antiderivative, [
            {
                "label": "antiderivative",
                "value": antiderivative,
                "formula": "setup_integral",
                "constant_ok": True,
            },
        ]),
        "given": expr,
    }


def _with_blueprint(params, x, expr, final, formula, definite, antiderivative, checkpoints):
    """The solution's checkpoints: the blueprint's plans when the template
    has one, else `checkpoints`."""
    plans = _blueprint_plans(params, x, expr, final, formula, definite, antiderivative)
    if not plans:
        return {"checkpoints": checkpoints}
    return {"checkpoints": plans[0]["checkpoints"], "aux_checkpoints": plans[0]["aux_checkpoints"],
            "methods": plans}

def _solve_definite_integral(params):
    var = params["var"]
    x = Symbol(var)
    expr = sympify(params["expr"], locals=_calc_locals(var))
    lower = sympify(params["lower"], locals=_calc_locals(var))
    upper = sympify(params["upper"], locals=_calc_locals(var))
    antiderivative = integrate(expr, x)
    result = integrate(expr, (x, lower, upper))
    if result.has(Integral):
        # SymPy sometimes leaves a definite form unevaluated (e.g.
        # ∫ ln(x)/√x dx) while a clean exact result exists. Try the manual
        # (rules-based) integrator first — for both the definite result and the
        # antiderivative (substituting the messy meijerg Piecewise is very slow).
        try:
            alt = integrate(expr, (x, lower, upper), manual=True)
            if alt is not None and not alt.has(Integral):
                result = alt
                ant_alt = integrate(expr, x, manual=True)
                if ant_alt is not None and not ant_alt.has(Integral, meijerg):
                    antiderivative = ant_alt
            else:
                alt2 = simplify(antiderivative.subs(x, upper) - antiderivative.subs(x, lower))
                if not alt2.has(Integral):
                    result = alt2
        except Exception:
            try:
                alt2 = simplify(antiderivative.subs(x, upper) - antiderivative.subs(x, lower))
                if not alt2.has(Integral):
                    result = alt2
            except Exception:
                pass
    variant = params.get("variant") or (
        "trig" if expr.has(sin, cos) else "polynomial"
    )
    antideriv_formula = {
        "trig": "antiderivative_trig",
        "linear_argument": "linear_argument_rule",
        "u_substitution": "u_substitution",
    }.get(variant, "antiderivative_power_rule")
    f_upper = simplify(antiderivative.subs(x, upper))
    f_lower = simplify(antiderivative.subs(x, lower))

    steps = []
    if variant == "linear_argument":
        steps.append({
            "title": "Apply the linear-argument rule",
            "detail": (
                f"The integrand {inline_latex(expr)} is a function of a linear "
                f"expression in \\({var}\\), so \\(\\int f(a{var}+b)\\,d{var} = "
                f"\\frac{{1}}{{a}}F(a{var}+b) + C\\): an antiderivative is "
                f"{inline_latex(antiderivative)} + C."
            ),
            "formula": "linear_argument_rule",
        })
    elif variant == "u_substitution":
        steps.append({
            "title": "Substitute u = g(x)",
            "detail": (
                f"The integrand {inline_latex(expr)} has the form "
                f"\\(g'(x)\\,f(g(x))\\), so set \\(u = g({var})\\) and "
                f"\\(du = g'({var})\\,d{var}\\)."
            ),
            "formula": "u_substitution",
        })
        steps.append({
            "title": "Integrate in u",
            "detail": (
                f"After substitution the integral becomes a standard form; "
                f"back-substituting \\(u = g({var})\\) gives the antiderivative "
                f"{inline_latex(antiderivative)} + C."
            ),
            "formula": "u_substitution",
        })
    elif variant == "by_parts":
        steps.append({
            "title": "Apply integration by parts",
            "detail": (
                f"Choose \\(u\\) and \\(dv\\) so the integrand is \\(u\\,dv\\): "
                f"\\(\\int u\\,dv = uv - \\int v\\,du\\). The antiderivative is "
                f"{inline_latex(antiderivative)} + C."
            ),
            "formula": "integration_by_parts",
        })
    elif variant == "mixed_sum":
        for term in expr.expand().as_ordered_terms():
            tag = _indefinite_term_tag(term, x)
            steps.append({
                "title": f"Antiderivative of {latex(term)}",
                "detail": f"Applying the rule for {inline_latex(term)} gives a term of the antiderivative.",
                "formula": tag,
            })
    else:
        steps.append({
            "title": "Find the antiderivative",
            "detail": f"An antiderivative of {inline_latex(expr)} with respect to \\({var}\\) is {inline_latex(antiderivative)} + C.",
            "formula": antideriv_formula,
        })

    steps.append({
        "title": "Apply the bounds",
        "detail": f"Evaluate the antiderivative from \\({var} = {latex(lower)}\\) to \\({var} = {latex(upper)}\\), i.e. \\(F({latex(upper)}) - F({latex(lower)})\\).",
        "formula": "fundamental_theorem",
    })
    steps.append({
        "title": "Result",
        "detail": f"\\(\\int_{{{latex(lower)}}}^{{{latex(upper)}}} {latex(expr)}\\,d{var}\\) = {inline_latex(result)}.",
        "formula": "fundamental_theorem",
    })
    try:
        decimal = float(N(result, 8))
    except (TypeError, ValueError):
        decimal = None
    return {
        "answer_exact": result,
        "answer_decimal": decimal,
        "answer_latex": latex(result),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        **_with_blueprint(params, x, expr, result, "fundamental_theorem", True, antiderivative, [
            {
                "label": "antiderivative",
                "value": antiderivative,
                "formula": antideriv_formula,
                "constant_ok": True,
            },
            {"label": "F(upper)", "value": f_upper, "formula": "fundamental_theorem"},
            {"label": "F(lower)", "value": f_lower, "formula": "fundamental_theorem"},
        ]),
        "given": expr,
    }