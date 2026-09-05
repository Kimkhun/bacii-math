"""Limit solver (technique handlers for parameterizable techniques + curated ``formula_name`` branch)."""
from sympy import (
    N,
    Pow,
    Symbol,
    cancel,
    cos,
    degree,
    exp,
    expand,
    factor,
    latex,
    limit,
    log,
    oo,
    simplify,
    sin,
    sqrt,
    sympify,
)

from ...core.shared import _calc_locals, _formula_tags, inline_latex


def _limit_step(title, detail, formula):
    return {"title": title, "detail": detail, "formula": formula}


def _has_radical(e):
    return any(isinstance(a, Pow) and not a.exp.is_integer for a in e.atoms(Pow))


def _rationalization_conjugate_checkpoints(x, point, expr, formula):
    """Derive the intermediate "cancelled form" checkpoint for a 0/0 limit
    where exactly one of numerator/denominator carries a square root: rationalize
    that side by its conjugate, cancel the shared (x - point) factor against the
    other (polynomial) side, and report the resulting expression. Generalizes the
    5 curated `rationalization_conjugate_finite` exercises (whichever side —
    numerator or denominator — the sqrt is on, and any leading constant
    multiplier) instead of hardcoding each one. Returns [] when the shape
    doesn't match (e.g. both sides have a radical), leaving the caller with
    just the final-value checkpoint."""
    try:
        num, den = expr.as_numer_denom()
        if _has_radical(num) and not _has_radical(den):
            sqrt_side, poly_side, side = num, den, "num"
        elif _has_radical(den) and not _has_radical(num):
            sqrt_side, poly_side, side = den, num, "den"
        else:
            return []
        terms = sqrt_side.as_ordered_terms()
        sqrt_terms = sum(t for t in terms if _has_radical(t))
        other_terms = sum(t for t in terms if not _has_radical(t))
        conjugate = other_terms - sqrt_terms
        rationalized = expand(sqrt_side * conjugate)
        if side == "num":
            reduced = cancel(rationalized / poly_side)
            cancelled = reduced / conjugate
        else:
            reduced = cancel(poly_side / rationalized)
            cancelled = reduced * conjugate
        if simplify(cancelled.subs(x, point) - limit(expr, x, point)) != 0:
            return []
    except Exception:
        return []
    return [{"label": "cancelled form", "value": cancelled, "formula": formula}]


# formula_names whose parameterized handler (below) computes its checkpoints
# purely from (x, point, expr) — no technique-specific params like a curated
# exercise's k/a/d — so it can be reused as-is to derive intermediate
# checkpoints for the curated version of the same technique.
_CURATED_REUSABLE_HANDLERS = {"direct_substitution", "factoring_0_0", "rational_function_infinity"}


def _exponential_standard_limit_checkpoints(x, point, expr, formula):
    """Derive the two intermediate "divide by the variable, apply the
    standard exponential limit separately" checkpoints for a 0/0 limit shaped
    like (e^{ax}-1)/(e^{bx}-1) at x=0: the numerator and denominator each
    divided by x and limited on their own (giving a and b respectively).
    Purely generic on `expr` — no a/b params needed — so it covers curated
    exercises too, whatever the exact coefficients. Returns [] when the
    denominator's own limit is 0 (shape doesn't apply)."""
    try:
        num, den = expr.as_numer_denom()
        num_lim = limit(num / x, x, point)
        den_lim = limit(den / x, x, point)
        if den_lim == 0:
            return []
        if simplify(num_lim / den_lim - limit(expr, x, point)) != 0:
            return []
    except Exception:
        return []
    return [
        {"label": "numerator limit", "value": num_lim, "formula": formula},
        {"label": "denominator limit", "value": den_lim, "formula": formula},
    ]


