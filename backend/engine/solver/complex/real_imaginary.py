"""Re(z) / Im(z) extraction. Textbook source: identify_re_im.json."""
from sympy import I, Symbol, latex

from ..shared import _formula_tags, inline_latex


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
