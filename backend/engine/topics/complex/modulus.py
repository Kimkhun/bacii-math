"""Modulus |z| = sqrt(a^2+b^2). Textbook source: modulus_argument_computation.json."""
from sympy import Abs, I, N, Symbol, latex, sqrt

from ...core.shared import _formula_tags, inline_latex


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
