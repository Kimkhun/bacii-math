"""Arithmetic on two given complex numbers: z1 (+|-|*|/) z2.
Textbook source: arithmetic_operations.json."""
from sympy import I, latex, simplify

from ..shared import _formula_tags, inline_latex

_OP_SYMBOL = {"add": "+", "subtract": "-", "multiply": r"\times", "divide": r"\div"}
_OP_NAME = {"add": "sum", "subtract": "difference", "multiply": "product", "divide": "quotient"}


def _solve_complex_arithmetic(a1, b1, a2, b2, operation):
    z1 = a1 + b1 * I
    z2 = a2 + b2 * I

    if operation == "add":
        result, formula = simplify(z1 + z2), "complex_addition"
        rule = r"(a_1+b_1 i) + (a_2+b_2 i) = (a_1+a_2) + (b_1+b_2)i"
    elif operation == "subtract":
        result, formula = simplify(z1 - z2), "complex_subtraction"
        rule = r"(a_1+b_1 i) - (a_2+b_2 i) = (a_1-a_2) + (b_1-b_2)i"
    elif operation == "multiply":
        result, formula = simplify((z1 * z2).expand(complex=True)), "complex_multiplication"
        rule = r"(a_1+b_1 i)(a_2+b_2 i) = (a_1 a_2 - b_1 b_2) + (a_1 b_2 + a_2 b_1)i"
    elif operation == "divide":
        denom = a2 * a2 + b2 * b2
        result = simplify(((z1 * (a2 - b2 * I)) / denom).expand(complex=True))
        formula = "complex_division"
        rule = r"\frac{z_1}{z_2} = \frac{z_1 \bar{z_2}}{|z_2|^2}"
    else:
        raise ValueError(f"unknown operation: {operation}")

    steps = [
        {
            "title": "Identify the two numbers",
            "detail": f"\\(z_1 = {latex(z1)}\\), \\(z_2 = {latex(z2)}\\).",
            "formula": "extract_real_imag",
        },
        {
            "title": f"Apply the {_OP_NAME[operation]} rule",
            "detail": f"\\({rule}\\).",
            "formula": formula,
        },
        {
            "title": "Result",
            "detail": f"\\(z_1 {_OP_SYMBOL[operation]} z_2\\) = {inline_latex(result)}.",
            "formula": formula,
        },
    ]
    return {
        "answer_exact": result,
        "answer_decimal": str(result),
        "answer_latex": latex(result),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": [{"label": f"z1 {operation} z2", "value": result, "formula": formula}],
    }
