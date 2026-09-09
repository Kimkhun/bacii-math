"""z^n via trigonometric form + De Moivre's formula (large n) — distinct from
power.py's direct algebraic expansion (small n). Textbook source: de_moivre_power.json.

z is built from a "nice" (r, standard angle) pair (see trig.py) so the given
number itself is realistic textbook style (e.g. z=2+2i*sqrt(3)), and z^n
reduces to a clean closed form after taking n*theta mod 2*pi.
"""
from sympy import I, cos, latex, simplify, sin

from ...core.shared import _formula_tags, inline_latex
from .trig import angle_from, angle_latex, principal_kd, z_from_polar


def _solve_de_moivre(r, k, d, n):
    theta = angle_from(k, d)
    z = z_from_polar(r, k, d)
    nk, nd = principal_kd(k * n, d)
    n_theta = angle_from(nk, nd)
    result = simplify(r ** n * cos(n_theta) + r ** n * I * sin(n_theta))

    steps = [
        {
            "title": "Write z in trigonometric form",
            "detail": f"\\(z = {latex(z)} = {r}\\left(\\cos({angle_latex(k, d)}) + i\\sin({angle_latex(k, d)})\\right)\\).",
            "formula": "trig_form_conversion",
        },
        {
            "title": "Apply De Moivre's formula",
            "detail": f"\\(z^{{{n}}} = r^{{{n}}}\\left(\\cos(n\\theta) + i\\sin(n\\theta)\\right) = {r}^{{{n}}}\\left(\\cos({n}\\cdot{angle_latex(k, d)}) + i\\sin({n}\\cdot{angle_latex(k, d)})\\right)\\).",
            "formula": "de_moivre_formula",
        },
        {
            "title": "Reduce the angle mod 2π",
            "detail": f"\\(n\\theta \\equiv {angle_latex(nk, nd)} \\pmod{{2\\pi}}\\).",
            "formula": "angle_reduction_mod_2pi",
        },
        {
            "title": "Result (algebraic form)",
            "detail": f"\\(z^{{{n}}}\\) = {inline_latex(result)}.",
            "formula": "trig_to_algebraic",
        },
    ]
    return {
        "answer_exact": result,
        "answer_decimal": str(result),
        "answer_latex": latex(result),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": [
            {"label": "r^n", "value": r ** n, "formula": "de_moivre_formula"},
            {"label": "n*theta mod 2pi", "value": n_theta, "formula": "angle_reduction_mod_2pi"},
            {"label": f"z^{n}", "value": result, "formula": "trig_to_algebraic"},
        ],
    }
