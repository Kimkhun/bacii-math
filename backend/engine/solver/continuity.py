"""Continuity solver (curated BAC II exercises): SymPy computes the real
left-hand/right-hand limits (or solves for an unknown parameter that makes
them agree) — the curated JSON only supplies the piecewise expressions, the
join point, and the exam-authored technique narration."""
from sympy import Eq, Symbol, latex, limit, simplify, solve, sympify

from .shared import _calc_locals, _formula_tags, inline_latex


def _step(title, detail, formula="continuity_at_point"):
    return {"title": title, "detail": detail, "formula": formula}


def _solve_continuity(params):
    var = params["var"]
    x = Symbol(var)
    locals_ = _calc_locals(var)
    unknown = params.get("unknown")
    if unknown:
        locals_ = dict(locals_)
        locals_[unknown] = Symbol(unknown)

    point = sympify(params["point"], locals=locals_)
    left_expr = sympify(params["left_expr"], locals=locals_)
    right_expr = sympify(params["right_expr"], locals=locals_)

    steps = [_step(
        "Set up the two one-sided limits",
        f"As \\({var} \\to {latex(point)}\\), compare the left-hand limit of "
        f"{inline_latex(left_expr)} with the right-hand limit of {inline_latex(right_expr)}.",
    )]

    if unknown:
        a = Symbol(unknown)
        left_lim = limit(left_expr, x, point, dir="-")
        right_lim = limit(right_expr, x, point, dir="+")
        target_value = params.get("target_value")
        target = sympify(target_value, locals=locals_) if target_value else right_lim
        equation = Eq(left_lim, target) if target_value else Eq(left_lim, right_lim)
        solutions = solve(equation, a)
        positive = [s for s in solutions if s.is_real and s.is_positive]
        result = (positive or solutions or [None])[0]
        steps.append(_step(
            "Compute the limit(s) in terms of the unknown",
            f"Left-hand limit \\(= {inline_latex(left_lim)}\\)"
            + (f", target value \\(= {inline_latex(target)}\\)." if target_value else
               f", right-hand limit \\(= {inline_latex(right_lim)}\\)."),
        ))
        steps.append(_step(
            "Solve for the unknown",
            params.get("curated_technique", ""),
        ))
        steps.append(_step(
            "Result",
            f"\\({unknown} = {inline_latex(result)}\\) makes the function continuous at "
            f"\\({var} = {latex(point)}\\).",
        ))
        checkpoints = [{"label": "parameter value", "value": result, "formula": "continuity_find_parameter"}]
        answer = result
    else:
        left_lim = limit(left_expr, x, point, dir="-")
        right_lim = limit(right_expr, x, point, dir="+")
        agree = simplify(left_lim - right_lim) == 0
        verdict = "continuous" if agree else "discontinuous"
        steps.append(_step("Apply the technique", params.get("curated_technique", "")))
        steps.append(_step(
            "Compare the one-sided limits",
            f"Left-hand limit \\(= {inline_latex(left_lim)}\\), right-hand limit \\(= {inline_latex(right_lim)}\\). "
            + ("They agree, so the function is continuous at this point."
               if agree else "They differ, so the function is discontinuous at this point."),
        ))
        checkpoints = [
            {"label": "left-hand limit", "value": left_lim, "formula": "continuity_at_point"},
            {"label": "right-hand limit", "value": right_lim, "formula": "continuity_at_point"},
        ]
        # The graded answer is the continuity verdict itself (what BAC II
        # actually asks for), not the raw limit value — students conclude in a
        # full sentence ("...so f is discontinuous at x=1"), so this is a
        # "continuity"-kind answer scanned for the verdict word rather than
        # parsed as an expression (see grader._judge_continuity). The limit
        # values above remain SymPy checkpoints so the numeric work leading up
        # to the conclusion is still line-checked.
        return {
            "answer_exact": verdict,
            "answer_kind": "continuity",
            # Restating a piecewise branch symbolically (e.g. writing out
            # "log(3x+1)/x" again before evaluating its limit) is the given
            # setup, not a new computed fact — analyze_work skips a line that
            # matches one of these rather than flagging it wrong.
            "given_expressions": [left_expr, right_expr],
            "answer_decimal": None,
            "answer_latex": verdict,
            "answer_display": verdict,
            "steps": steps,
            "formula_tags": _formula_tags(steps),
            "checkpoints": checkpoints,
        }

    return {
        "answer_exact": answer,
        "answer_decimal": _safe_float(answer),
        "answer_latex": latex(answer),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
    }


def _safe_float(value):
    try:
        from sympy import N
        return float(N(value, 8))
    except (TypeError, ValueError):
        return None
