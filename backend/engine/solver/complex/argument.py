"""Principal argument arg(z) via atan2. Textbook source: modulus_argument_computation.json."""
from sympy import I, N, arg, latex, sympify

from ..shared import _formula_tags, inline_latex


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
