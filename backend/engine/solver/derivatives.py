"""Derivative solver (curated BAC II exercises): SymPy computes the first or
second derivative for real; the curated JSON only supplies the expression and
the exam-authored technique narration."""
from sympy import Symbol, diff, latex, simplify, sympify

from .shared import _calc_locals, _formula_tags


def _step(title, detail, formula="compute_derivative"):
    return {"title": title, "detail": detail, "formula": formula}


def _solve_derivative(params):
    var = params["var"]
    x = Symbol(var)
    expr = sympify(params["expr"], locals=_calc_locals(var))
    order = int(params.get("order", 1))

    steps = [_step(
        "Set up the derivative",
        f"Differentiate \\(y = {latex(expr)}\\)" + (f" twice" if order == 2 else "") + ".",
    )]
    steps.append(_step("Apply the technique", params.get("curated_technique", "")))

    first = simplify(diff(expr, x))
    result = first
    if order == 2:
        second = simplify(diff(first, x))
        steps.append(_step("First derivative", f"\\(y' = {latex(first)}\\)."))
        steps.append(_step("Second derivative", f"\\(y'' = {latex(second)}\\)."))
        result = second
    else:
        steps.append(_step("Result", f"\\(y' = {latex(result)}\\)."))

    if order == 2:
        checkpoints = [
            {"label": "first derivative", "value": first, "formula": "compute_derivative"},
            {"label": "second derivative", "value": result, "formula": "compute_derivative"},
        ]
    else:
        checkpoints = [{"label": "derivative", "value": result, "formula": "compute_derivative"}]
    return {
        "answer_exact": result,
        "answer_decimal": None,
        "answer_latex": latex(result),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
    }
