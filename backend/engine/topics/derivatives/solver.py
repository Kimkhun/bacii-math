"""Derivative solver (curated BAC II exercises): SymPy computes the first or
second derivative for real; the curated JSON only supplies the expression and
the exam-authored technique narration."""
from sympy import Symbol, diff, latex, simplify, sympify

from ...core import blueprints
from ...core.shared import _calc_locals, _formula_tags


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
    aux_checkpoints = []
    # The template's blueprint (engine/core/blueprints.py), when it has one,
    # supplies the intermediate checkpoints (u', v', the inner derivative, ...)
    # — each value recomputed by SymPy from its relation on this question's
    # numbers; the last checkpoint stays `result`.
    # A template may have several methods (alternative solution paths);
    # the first is the default, and the grader picks whichever one the
    # student's work follows (derivatives/rubric.py select_method).
    plans = blueprints.resolve("derivatives", params.get("template_id"), params.get("template_params"),
                               given=expr, final=result, x=x, formula="compute_derivative")
    if plans:
        checkpoints = plans[0]["checkpoints"]
        aux_checkpoints = plans[0]["aux_checkpoints"]
    return {
        "answer_exact": result,
        "answer_decimal": None,
        "answer_latex": latex(result),
        "given": expr,
        # Judge the student's own labelled lines (u = ..., u' = ...) by
        # truth, so a different method than the blueprint's isn't marked
        # wrong — see grading._ClaimChecker.
        "verify_claims": True,
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
        "aux_checkpoints": aux_checkpoints,
        "methods": plans,
    }
