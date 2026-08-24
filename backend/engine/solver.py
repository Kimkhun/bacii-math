"""SymPy-based solving for complex-number, limit, and integral questions.

`solve()` returns a solution dict holding SymPy expressions (used internally by
the grader and explainer). `serialize()` converts it to JSON-safe primitives for
the HTTP API.
"""
from sympy import (
    I,
    Abs,
    E,
    Integral,
    Rational,
    Symbol,
    arg,
    binomial,
    cancel,
    conjugate,
    cos,
    cot,
    csc,
    degree,
    exp,
    expand,
    factor,
    integrate,
    latex,
    limit,
    meijerg,
    oo,
    pi,
    N,
    sec,
    simplify,
    sin,
    sqrt,
    sympify,
    tan,
)

QUESTION_TYPES = ("modulus", "argument", "conjugate", "real_part", "imaginary_part")

QUESTION_TYPES_BY_TOPIC = {
    "complex": QUESTION_TYPES,
    "limit": ("limit",),
    "integral": ("definite_integral", "indefinite_integral"),
    "probability": ("probability",),
}


def format_z(a, b):
    if b == 0:
        return str(a)
    if a == 0:
        if b == 1:
            return "i"
        if b == -1:
            return "-i"
        return f"{b}i"
    imag = "" if abs(b) == 1 else str(abs(b))
    sign = "+" if b > 0 else "-"
    return f"{a} {sign} {imag}i"


def z_latex(a, b):
    if b == 0:
        return str(a)
    imag = "" if abs(b) == 1 else str(abs(b))
    if a == 0:
        return ("-" if b < 0 else "") + (imag or "1") + "i"
    sign = "+" if b > 0 else "-"
    return f"{a} {sign} {(imag or '1')}i"


def _calc_locals(var):
    return {var: Symbol(var), "pi": pi, "oo": oo, "sqrt": sqrt, "e": E}


def inline_latex(value) -> str:
    """Wrap a value's LaTeX form in \\( \\) inline-math delimiters, for embedding in
    step 'detail' text that the frontend renders with KaTeX's auto-render."""
    return f"\\({latex(value)}\\)"


def solve(topic, question_type, params):
    if topic == "complex":
        return _solve_complex(question_type, params["a"], params["b"])
    if topic == "limit":
        return _solve_limit(params)
    if topic == "integral":
        if question_type == "indefinite_integral":
            return _solve_indefinite_integral(params)
        return _solve_definite_integral(params)
    if topic == "probability":
        return _solve_probability(params)
    raise ValueError(f"unknown topic: {topic}")


def serialize(solution):
    return {
        "answer_exact": str(solution["answer_exact"]),
        "answer_decimal": solution["answer_decimal"],
        "answer_latex": solution["answer_latex"],
        "steps": solution["steps"],
    }


def _solve_complex(question_type, a, b):
    if question_type == "modulus":
        return _solve_modulus(a, b)
    if question_type == "argument":
        return _solve_argument(a, b)
    if question_type == "conjugate":
        return _solve_conjugate(a, b)
    if question_type == "real_part":
        return _solve_real(a, b)
    if question_type == "imaginary_part":
        return _solve_imag(a, b)
    raise ValueError(f"unknown question_type: {question_type}")


def _formula_tags(steps):
    """Ordered, de-duplicated formula ids used across a solution's steps."""
    return list(dict.fromkeys(s["formula"] for s in steps))


