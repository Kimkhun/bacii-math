"""Shared trig-form machinery for de_moivre.py and nth_roots.py: build a complex
number from a "nice" (r, standard angle) pair so SymPy's cos/sin evaluate to a
closed algebraic form (matching the textbook's own worked examples, e.g.
z = 2+2i*sqrt(3) is r=4, theta=pi/3).

Standard angles are multiples of pi/6 or pi/4 (0, 30, 45, 60, 90, ... degrees),
the same denominators SymPy already has exact cos/sin values for.
"""
from sympy import I, Rational, cos, latex, pi, simplify, sin

# (k, d) pairs meaning theta = k*pi/d, covering every standard angle in [0, 2*pi).
STANDARD_ANGLES = (
    [(k, 6) for k in range(12)]
    + [(k, 4) for k in range(8)]
)
# De-duplicate by actual angle value while keeping (k, d) in lowest terms.
def _reduce(k, d):
    from math import gcd
    g = gcd(k, d) or 1
    return k // g, d // g

_SEEN = {}
for k, d in STANDARD_ANGLES:
    rk, rd = _reduce(k % (2 * d), d)
    _SEEN[(rk, rd)] = True
STANDARD_ANGLES = sorted(_SEEN.keys(), key=lambda kd: kd[0] / kd[1])


def angle_from(k, d):
    return Rational(k, d) * pi


def z_from_polar(r, k, d):
    """z = r*(cos(theta) + i*sin(theta)) as an exact SymPy expression."""
    theta = angle_from(k, d)
    return simplify(r * cos(theta) + r * I * sin(theta))


def principal_kd(k, d):
    """Reduce k/d (in units of pi) to the principal range (-d, d] (i.e. angle in (-pi, pi])."""
    k = k % (2 * d)
    if k > d:
        k -= 2 * d
    return k, d


def angle_latex(k, d):
    k, d = principal_kd(k, d)
    if k == 0:
        return "0"
    sign = "-" if k < 0 else ""
    k = abs(k)
    from math import gcd
    g = gcd(k, d) or 1
    k, d = k // g, d // g
    if d == 1:
        return f"{sign}{k}\\pi" if k != 1 else f"{sign}\\pi"
    coeff = "" if k == 1 else str(k)
    return f"{sign}\\frac{{{coeff}\\pi}}{{{d}}}"

def trig_form_latex(r, k, d):
    return rf"{r}\left(\cos({angle_latex(k, d)}) + i\sin({angle_latex(k, d)})\right)"
