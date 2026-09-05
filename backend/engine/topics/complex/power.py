"""Small integer powers of z = a+bi via direct algebraic expansion (not De Moivre —
see de_moivre.py for the trig-form/large-exponent technique). Textbook source:
power_and_polynomial_expressions.json."""
from sympy import I, expand, latex, simplify

from ...core.shared import _formula_tags, inline_latex


def _solve_complex_power(a, b, n):
    z = a + b * I
    result = simplify(expand((z ** n), complex=True))
    steps = [
        {
            "title": "Identify z",
            "detail": f"\\(z = {latex(z)}\\).",
            "formula": "extract_real_imag",
        },
        {
            "title": f"Expand z^{n} algebraically",
            "detail": f"Expand \\(z^{{{n}}}\\) using \\(i^2=-1\\), collecting real and imaginary terms.",
            "formula": "binomial_expansion_i_squared",
        },
        {
            "title": "Result",
            "detail": f"\\(z^{{{n}}}\\) = {inline_latex(result)}.",
            "formula": "binomial_expansion_i_squared",
        },
    ]
    return {
        "answer_exact": result,
        "answer_decimal": str(result),
        "answer_latex": latex(result),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": [{"label": f"z^{n}", "value": result, "formula": "binomial_expansion_i_squared"}],
    }