def _solve_modulus(a, b):
    a2 = a * a
    b2 = b * b
    total = a2 + b2
    r = sqrt(total)
    z_sym = a + b * I
    az, bz = Symbol("a"), Symbol("b")
    steps = [
        {
            "title": "Identify the real and imaginary parts",
            "detail": f"For {inline_latex(Symbol('z'))} = {inline_latex(z_sym)}, the real part is {inline_latex(az)} = {inline_latex(a)} and the imaginary part is {inline_latex(bz)} = {inline_latex(b)}.",
            "formula": "extract_real_imag",
        },
        {
            "title": "Apply the modulus formula",
            "detail": f"{inline_latex(Abs(Symbol('z')))} = {inline_latex(sqrt(az**2 + bz**2))}.",
            "formula": "pythagorean",
        },
        {
            "title": "Substitute the values",
            "detail": f"{inline_latex(Abs(Symbol('z')))} = \\(\\sqrt{{({a})^2 + ({b})^2}}\\) = \\(\\sqrt{{{a2} + {b2}}}\\).",
            "formula": "pythagorean",
        },
        {
            "title": "Simplify",
            "detail": f"{inline_latex(Abs(Symbol('z')))} = \\(\\sqrt{{{total}}}\\) = {inline_latex(r)}.",
            "formula": "sqrt_simplify",
        },
    ]
    return {
        "answer_exact": r,
        "answer_decimal": float(N(r, 8)),
        "answer_latex": latex(r),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": [
            {"label": "a^2", "value": a2, "formula": "pythagorean"},
            {"label": "b^2", "value": b2, "formula": "pythagorean"},
            {"label": "a^2 + b^2", "value": total, "formula": "pythagorean"},
            {"label": "sqrt(a^2 + b^2)", "value": r, "formula": "sqrt_simplify"},
        ],
    }


def _solve_argument(a, b):
    theta = arg(a + b * I)
    steps = [
        {
            "title": "Apply the argument formula",
            "detail": f"\\(\\arg(z) = \\operatorname{{atan2}}(b, a)\\), using the principal value in \\((-\\pi, \\pi]\\).",
            "formula": "atan2_ratio",
        },
        {
            "title": "Substitute the values",
            "detail": f"\\(\\arg(z) = \\operatorname{{atan2}}({b}, {a})\\).",
            "formula": "atan2_ratio",
        },
        {
            "title": "Result",
            "detail": f"\\(\\arg(z)\\) = {inline_latex(theta)}.",
            "formula": "quadrant_adjustment",
        },
    ]
    checkpoints = [{"label": "arg(z)", "value": theta, "formula": "quadrant_adjustment"}]
    if a != 0:
        checkpoints.insert(0, {"label": "b/a", "value": sympify(b) / a, "formula": "atan2_ratio"})
    return {
        "answer_exact": theta,
        "answer_decimal": float(N(theta, 8)),
        "answer_latex": latex(theta),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
    }


def _solve_conjugate(a, b):
    c = a - b * I
    steps = [
        {
            "title": "Apply the conjugate rule",
            "detail": "The conjugate of \\(z = a + bi\\) is \\(\\bar{z} = a - bi\\).",
            "formula": "sign_flip",
        },
        {
            "title": "Result",
            "detail": f"\\(\\bar{{z}}\\) = {inline_latex(c)}.",
            "formula": "sign_flip",
        },
    ]
    return {
        "answer_exact": c,
        "answer_decimal": str(c),
        "answer_latex": latex(c),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": [{"label": "conjugate", "value": c, "formula": "sign_flip"}],
    }


def _solve_real(a, b):
    steps = [
        {
            "title": "Identify the real part",
            "detail": f"For {inline_latex(Symbol('z'))} = {inline_latex(a + b * I)}, \\(\\operatorname{{Re}}(z) = a\\) = {inline_latex(a)}.",
            "formula": "extract_real",
        },
    ]
    return {
        "answer_exact": a,
        "answer_decimal": float(a),
        "answer_latex": latex(a),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": [{"label": "Re(z)", "value": a, "formula": "extract_real"}],
    }


def _solve_imag(a, b):
    steps = [
        {
            "title": "Identify the imaginary part",
            "detail": f"For {inline_latex(Symbol('z'))} = {inline_latex(a + b * I)}, \\(\\operatorname{{Im}}(z) = b\\) = {inline_latex(b)}.",
            "formula": "extract_imag",
        },
    ]
    return {
        "answer_exact": b,
        "answer_decimal": float(b),
        "answer_latex": latex(b),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": [{"label": "Im(z)", "value": b, "formula": "extract_imag"}],
    }


def _limit_step(title, detail, formula):
    return {"title": title, "detail": detail, "formula": formula}