def _curated_limit_steps(params, var, x, point, point_latex, expr, result):
    """Curated real BAC II exercise: SymPy still computes `result` (the graded
    answer); the exam-authored technique text narrates the steps instead of a
    generic technique handler — the curated JSON only stores prose, not a
    reusable parameterized derivation. A handful of formula_names still get a
    generically-derived intermediate checkpoint (either by reusing the
    parameter-free handler for the same technique, or a bespoke generic
    deriver for `rationalization_conjugate_finite`) so correct intermediate
    work verifies instead of only the final answer."""
    formula = params["formula_name"]
    steps = [_limit_step(
        "Apply the technique", params.get("curated_technique", ""), formula,
    )]
    if params.get("curated_formula_latex"):
        steps.append(_limit_step(
            "Key identity used", f"\\({params['curated_formula_latex']}\\)", formula,
        ))
    steps.append(_limit_step(
        "Result",
        f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(expr)}\\) = {inline_latex(result)}.",
        formula,
    ))
    checkpoints = []
    if formula == "rationalization_conjugate_finite":
        checkpoints.extend(_rationalization_conjugate_checkpoints(x, point, expr, formula))
    elif formula == "exponential_standard_limit":
        checkpoints.extend(_exponential_standard_limit_checkpoints(x, point, expr, formula))
    elif formula in _CURATED_REUSABLE_HANDLERS:
        try:
            _, extra_cps = _LIMIT_TECHNIQUE_HANDLERS[formula]({}, var, x, point, point_latex, expr, result)
            for cp in extra_cps:
                if simplify(cp["value"] - result) != 0:
                    checkpoints.append({**cp, "formula": formula})
        except Exception:
            pass
    checkpoints.append({"label": "final value", "value": result, "formula": formula})
    return steps, checkpoints


def _handle_direct_substitution(params, var, x, point, point_latex, expr, result):
    direct = simplify(expr.subs(x, point))
    steps = [_limit_step(
        "Evaluate by direct substitution",
        f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(expr)}\\) = {inline_latex(direct)}.",
        "direct_substitution",
    )]
    checkpoints = [{"label": "substituted value", "value": direct, "formula": "direct_substitution"}]
    return steps, checkpoints


def _handle_factoring_0_0(params, var, x, point, point_latex, expr, result):
    num, den = expr.as_numer_denom()
    num_f = factor(num)
    den_f = factor(den)
    cancelled = cancel(num_f / den_f)
    sub_val = simplify(cancelled.subs(x, point))
    steps = [
        _limit_step(
            "Try direct substitution",
            f"Substituting \\({var} = {point_latex}\\) into {inline_latex(expr)} gives \\(0/0\\), an indeterminate form, so we factor.",
            "setup_limit",
        ),
        _limit_step(
            "Factor the expression",
            f"{inline_latex(expr)} = \\(\\dfrac{{{latex(num_f)}}}{{{latex(den_f)}}}\\).",
            "factor_difference_of_squares",
        ),
        _limit_step(
            "Cancel the common factor",
            f"\\(\\dfrac{{{latex(num_f)}}}{{{latex(den_f)}}}\\) = {inline_latex(cancelled)}.",
            "cancel_common_factor",
        ),
        _limit_step(
            "Evaluate by direct substitution",
            f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(cancelled)}\\) = {inline_latex(sub_val)}.",
            "direct_substitution",
        ),
    ]
    checkpoints = [
        {"label": "factored form", "value": num_f / den_f, "formula": "factor_difference_of_squares"},
        {"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"},
        {"label": "substituted value", "value": sub_val, "formula": "direct_substitution"},
    ]
    return steps, checkpoints


def _handle_rational_function_infinity(params, var, x, point, point_latex, expr, result):
    num, den = expr.as_numer_denom()
    n = max(degree(num, x), degree(den, x))
    divided = expand(num / x**n) / expand(den / x**n)
    ratio = limit(divided, x, oo)
    steps = [
        _limit_step(
            "Divide numerator and denominator by the highest power",
            f"{inline_latex(expr)} = {inline_latex(divided)}.",
            "divide_highest_power",
        ),
        _limit_step(
            "Take the limit of the resulting ratio",
            f"\\(\\lim_{{{var} \\to \\infty}} {latex(divided)}\\) = {inline_latex(ratio)}.",
            "leading_coefficient_ratio",
        ),
    ]
    checkpoints = [
        {"label": "divided by highest power", "value": divided, "formula": "divide_highest_power"},
        {"label": "leading coefficient ratio", "value": ratio, "formula": "leading_coefficient_ratio"},
    ]
    return steps, checkpoints


def _handle_sinc_standard_limit(params, var, x, point, point_latex, expr, result):
    k, c = params["k"], params.get("c", 1)
    kx = f"{k}{var}" if k != 1 else var
    coeff_prefix = f"{c} \\cdot " if c != 1 else ""
    steps = [
        _limit_step(
            "Rewrite so the sine's argument matches the denominator",
            f"{inline_latex(expr)} = \\({coeff_prefix}{k} \\cdot \\dfrac{{\\sin({kx})}}{{{kx}}}\\).",
            "sinc_standard_limit",
        ),
        _limit_step(
            "Apply the standard sinc limit",
            f"As \\({var} \\to 0\\), \\(\\dfrac{{\\sin({kx})}}{{{kx}}} \\to 1\\), so the limit is {inline_latex(result)}.",
            "sinc_standard_limit",
        ),
    ]
    rewritten = c * k * sin(k * x) / (k * x)
    checkpoints = [
        {"label": "rewritten form", "value": rewritten, "formula": "sinc_standard_limit"},
        {"label": "final value", "value": result, "formula": "sinc_standard_limit"},
    ]
    return steps, checkpoints


