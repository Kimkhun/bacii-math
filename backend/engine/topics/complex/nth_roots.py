"""Find one n-th root of z (solve w^n = z for one w), built by reverse
construction from a "nice" root: pick w = rho(cos(theta0)+i sin(theta0)) from
the standard-angle pool first, then z = w^n is the given number, so the
expected answer is always a clean closed form. Textbook source: roots_of_unity.json
(the subset asking for a concrete root; the symmetric-sum/Vieta identity
problems in that file are not yet templated — see docs/generator-variants.md)."""
from sympy import I, cos, latex, simplify, sin

from ...core.shared import _formula_tags, inline_latex
from .trig import angle_from, angle_latex, principal_kd, z_from_polar


def _solve_nth_root(rho, k0, d0, n):
    """rho, k0, d0 define the *answer* w = rho*(cos(k0*pi/d0) + i*sin(...));
    z = w^n is computed and presented as the given number."""
    theta0 = angle_from(k0, d0)
    w = z_from_polar(rho, k0, d0)
    zk, zd = principal_kd(k0 * n, d0)
    z_theta = angle_from(zk, zd)
    z = simplify(rho ** n * cos(z_theta) + rho ** n * I * sin(z_theta))

    steps = [
        {
            "title": "Write z in trigonometric form",
            "detail": f"\\(z = {latex(z)} = {rho ** n}\\left(\\cos({angle_latex(zk, zd)}) + i\\sin({angle_latex(zk, zd)})\\right)\\).",
            "formula": "trig_form_conversion",
        },
        {
            "title": f"Take the modulus^(1/{n}) and divide the angle by {n}",
            "detail": rf"\(|w| = |z|^{{1/{n}}} = {rho}\), \(\arg(w) = \dfrac{{\arg(z)}}{{{n}}} = {angle_latex(k0, d0)}\) (one of {n} possible roots, differing by \(\dfrac{{2\pi}}{{{n}}}\)).",
            "formula": "nth_root_formula",
        },
        {
            "title": "Result (algebraic form)",
            "detail": f"\\(w\\) = {inline_latex(w)}.",
            "formula": "trig_to_algebraic",
        },
    ]
    return {
        "answer_exact": w,
        "answer_decimal": str(w),
        "answer_latex": latex(w),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": [
            {"label": "|w|", "value": rho, "formula": "nth_root_formula"},
            {"label": "arg(w)", "value": theta0, "formula": "nth_root_formula"},
            {"label": "w", "value": w, "formula": "trig_to_algebraic"},
        ],
        # The problem statement needs z (the given number), not w (the answer).
        "given_z": z,
        "given_z_latex": latex(z),
    }