def _curated_limit_steps(params, var, point_latex, expr, result):
    """Curated real BAC II exercise: SymPy still computes `result` (the graded
    answer); the exam-authored technique text narrates the steps instead of a
    generic technique handler — the curated JSON only stores prose, not a
    reusable parameterized derivation."""
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
    checkpoints = [{"label": "final value", "value": result, "formula": formula}]
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
    checkpoints = [{"label": "final value", "value": result, "formula": "sinc_standard_limit"}]
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
    checkpoints = [{"label": "final value", "value": result, "formula": "exponential_standard_limit"}]
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
    checkpoints = [{"label": "final value", "value": result, "formula": "rationalization_sinc_combo"}]
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
    checkpoints = [{"label": "final value", "value": result, "formula": "exponential_sinc_combo"}]
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
    checkpoints = [{"label": "final value", "value": result, "formula": "half_angle_sinc_combo"}]
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
    checkpoints = [{"label": "final value", "value": result, "formula": "log_limit_infinity"}]
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
        more_steps, checkpoints = _curated_limit_steps(params, var, point_latex, expr, result)
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
    }


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
        "checkpoints": [
            {
                "label": "antiderivative",
                "value": antiderivative,
                "formula": "setup_integral",
                "constant_ok": True,
            },
        ],
        "given": expr,
    }


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
        "checkpoints": [
            {
                "label": "antiderivative",
                "value": antiderivative,
                "formula": antideriv_formula,
                "constant_ok": True,
            },
            {"label": "F(upper)", "value": f_upper, "formula": "fundamental_theorem"},
            {"label": "F(lower)", "value": f_lower, "formula": "fundamental_theorem"},
        ],
        "given": expr,
    }


# ---------------------------------------------------------------------------
# Probability (topic = "probability", question_type = "probability")
#
# Khmer word problems: the story text comes from the scenario catalog
# (backend/data/scenarios/*.json); the math here is the only authority. Each
# `structure` maps to one solver branch and every branch validates its params
# (impossible problems raise ValueError — the generator's constraint sampler
# prevents them, the solver refuses them).
# ---------------------------------------------------------------------------

_PROB_STRUCTURES = (
    "laplace",
    "hypergeometric",
    "two_box",
    "two_bag_numbers",
    "binomial",
    "union",
    "conditional",
)


def _rational(value):
    """int or '1/2'-style string -> SymPy Rational."""
    return Rational(sympify(value))


def _p_solution(steps, checkpoints, p):
    return {
        "answer_exact": p,
        "answer_decimal": float(N(p, 8)),
        "answer_latex": latex(p),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
        "work_mode": "any_order",
    }


def _solve_probability(params):
    structure = params.get("structure")
    if structure not in _PROB_STRUCTURES:
        raise ValueError(f"unknown probability structure: {structure}")
    parts = params.get("parts")
    if isinstance(parts, list) and parts and all(
        isinstance(p, dict) and p.get("want") for p in parts
    ):
        return _solve_prob_multipart(params, structure, parts)
    return _solve_prob_single(params)