def _handle_exponential_standard_limit(params, var, x, point, point_latex, expr, result):
    a, b = params["a"], params["b"]
    steps = [
        _limit_step(
            "Divide numerator and denominator by the variable",
            f"{inline_latex(expr)} = \\(\\dfrac{{(e^{{{a}{var}}}-1)/{var}}}{{(e^{{{b}{var}}}-1)/{var}}}\\).",
            "exponential_standard_limit",
        ),
        _limit_step(
            "Apply the standard exponential limit",
            f"As \\({var} \\to 0\\), \\(\\dfrac{{e^{{k{var}}}-1}}{{{var}}} \\to k\\) for any constant \\(k\\), so this ratio \\(\\to \\dfrac{{{a}}}{{{b}}}\\) = {inline_latex(result)}.",
            "exponential_standard_limit",
        ),
    ]
    checkpoints = _exponential_standard_limit_checkpoints(x, point, expr, "exponential_standard_limit")
    checkpoints.append({"label": "final value", "value": result, "formula": "exponential_standard_limit"})
    return steps, checkpoints


def _handle_conjugate_infinity(params, var, x, point, point_latex, expr, result):
    k, b, c, d = params["k"], params["b"], params["c"], params["d"]
    sqrt_part = sqrt(k**2 * x**2 + b * x + c)
    linear_part = k * x + d
    conjugate = sqrt_part + linear_part
    numerator = expand(sqrt_part**2 - linear_part**2)
    divided = expand(numerator / x) / expand(conjugate / x)
    steps = [
        _limit_step(
            "Multiply and divide by the conjugate",
            f"Multiply and divide by \\({latex(conjugate)}\\): {inline_latex(expr)} = \\(\\dfrac{{{latex(numerator)}}}{{{latex(conjugate)}}}\\).",
            "conjugate_infinity",
        ),
        _limit_step(
            "Divide numerator and denominator by the dominant power",
            f"\\(\\dfrac{{{latex(numerator)}}}{{{latex(conjugate)}}}\\) = {inline_latex(divided)}.",
            "divide_highest_power",
        ),
        _limit_step(
            "Take the limit of the resulting ratio",
            f"\\(\\lim_{{{var} \\to \\infty}} {latex(divided)}\\) = {inline_latex(result)}.",
            "leading_coefficient_ratio",
        ),
    ]
    checkpoints = [
        {"label": "divided by highest power", "value": divided, "formula": "divide_highest_power"},
        {"label": "final value", "value": result, "formula": "leading_coefficient_ratio"},
    ]
    return steps, checkpoints


def _handle_rationalization_conjugate_finite(params, var, x, point, point_latex, expr, result):
    p, d, c, n = params["p"], params["d"], params["c"], params["n"]
    conjugate = sqrt(x + c) + d
    numerator_poly = expand(x**n - p**n)
    poly_ratio = cancel(numerator_poly / (x - p))
    cancelled = expand(poly_ratio) * conjugate
    steps = [
        _limit_step(
            "Multiply and divide by the conjugate",
            f"Since \\(\\sqrt{{{point_latex}+{c}}} = {d}\\), this is \\(0/0\\). Multiply and divide by \\({latex(conjugate)}\\): "
            f"{inline_latex(expr)} = \\(\\dfrac{{{latex(numerator_poly)} \\cdot ({latex(conjugate)})}}{{{var}-{p}}}\\).",
            "rationalization_conjugate_finite",
        ),
        _limit_step(
            "Cancel the common factor",
            f"\\(\\dfrac{{{latex(numerator_poly)}}}{{{var}-{p}}} = {latex(poly_ratio)}\\), so the expression simplifies to {inline_latex(cancelled)}.",
            "cancel_common_factor",
        ),
        _limit_step(
            "Evaluate by direct substitution",
            f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(cancelled)}\\) = {inline_latex(result)}.",
            "direct_substitution",
        ),
    ]
    checkpoints = [
        {"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"},
        {"label": "final value", "value": result, "formula": "direct_substitution"},
    ]
    return steps, checkpoints


