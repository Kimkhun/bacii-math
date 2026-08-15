"""SymPy-based solving for complex-number and calculus questions.

`solve()` returns a solution dict holding SymPy expressions (used internally by
the grader and explainer). `serialize()` converts it to JSON-safe primitives for
the HTTP API.
"""
from sympy import I, Abs, Symbol, arg, conjugate, integrate, latex, limit, oo, pi, sympify, latex as _latex, N, sqrt

QUESTION_TYPES = ("modulus", "argument", "conjugate", "real_part", "imaginary_part")
CALCULUS_QUESTION_TYPES = ("limit", "definite_integral")

QUESTION_TYPES_BY_TOPIC = {
    "complex": QUESTION_TYPES,
    "calculus": CALCULUS_QUESTION_TYPES,
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
    return {var: Symbol(var), "pi": pi, "oo": oo, "sqrt": sqrt}


def inline_latex(value) -> str:
    """Wrap a value's LaTeX form in \\( \\) inline-math delimiters, for embedding in
    step 'detail' text that the frontend renders with KaTeX's auto-render."""
    return f"\\({latex(value)}\\)"


def solve(topic, question_type, params):
    if topic == "complex":
        return _solve_complex(question_type, params["a"], params["b"])
    if topic == "calculus":
        return _solve_calculus(question_type, params)
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


def _solve_calculus(question_type, params):
    if question_type == "limit":
        return _solve_limit(params)
    if question_type == "definite_integral":
        return _solve_definite_integral(params)
    raise ValueError(f"unknown question_type: {question_type}")


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
        },
        {
            "title": "Apply the modulus formula",
            "detail": f"{inline_latex(Abs(Symbol('z')))} = {inline_latex(sqrt(az**2 + bz**2))}.",
        },
        {
            "title": "Substitute the values",
            "detail": f"{inline_latex(Abs(Symbol('z')))} = \\(\\sqrt{{({a})^2 + ({b})^2}}\\) = \\(\\sqrt{{{a2} + {b2}}}\\).",
        },
        {
            "title": "Simplify",
            "detail": f"{inline_latex(Abs(Symbol('z')))} = \\(\\sqrt{{{total}}}\\) = {inline_latex(r)}.",
        },
    ]
    return {
        "answer_exact": r,
        "answer_decimal": float(N(r, 8)),
        "answer_latex": latex(r),
        "steps": steps,
        "checkpoints": [
            ("a^2", a2),
            ("b^2", b2),
            ("a^2 + b^2", total),
            ("sqrt(a^2 + b^2)", r),
        ],
    }


def _solve_argument(a, b):
    theta = arg(a + b * I)
    steps = [
        {
            "title": "Apply the argument formula",
            "detail": f"\\(\\arg(z) = \\operatorname{{atan2}}(b, a)\\), using the principal value in \\((-\\pi, \\pi]\\).",
        },
        {
            "title": "Substitute the values",
            "detail": f"\\(\\arg(z) = \\operatorname{{atan2}}({b}, {a})\\).",
        },
        {
            "title": "Result",
            "detail": f"\\(\\arg(z)\\) = {inline_latex(theta)}.",
        },
    ]
    return {
        "answer_exact": theta,
        "answer_decimal": float(N(theta, 8)),
        "answer_latex": latex(theta),
        "steps": steps,
    }


def _solve_conjugate(a, b):
    c = a - b * I
    steps = [
        {
            "title": "Apply the conjugate rule",
            "detail": "The conjugate of \\(z = a + bi\\) is \\(\\bar{z} = a - bi\\).",
        },
        {
            "title": "Result",
            "detail": f"\\(\\bar{{z}}\\) = {inline_latex(c)}.",
        },
    ]
    return {
        "answer_exact": c,
        "answer_decimal": str(c),
        "answer_latex": latex(c),
        "steps": steps,
    }


def _solve_real(a, b):
    steps = [
        {
            "title": "Identify the real part",
            "detail": f"For {inline_latex(Symbol('z'))} = {inline_latex(a + b * I)}, \\(\\operatorname{{Re}}(z) = a\\) = {inline_latex(a)}.",
        },
    ]
    return {
        "answer_exact": a,
        "answer_decimal": float(a),
        "answer_latex": latex(a),
        "steps": steps,
    }


def _solve_imag(a, b):
    steps = [
        {
            "title": "Identify the imaginary part",
            "detail": f"For {inline_latex(Symbol('z'))} = {inline_latex(a + b * I)}, \\(\\operatorname{{Im}}(z) = b\\) = {inline_latex(b)}.",
        },
    ]
    return {
        "answer_exact": b,
        "answer_decimal": float(b),
        "answer_latex": latex(b),
        "steps": steps,
    }


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
        },
        {
            "title": "Evaluate",
            "detail": f"The limit evaluates to {inline_latex(result)}.",
        },
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
    }


def _solve_definite_integral(params):
    var = params["var"]
    x = Symbol(var)
    expr = sympify(params["expr"], locals=_calc_locals(var))
    lower = sympify(params["lower"], locals=_calc_locals(var))
    upper = sympify(params["upper"], locals=_calc_locals(var))
    antiderivative = integrate(expr, x)
    result = integrate(expr, (x, lower, upper))

    steps = [
        {
            "title": "Find the antiderivative",
            "detail": f"An antiderivative of {inline_latex(expr)} with respect to \\({var}\\) is {inline_latex(antiderivative)} + C.",
        },
        {
            "title": "Apply the bounds",
            "detail": f"Evaluate the antiderivative from \\({var} = {latex(lower)}\\) to \\({var} = {latex(upper)}\\).",
        },
        {
            "title": "Result",
            "detail": f"\\(\\int_{{{latex(lower)}}}^{{{latex(upper)}}} {latex(expr)}\\,d{var}\\) = {inline_latex(result)}.",
        },
    ]
    return {
        "answer_exact": result,
        "answer_decimal": float(N(result, 8)),
        "answer_latex": latex(result),
        "steps": steps,
    }