def _solve_prob_multipart(params, structure, parts):
    """Solve every sub-part of a multi-part exercise.

    Each part reuses the single-part branches (params env = shared slots +
    that part's overrides). The question's `answer_exact`/`steps`/... become the
    TARGET part's (the last one by default — the culminating sub-question), so
    create_question/grade keep working unchanged. The full solution is exposed
    via `parts` and the merged `checkpoints` (deduplicated shared totals), so
    explanations and line-checking cover the whole exercise."""
    part_solutions = []
    for part in parts:
        label = part.get("label") or "?"
        want = part.get("want")
        env = {k: v for k, v in part.items() if k not in ("label", "want", "km", "en")}
        single = _solve_prob_single({"structure": structure, "want": want, **env})
        single["checkpoints"] = [
            {**cp, "label": f"{label}: {cp['label']}"} for cp in single["checkpoints"]
        ]
        single["steps"] = [
            {**s, "title": f"Part {label}: {s['title']}"} for s in single["steps"]
        ]
        part_solutions.append({
            "label": label,
            "want": want,
            "answer_exact": single["answer_exact"],
            "answer_decimal": single["answer_decimal"],
            "answer_latex": single["answer_latex"],
            "steps": single["steps"],
            "checkpoints": single["checkpoints"],
            "formula_tags": single["formula_tags"],
        })

    merged_cps = []
    for i, sol in enumerate(part_solutions):
        cps = sol["checkpoints"]
        # The shared sample-space total (first checkpoint) repeats across parts:
        # keep it once, at the top.
        if i > 0 and cps and merged_cps and cps[0]["value"] == merged_cps[0]["value"]:
            cps = cps[1:]
        merged_cps.extend(cps)

    merged_steps = [s for sol in part_solutions for s in sol["steps"]]
    tags = list(dict.fromkeys(t for sol in part_solutions for t in sol["formula_tags"]))
    target = part_solutions[-1]
    return {
        "answer_exact": target["answer_exact"],
        "answer_decimal": target["answer_decimal"],
        "answer_latex": target["answer_latex"],
        "steps": merged_steps,
        "formula_tags": tags,
        "checkpoints": merged_cps,
        "parts": part_solutions,
        "target_label": target["label"],
        "work_mode": "any_order",
    }


def _solve_prob_single(params):
    structure = params.get("structure")
    if structure == "laplace":
        return _solve_prob_laplace(params)
    if structure == "hypergeometric":
        return _solve_prob_hypergeometric(params)
    if structure == "two_box":
        return _solve_prob_two_box(params)
    if structure == "two_bag_numbers":
        return _solve_prob_two_bag_numbers(params)
    if structure == "binomial":
        return _solve_prob_binomial(params)
    if structure == "union":
        return _solve_prob_union(params)
    return _solve_prob_conditional(params)


def _solve_prob_laplace(params):
    total = int(params["total"])
    favorable = int(params["favorable"])
    if not (0 < favorable < total):
        raise ValueError(f"impossible laplace params: favorable={favorable} total={total}")
    p = Rational(favorable, total)
    steps = [
        {
            "title": "Count the total outcomes",
            "detail": f"The sample space has \\(n(\\Omega) = {total}\\) equally likely outcomes.",
            "formula": "laplace_rule",
        },
        {
            "title": "Count the favorable outcomes",
            "detail": f"The event has \\(n(A) = {favorable}\\) favorable outcomes.",
            "formula": "laplace_rule",
        },
        {
            "title": "Apply Laplace's rule",
            "detail": f"\\(P(A) = \\dfrac{{n(A)}}{{n(\\Omega)}} = \\dfrac{{{favorable}}}{{{total}}}\\) = {inline_latex(p)}.",
            "formula": "laplace_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "n(Ω)", "value": total, "formula": "laplace_rule"},
            {"label": "n(A)", "value": favorable, "formula": "laplace_rule"},
            {"label": "P(A)", "value": p, "formula": "laplace_rule"},
        ],
        p,
    )