def _handle_rationalization_sinc_combo(params, var, x, point, point_latex, expr, result):
    a, k = params["a"], params["k"]
    conjugate = sqrt(a + x) + sqrt(a - x)
    part1 = limit(2 * x / sin(k * x), x, 0)
    part2 = limit(1 / conjugate, x, 0)
    steps = [
        _limit_step(
            "Multiply and divide by the conjugate",
            f"Multiply and divide by \\({latex(conjugate)}\\): {inline_latex(expr)} = "
            f"\\(\\dfrac{{2{var}}}{{\\sin({k}{var}) \\cdot ({latex(conjugate)})}}\\).",
            "rationalization_sinc_combo",
        ),
        _limit_step(
            "Split into a sinc limit and a continuous factor",
            f"\\(\\dfrac{{2{var}}}{{\\sin({k}{var})}} \\to {latex(part1)}\\) and "
            f"\\(\\dfrac{{1}}{{{latex(conjugate)}}} \\to {latex(part2)}\\) as \\({var} \\to 0\\).",
            "rationalization_sinc_combo",
        ),
        _limit_step(
            "Multiply the two limits",
            f"{inline_latex(part1)} \\(\\cdot\\) {inline_latex(part2)} = {inline_latex(result)}.",
            "rationalization_sinc_combo",
        ),
    ]
    checkpoints = [
        {"label": "sinc factor", "value": part1, "formula": "rationalization_sinc_combo"},
        {"label": "conjugate factor", "value": part2, "formula": "rationalization_sinc_combo"},
        {"label": "final value", "value": result, "formula": "rationalization_sinc_combo"},
    ]
    return steps, checkpoints


def _handle_exponential_sinc_combo(params, var, x, point, point_latex, expr, result):
    a, k = params["a"], params["k"]
    continuous_val = (exp(a * x) + exp(-a * x)).subs(x, 0)
    sinc_sq = limit(sin(k * x)**2 / x**2, x, 0)
    steps = [
        _limit_step(
            "Split into a continuous factor and a sinc-squared limit",
            f"{inline_latex(expr)} = \\(\\dfrac{{(e^{{{a}{var}}}+e^{{-{a}{var}}})}}{{2}} \\cdot \\dfrac{{\\sin^2({k}{var})}}{{{var}^2}}\\).",
            "exponential_sinc_combo",
        ),
        _limit_step(
            "Evaluate each factor",
            f"As \\({var} \\to 0\\): the continuous factor \\(\\to {latex(continuous_val)}/2\\), and "
            f"\\(\\dfrac{{\\sin^2({k}{var})}}{{{var}^2}} \\to {latex(sinc_sq)}\\).",
            "exponential_sinc_combo",
        ),
        _limit_step(
            "Multiply the two limits",
            f"\\(\\dfrac{{{latex(continuous_val)}}}{{2}} \\cdot {latex(sinc_sq)}\\) = {inline_latex(result)}.",
            "exponential_sinc_combo",
        ),
    ]
    checkpoints = [
        {"label": "exponential factor", "value": continuous_val, "formula": "exponential_sinc_combo"},
        {"label": "sinc-squared factor", "value": sinc_sq, "formula": "exponential_sinc_combo"},
        {"label": "final value", "value": result, "formula": "exponential_sinc_combo"},
    ]
    return steps, checkpoints


def _handle_half_angle_sinc_combo(params, var, x, point, point_latex, expr, result):
    k, m = params["k"], params["m"]
    part1 = limit(sin(k * x) / x, x, 0)
    part2 = limit((1 - cos(m * x)) / x**2, x, 0)
    steps = [
        _limit_step(
            "Split into a sinc limit and a half-angle limit",
            f"{inline_latex(expr)} = \\(\\dfrac{{\\sin({k}{var})}}{{{var}}} \\cdot \\dfrac{{1-\\cos({m}{var})}}{{{var}^2}}\\).",
            "half_angle_sinc_combo",
        ),
        _limit_step(
            "Evaluate each factor",
            f"As \\({var} \\to 0\\): \\(\\dfrac{{\\sin({k}{var})}}{{{var}}} \\to {latex(part1)}\\), and "
            f"\\(\\dfrac{{1-\\cos({m}{var})}}{{{var}^2}} \\to {latex(part2)}\\).",
            "half_angle_sinc_combo",
        ),
        _limit_step(
            "Multiply the two limits",
            f"{inline_latex(part1)} \\(\\cdot\\) {inline_latex(part2)} = {inline_latex(result)}.",
            "half_angle_sinc_combo",
        ),
    ]
    checkpoints = [
        {"label": "sinc factor", "value": part1, "formula": "half_angle_sinc_combo"},
        {"label": "half-angle factor", "value": part2, "formula": "half_angle_sinc_combo"},
        {"label": "final value", "value": result, "formula": "half_angle_sinc_combo"},
    ]
    return steps, checkpoints


