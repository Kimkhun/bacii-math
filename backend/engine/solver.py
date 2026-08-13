"""SymPy-based solving for complex-number questions.

`solve()` returns a solution dict holding SymPy expressions (used internally by
the grader and explainer). `serialize()` converts it to JSON-safe primitives for
the HTTP API.
"""
from sympy import I, Abs, arg, conjugate, latex, N, sqrt

QUESTION_TYPES = ("modulus", "argument", "conjugate", "real_part", "imaginary_part")


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


def solve(question_type, a, b):
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


def serialize(solution):
    return {
        "answer_exact": str(solution["answer_exact"]),
        "answer_decimal": solution["answer_decimal"],
        "answer_latex": solution["answer_latex"],
        "steps": solution["steps"],
    }


def _solve_modulus(a, b):
    a2 = a * a
    b2 = b * b
    total = a2 + b2
    r = sqrt(total)
    steps = [
        {
            "title": "Identify the real and imaginary parts",
            "detail": f"For z = {format_z(a, b)}, the real part is a = {a} and the imaginary part is b = {b}.",
        },
        {
            "title": "Apply the modulus formula",
            "detail": "|z| = sqrt(a^2 + b^2).",
        },
        {
            "title": "Substitute the values",
            "detail": f"|z| = sqrt(({a})^2 + ({b})^2) = sqrt({a2} + {b2}).",
        },
        {
            "title": "Simplify",
            "detail": f"|z| = sqrt({total}) = {r}.",
        },
    ]
    return {
        "answer_exact": r,
        "answer_decimal": float(N(r, 8)),
        "answer_latex": latex(r),
        "steps": steps,
    }


def _solve_argument(a, b):
    theta = arg(a + b * I)
    steps = [
        {
            "title": "Apply the argument formula",
            "detail": "arg(z) = atan2(b, a), using the principal value in (-pi, pi].",
        },
        {
            "title": "Substitute the values",
            "detail": f"arg(z) = atan2({b}, {a}).",
        },
        {
            "title": "Result",
            "detail": f"arg(z) = {theta}.",
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
            "detail": "The conjugate of z = a + bi is z_bar = a - bi.",
        },
        {
            "title": "Result",
            "detail": f"z_bar = {format_z(a, -b)}.",
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
            "detail": f"For z = {format_z(a, b)}, Re(z) = a = {a}.",
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
            "detail": f"For z = {format_z(a, b)}, Im(z) = b = {b}.",
        },
    ]
    return {
        "answer_exact": b,
        "answer_decimal": float(b),
        "answer_latex": latex(b),
        "steps": steps,
    }