def _solve_prob_hypergeometric(params):
    w = int(params["w"])
    b = int(params["b"])
    k = int(params["k"])
    want = params.get("want")
    if w < 1 or b < 1 or not (1 <= k <= w + b):
        raise ValueError(f"impossible hypergeometric params: w={w} b={b} k={k}")
    n = w + b
    total = binomial(n, k)

    # Which category a part asks about. "wanted" defaults to w (the white/first
    # category); parts that ask about the second category pass "wanted": "b".
    wanted = params.get("wanted", "w")
    if wanted not in ("w", "b"):
        raise ValueError(f"unknown wanted slot: {wanted}")
    if wanted == "b":
        first, second = b, w
    else:
        first, second = w, b
    first_name = params.get("want_label") or "white"
    second_name = params.get("other_label") or "black"

    if want == "all_white":
        if k > first:
            raise ValueError("all_white: k > wanted count")
        favorable = binomial(first, k)
        title = "Count the favorable draws"
        detail = (
            f"Choosing {k} {first_name} balls from {first}: "
            f"\\(n(A) = C({first}, {k})\\) = {inline_latex(favorable)}."
        )
    elif want == "all_black":
        if k > second:
            raise ValueError("all_black: k > other count")
        favorable = binomial(second, k)
        title = "Count the favorable draws"
        detail = (
            f"Choosing {k} {second_name} balls from {second}: "
            f"\\(n(A) = C({second}, {k})\\) = {inline_latex(favorable)}."
        )
    elif want == "exactly_split":
        a = int(params["a"])
        if not (1 <= a <= k - 1 and a <= first and k - a <= second):
            raise ValueError(f"impossible exactly_split params: w={w} b={b} k={k} a={a}")
        favorable = binomial(first, a) * binomial(second, k - a)
        title = "Count the favorable draws"
        detail = (
            f"Choosing {a} {first_name} balls from {first} and {k - a} {second_name} "
            f"balls from {second}: \\(n(A) = C({first}, {a})\\,C({second}, {k - a})\\) "
            f"= {inline_latex(favorable)}."
        )
    elif want == "at_least_white":
        if not (1 <= k <= second):
            raise ValueError("at_least_white: complement would be trivial")
        no = binomial(second, k)
        p_no = Rational(no, total)
        p = 1 - p_no
        steps = [
            {
                "title": "Count the total draws",
                "detail": f"Drawing {k} balls from {n}: \\(n(\\Omega) = C({n}, {k})\\) = {inline_latex(total)}.",
                "formula": "hypergeometric_rule",
            },
            {
                "title": "Count the unfavorable draws",
                "detail": (
                    f"\"No {first_name} ball\" means all {k} are {second_name}: "
                    f"\\(C({second}, {k})\\) = {inline_latex(no)}. The probability of "
                    f"no {first_name} ball is \\(P(\\text{{no {first_name}}}) = "
                    f"\\dfrac{{{no}}}{{{total}}}\\) = {inline_latex(p_no)}."
                ),
                "formula": "combination_rule",
            },
            {
                "title": "Apply the complement rule",
                "detail": (
                    f"\\(P(\\text{{at least one {first_name}}}) = "
                    f"1 - P(\\text{{no {first_name}}})\\) = {inline_latex(1 - p_no)}."
                ),
                "formula": "complement_rule",
            },
        ]
        return _p_solution(
            steps,
            [
                {"label": "C(n,k) total", "value": total, "formula": "hypergeometric_rule"},
                {"label": f"C({second},{k}) no {first_name}", "value": no, "formula": "combination_rule"},
                {"label": f"P(no {first_name})", "value": p_no, "formula": "combination_rule"},
                {"label": f"P(at least one {first_name})", "value": p, "formula": "complement_rule"},
            ],
            p,
        )
    else:
        raise ValueError(f"unknown hypergeometric want: {want}")

    p = Rational(favorable, total)
    steps = [
        {
            "title": "Count the total draws",
            "detail": f"Drawing {k} balls from {n}: \\(n(\\Omega) = C({n}, {k})\\) = {inline_latex(total)}.",
            "formula": "hypergeometric_rule",
        },
        {
            "title": title,
            "detail": detail,
            "formula": "combination_rule" if want == "exactly_split" else "hypergeometric_rule",
        },
        {
            "title": "Apply the hypergeometric ratio",
            "detail": f"\\(P(A) = \\dfrac{{n(A)}}{{n(\\Omega)}} = \\dfrac{{{favorable}}}{{{total}}}\\) = {inline_latex(p)}.",
            "formula": "hypergeometric_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "C(n,k) total", "value": total, "formula": "hypergeometric_rule"},
            {"label": "n(A) favorable", "value": favorable, "formula": "combination_rule" if want == "exactly_split" else "hypergeometric_rule"},
            {"label": "P(A)", "value": p, "formula": "hypergeometric_rule"},
        ],
        p,
    )


