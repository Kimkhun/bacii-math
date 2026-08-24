"""Limit solver (procedural variants + the curated ``formula_name`` branch)."""
from sympy import N, Symbol, cancel, degree, expand, factor, latex, limit, oo, simplify, sympify

from .shared import _calc_locals, _formula_tags, inline_latex


def _solve_limit(params):
    var = params["var"]
    x = Symbol(var)
    expr = sympify(params["expr"], locals=_calc_locals(var))
    point = sympify(params["point"], locals=_calc_locals(var))
    side = params.get("side")
    kwargs = {"dir": side} if side else {}
    result = limit(expr, x, point, **kwargs)

    point_latex = latex(point) + ("^" + ("+" if side == "+" else "-") if side else "")

    if point in (oo, -oo):
        variant = "infinity_rational"
    else:
        try:
            direct = simplify(expr.subs(x, point))
        except Exception:
            direct = None
        variant = "polynomial" if direct is not None and direct.is_finite else "removable"

    steps = [
        {
            "title": "Set up the limit",
            "detail": f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(expr)}\\).",
            "formula": "setup_limit",
        },
    ]

    if params.get("formula_name"):
        # Curated real BAC II exercise: SymPy still computes `result` above
        # (the graded answer); the exam-authored technique text narrates the
        # steps instead of the generic 3-branch classification below.
        formula = params["formula_name"]
        steps.append({
            "title": "Apply the technique",
            "detail": params.get("curated_technique", ""),
            "formula": formula,
        })
        if params.get("curated_formula_latex"):
            steps.append({
                "title": "Key identity used",
                "detail": f"\\({params['curated_formula_latex']}\\)",
                "formula": formula,
            })
        steps.append({
            "title": "Result",
            "detail": f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(expr)}\\) = {inline_latex(result)}.",
            "formula": formula,
        })
        checkpoints = [{"label": "final value", "value": result, "formula": formula}]
    elif variant == "polynomial":
        steps.append({
            "title": "Evaluate by direct substitution",
            "detail": f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(expr)}\\) = {inline_latex(direct)}.",
            "formula": "direct_substitution",
        })
        checkpoints = [{"label": "substituted value", "value": direct, "formula": "direct_substitution"}]
    elif variant == "removable":
        num, den = expr.as_numer_denom()
        num_f = factor(num)
        den_f = factor(den)
        cancelled = cancel(num_f / den_f)
        sub_val = simplify(cancelled.subs(x, point))
        steps.append({
            "title": "Try direct substitution",
            "detail": f"Substituting \\({var} = {point_latex}\\) into {inline_latex(expr)} gives \\(0/0\\), an indeterminate form, so we factor.",
            "formula": "setup_limit",
        })
        steps.append({
            "title": "Factor the expression",
            "detail": f"{inline_latex(expr)} = \\(\\dfrac{{{latex(num_f)}}}{{{latex(den_f)}}}\\).",
            "formula": "factor_difference_of_squares",
        })
        steps.append({
            "title": "Cancel the common factor",
            "detail": f"\\(\\dfrac{{{latex(num_f)}}}{{{latex(den_f)}}}\\) = {inline_latex(cancelled)}.",
            "formula": "cancel_common_factor",
        })
        steps.append({
            "title": "Evaluate by direct substitution",
            "detail": f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(cancelled)}\\) = {inline_latex(sub_val)}.",
            "formula": "direct_substitution",
        })
        checkpoints = [
            {"label": "factored form", "value": num_f / den_f, "formula": "factor_difference_of_squares"},
            {"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"},
            {"label": "substituted value", "value": sub_val, "formula": "direct_substitution"},
        ]
    else:  # infinity_rational
        num, den = expr.as_numer_denom()
        n = max(degree(num, x), degree(den, x))
        divided = expand(num / x**n) / expand(den / x**n)
        ratio = limit(divided, x, oo)
        steps.append({
            "title": "Divide numerator and denominator by the highest power",
            "detail": f"{inline_latex(expr)} = {inline_latex(divided)}.",
            "formula": "divide_highest_power",
        })
        steps.append({
            "title": "Take the limit of the resulting ratio",
            "detail": f"\\(\\lim_{{{var} \\to \\infty}} {latex(divided)}\\) = {inline_latex(ratio)}.",
            "formula": "leading_coefficient_ratio",
        })
        checkpoints = [
            {"label": "divided by highest power", "value": divided, "formula": "divide_highest_power"},
            {"label": "leading coefficient ratio", "value": ratio, "formula": "leading_coefficient_ratio"},
        ]

    try:
        decimal = float(N(result, 8))
    except TypeError:
        decimal = str(result)
    return {
        "answer_exact": result,
        "answer_decimal": decimal,
        "answer_latex": latex(result),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
        "given": expr,
    }