"""Complex-number solvers: modulus, argument, conjugate, real/imaginary part."""
from sympy import Abs, I, N, Symbol, arg, latex, sqrt, sympify

from .shared import _formula_tags, inline_latex


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