def _solve_prob_two_box(params):
    w1 = int(params["w1"])
    b1 = int(params["b1"])
    w2 = int(params["w2"])
    b2 = int(params["b2"])
    want = params.get("want")
    if min(w1, b1, w2, b2) < 1:
        raise ValueError(f"impossible two_box params: {params}")
    n1, n2 = w1 + b1, w2 + b2
    p_w1, p_b1 = Rational(w1, n1), Rational(b1, n1)
    p_w2, p_b2 = Rational(w2, n2), Rational(b2, n2)

    if want == "both_white":
        p = p_w1 * p_w2
        steps = [
            {"title": "Probability from box 1", "detail": f"\\(P(\\text{{white from box 1}}) = \\dfrac{{{w1}}}{{{n1}}}\\) = {inline_latex(p_w1)}.", "formula": "laplace_rule"},
            {"title": "Probability from box 2", "detail": f"\\(P(\\text{{white from box 2}}) = \\dfrac{{{w2}}}{{{n2}}}\\) = {inline_latex(p_w2)}.", "formula": "laplace_rule"},
            {"title": "Multiply the independent draws", "detail": f"\\(P(\\text{{2 white}}) = \\dfrac{{{w1}}}{{{n1}}} \\times \\dfrac{{{w2}}}{{{n2}}}\\) = {inline_latex(p)}.", "formula": "product_rule"},
        ]
        checkpoints = [
            {"label": "P(white box 1)", "value": p_w1, "formula": "laplace_rule"},
            {"label": "P(white box 2)", "value": p_w2, "formula": "laplace_rule"},
            {"label": "P(A)", "value": p, "formula": "product_rule"},
        ]
    elif want == "both_black":
        p = p_b1 * p_b2
        steps = [
            {"title": "Probability from box 1", "detail": f"\\(P(\\text{{black from box 1}}) = \\dfrac{{{b1}}}{{{n1}}}\\) = {inline_latex(p_b1)}.", "formula": "laplace_rule"},
            {"title": "Probability from box 2", "detail": f"\\(P(\\text{{black from box 2}}) = \\dfrac{{{b2}}}{{{n2}}}\\) = {inline_latex(p_b2)}.", "formula": "laplace_rule"},
            {"title": "Multiply the independent draws", "detail": f"\\(P(\\text{{2 black}}) = \\dfrac{{{b1}}}{{{n1}}} \\times \\dfrac{{{b2}}}{{{n2}}}\\) = {inline_latex(p)}.", "formula": "product_rule"},
        ]
        checkpoints = [
            {"label": "P(black box 1)", "value": p_b1, "formula": "laplace_rule"},
            {"label": "P(black box 2)", "value": p_b2, "formula": "laplace_rule"},
            {"label": "P(A)", "value": p, "formula": "product_rule"},
        ]
    elif want == "cross":
        p = p_w1 * p_b2
        steps = [
            {"title": "Probability from box 1", "detail": f"\\(P(\\text{{white from box 1}}) = \\dfrac{{{w1}}}{{{n1}}}\\) = {inline_latex(p_w1)}.", "formula": "laplace_rule"},
            {"title": "Probability from box 2", "detail": f"\\(P(\\text{{black from box 2}}) = \\dfrac{{{b2}}}{{{n2}}}\\) = {inline_latex(p_b2)}.", "formula": "laplace_rule"},
            {"title": "Multiply the independent draws", "detail": f"\\(P(\\text{{white, black}}) = \\dfrac{{{w1}}}{{{n1}}} \\times \\dfrac{{{b2}}}{{{n2}}}\\) = {inline_latex(p)}.", "formula": "product_rule"},
        ]
        checkpoints = [
            {"label": "P(white box 1)", "value": p_w1, "formula": "laplace_rule"},
            {"label": "P(black box 2)", "value": p_b2, "formula": "laplace_rule"},
            {"label": "P(A)", "value": p, "formula": "product_rule"},
        ]
    elif want == "exactly_one_white":
        term1 = p_w1 * p_b2
        term2 = p_b1 * p_w2
        p = term1 + term2
        steps = [
            {"title": "White from box 1, black from box 2", "detail": f"\\(P(W_1) = \\dfrac{{{w1}}}{{{n1}}}\\), \\(P(B_2) = \\dfrac{{{b2}}}{{{n2}}}\\), so \\(P(W_1 \\cap B_2) = {inline_latex(term1)}\\).", "formula": "product_rule"},
            {"title": "Black from box 1, white from box 2", "detail": f"\\(P(B_1) = \\dfrac{{{b1}}}{{{n1}}}\\), \\(P(W_2) = \\dfrac{{{w2}}}{{{n2}}}\\), so \\(P(B_1 \\cap W_2) = {inline_latex(term2)}\\).", "formula": "product_rule"},
            {"title": "Add the two disjoint cases", "detail": f"\\(P(\\text{{exactly one white}}) = {inline_latex(term1)} + {inline_latex(term2)}\\) = {inline_latex(p)}.", "formula": "union_rule"},
        ]
        checkpoints = [
            {"label": "P(white box 1)", "value": p_w1, "formula": "laplace_rule"},
            {"label": "P(black box 2)", "value": p_b2, "formula": "laplace_rule"},
            {"label": "P(W1 ∩ B2)", "value": term1, "formula": "product_rule"},
            {"label": "P(B1 ∩ W2)", "value": term2, "formula": "product_rule"},
            {"label": "P(A)", "value": p, "formula": "union_rule"},
        ]
    else:
        raise ValueError(f"unknown two_box want: {want}")

    return _p_solution(steps, checkpoints, p)


