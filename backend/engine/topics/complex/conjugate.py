"""Conjugate: z̄ = a - bi. Textbook source: conjugate_computation.json."""
from sympy import I, latex

from ...core.shared import _formula_tags, inline_latex


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