def _handle_log_limit_infinity(params, var, x, point, point_latex, expr, result):
    c, k = params["c"], params["k"]
    coeff_prefix = f"{c} \\cdot " if c != 1 else ""
    steps = [
        _limit_step(
            "Rewrite the log difference as a single logarithm",
            f"{inline_latex(expr)} = \\({coeff_prefix}{var} \\ln\\!\\left(1+\\dfrac{{{k}}}{{{var}}}\\right)\\).",
            "log_limit_infinity",
        ),
        _limit_step(
            "Reduce to the standard log limit",
            f"With \\(u = {k}/{var} \\to 0\\), \\({var}\\ln(1+{k}/{var}) = {k} \\cdot \\dfrac{{\\ln(1+u)}}{{u}} \\to {k}\\) "
            f"since \\(\\dfrac{{\\ln(1+u)}}{{u}} \\to 1\\).",
            "log_limit_infinity",
        ),
        _limit_step(
            "Multiply by the remaining coefficient",
            f"The limit is {inline_latex(result)}.",
            "log_limit_infinity",
        ),
    ]
    rewritten = c * x * log(1 + k / x)
    checkpoints = [
        {"label": "rewritten form", "value": rewritten, "formula": "log_limit_infinity"},
        {"label": "final value", "value": result, "formula": "log_limit_infinity"},
    ]
    return steps, checkpoints


_LIMIT_TECHNIQUE_HANDLERS = {
    "direct_substitution": _handle_direct_substitution,
    "factoring_0_0": _handle_factoring_0_0,
    "rational_function_infinity": _handle_rational_function_infinity,
    "sinc_standard_limit": _handle_sinc_standard_limit,
    "exponential_standard_limit": _handle_exponential_standard_limit,
    "conjugate_infinity": _handle_conjugate_infinity,
    "rationalization_conjugate_finite": _handle_rationalization_conjugate_finite,
    "rationalization_sinc_combo": _handle_rationalization_sinc_combo,
    "exponential_sinc_combo": _handle_exponential_sinc_combo,
    "half_angle_sinc_combo": _handle_half_angle_sinc_combo,
    "log_limit_infinity": _handle_log_limit_infinity,
}


def _legacy_inferred_steps(var, x, point, point_latex, expr, result):
    """Fallback classification for limit params with neither `formula_name` nor
    a known `technique` (shouldn't happen once callers always tag one of
    those, but kept as a safety net)."""
    if point in (oo, -oo):
        return _handle_rational_function_infinity({}, var, x, point, point_latex, expr, result)
    try:
        direct = simplify(expr.subs(x, point))
    except Exception:
        direct = None
    if direct is not None and direct.is_finite:
        return _handle_direct_substitution({}, var, x, point, point_latex, expr, result)
    return _handle_factoring_0_0({}, var, x, point, point_latex, expr, result)


def _solve_limit(params):
    var = params["var"]
    x = Symbol(var)
    expr = sympify(params["expr"], locals=_calc_locals(var))
    point = sympify(params["point"], locals=_calc_locals(var))
    side = params.get("side")
    kwargs = {"dir": side} if side else {}
    result = limit(expr, x, point, **kwargs)

    point_latex = latex(point) + ("^" + ("+" if side == "+" else "-") if side else "")

    steps = [
        {
            "title": "Set up the limit",
            "detail": f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(expr)}\\).",
            "formula": "setup_limit",
        },
    ]

    if params.get("formula_name"):
        more_steps, checkpoints = _curated_limit_steps(params, var, x, point, point_latex, expr, result)
    else:
        technique = params.get("technique")
        handler = _LIMIT_TECHNIQUE_HANDLERS.get(technique)
        if handler:
            more_steps, checkpoints = handler(params, var, x, point, point_latex, expr, result)
        else:
            more_steps, checkpoints = _legacy_inferred_steps(var, x, point, point_latex, expr, result)
    steps.extend(more_steps)

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
        "point": point,
        "var": var,
    }