def _solve_prob_two_bag_numbers(params):
    n = int(params["n"])
    k1 = int(params["k1"])
    k2 = int(params["k2"])
    want = params.get("want")
    if n < 3 or n % 2 == 0 or not (1 <= k1 <= n) or not (1 <= k2 <= n):
        raise ValueError(f"impossible two_bag_numbers params: {params}")
    o, e = (n + 1) // 2, (n - 1) // 2  # odd and even counts among 1..n
    total = binomial(n, k1) * binomial(n, k2)

    def favorable(count):
        return binomial(count, k1) * binomial(count, k2)

    if want == "at_least_one_odd":
        fav_even = favorable(e)
        p_all_even = Rational(fav_even, total)
        p = 1 - p_all_even
        steps = [
            {
                "title": "Count the total draws",
                "detail": f"Drawing {k1} balls from bag 1 and {k2} from bag 2: \\(n(S) = C({n}, {k1})\\,C({n}, {k2})\\) = {inline_latex(total)}.",
                "formula": "combination_rule",
            },
            {
                "title": "Count the all-even draws",
                "detail": f"Choosing only even numbers: \\(n(\\text{{all even}}) = C({e}, {k1})\\,C({e}, {k2})\\) = {inline_latex(fav_even)}.",
                "formula": "combination_rule",
            },
            {
                "title": "Probability that all drawn balls are even",
                "detail": f"\\(P(\\text{{all even}}) = \\dfrac{{{fav_even}}}{{{total}}}\\) = {inline_latex(p_all_even)}.",
                "formula": "product_rule",
            },
            {
                "title": "Apply the complement rule",
                "detail": f"\\(P(\\text{{at least one odd}}) = 1 - P(\\text{{all even}})\\) = {inline_latex(p)}.",
                "formula": "complement_rule",
            },
        ]
        return _p_solution(
            steps,
            [
                {"label": "n(S) total", "value": total, "formula": "combination_rule"},
                {"label": "n(all even)", "value": fav_even, "formula": "combination_rule"},
                {"label": "P(all even)", "value": p_all_even, "formula": "product_rule"},
                {"label": "P(at least one odd)", "value": p, "formula": "complement_rule"},
            ],
            p,
        )

    if want not in ("all_odd", "all_even"):
        raise ValueError(f"unknown two_bag_numbers want: {want}")
    count = o if want == "all_odd" else e
    name = "odd" if want == "all_odd" else "even"
    fav = favorable(count)
    p = Rational(fav, total)
    steps = [
        {
            "title": "Count the total draws",
            "detail": f"Drawing {k1} balls from bag 1 and {k2} from bag 2: \\(n(S) = C({n}, {k1})\\,C({n}, {k2})\\) = {inline_latex(total)}.",
            "formula": "combination_rule",
        },
        {
            "title": "Count the favorable draws",
            "detail": f"Choosing only {name} numbers: \\(n(A) = C({count}, {k1})\\,C({count}, {k2})\\) = {inline_latex(fav)}.",
            "formula": "combination_rule",
        },
        {
            "title": "Apply the ratio",
            "detail": f"\\(P(A) = \\dfrac{{n(A)}}{{n(S)}} = \\dfrac{{{fav}}}{{{total}}}\\) = {inline_latex(p)}.",
            "formula": "product_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "n(S) total", "value": total, "formula": "combination_rule"},
            {"label": "n(A) favorable", "value": fav, "formula": "combination_rule"},
            {"label": "P(A)", "value": p, "formula": "product_rule"},
        ],
        p,
    )


def _solve_prob_binomial(params):
    n = int(params["n"])
    k = int(params["k"])
    if not (1 <= k <= n):
        raise ValueError(f"impossible binomial params: n={n} k={k}")
    total = 2**n
    favorable = binomial(n, k)
    p = Rational(favorable, total)
    steps = [
        {
            "title": "Count the total outcomes",
            "detail": f"Each of the {n} flips has 2 outcomes: \\(n(\\Omega) = 2^{{{n}}}\\) = {total}.",
            "formula": "binomial_rule",
        },
        {
            "title": "Count the favorable outcomes",
            "detail": f"Choosing which {k} of the {n} flips are heads: \\(n(A) = C({n}, {k})\\) = {inline_latex(favorable)}.",
            "formula": "binomial_rule",
        },
        {
            "title": "Apply the binomial formula",
            "detail": f"\\(P(\\text{{exactly }} {k} \\text{{ heads}}) = \\dfrac{{C({n}, {k})}}{{2^{{{n}}}}}\\) = {inline_latex(p)}.",
            "formula": "binomial_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "n(Ω)", "value": total, "formula": "binomial_rule"},
            {"label": "n(A)", "value": favorable, "formula": "binomial_rule"},
            {"label": "P(A)", "value": p, "formula": "binomial_rule"},
        ],
        p,
    )


def _solve_prob_union(params):
    pa = _rational(params["pa"])
    pb = _rational(params["pb"])
    pab = _rational(params["pab"])
    if not (0 < pab <= pa and pab <= pb and pa + pb - pab <= 1):
        raise ValueError(f"impossible union params: {params}")
    p = pa + pb - pab
    steps = [
        {
            "title": "Sum the individual probabilities",
            "detail": f"\\(P(A) + P(B) = {inline_latex(pa)} + {inline_latex(pb)}\\) = {inline_latex(pa + pb)}.",
            "formula": "union_rule",
        },
        {
            "title": "Subtract the intersection",
            "detail": f"\\(P(A \\cup B) = P(A) + P(B) - P(A \\cap B)\\) = {inline_latex(pa + pb)} - {inline_latex(pab)} = {inline_latex(p)}.",
            "formula": "union_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "P(A)+P(B)", "value": pa + pb, "formula": "union_rule"},
            {"label": "P(A∪B)", "value": p, "formula": "union_rule"},
        ],
        p,
    )


def _solve_prob_conditional(params):
    pab = _rational(params["pab"])
    pb = _rational(params["pb"])
    if not (0 < pab <= pb):
        raise ValueError(f"impossible conditional params: {params}")
    p = pab / pb
    steps = [
        {
            "title": "Identify the given probabilities",
            "detail": f"\\(P(A \\cap B) = {inline_latex(pab)}\\) and \\(P(B) = {inline_latex(pb)}\\).",
            "formula": "conditional_rule",
        },
        {
            "title": "Apply the conditional formula",
            "detail": f"\\(P(A \\mid B) = \\dfrac{{P(A \\cap B)}}{{P(B)}} = \\dfrac{{{pab}}}{{{pb}}}\\) = {inline_latex(p)}.",
            "formula": "conditional_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "P(A∩B)", "value": pab, "formula": "conditional_rule"},
            {"label": "P(A|B)", "value": p, "formula": "conditional_rule"},
        ],
        p,
    )


