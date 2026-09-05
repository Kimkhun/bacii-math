"""Complex-number solvers, one module per exercise technique (mirrors the
data layout in backend/data/complex_numbers/{formula_name}.json):

  modulus.py         |z| = sqrt(a^2+b^2)
  argument.py        arg(z) via atan2
  conjugate.py        z̄ = a - bi
  real_imaginary.py   Re(z) / Im(z)
  arithmetic.py       z1 (+|-|*|/) z2
  power.py            z^n, small n, direct algebraic expansion
  de_moivre.py         z^n, large n, via trigonometric form + De Moivre
  nth_roots.py         one n-th root of z (reverse-built from a clean root)

Not yet templated here (heterogeneous forms/proof-style, no single-value
SymPy answer to grade against yet — see docs/generator-variants.md):
"write z in trig form" as its own multi-part exercise, quotient-in-trig-form,
complex equations, locus equations, geometric plotting, and the symmetric-sum
/ Vieta roots-of-unity identities.

``_solve_complex(question_type, params)`` is this package's public entry
point (same name/shape as before the split); ``solver/solver.py`` calls it.
"""
from .arithmetic import _solve_complex_arithmetic
from .argument import _solve_argument
from .conjugate import _solve_conjugate
from .de_moivre import _solve_de_moivre
from .modulus import _solve_modulus
from .nth_roots import _solve_nth_root
from .power import _solve_complex_power
from .real_imaginary import _solve_imag, _solve_real


def _solve_complex(question_type, params):
    if question_type == "modulus":
        return _solve_modulus(params["a"], params["b"])
    if question_type == "argument":
        return _solve_argument(params["a"], params["b"])
    if question_type == "conjugate":
        return _solve_conjugate(params["a"], params["b"])
    if question_type == "real_part":
        return _solve_real(params["a"], params["b"])
    if question_type == "imaginary_part":
        return _solve_imag(params["a"], params["b"])
    if question_type == "complex_arithmetic":
        return _solve_complex_arithmetic(params["a1"], params["b1"], params["a2"], params["b2"], params["operation"])
    if question_type == "complex_power":
        return _solve_complex_power(params["a"], params["b"], params["n"])
    if question_type == "de_moivre_power":
        return _solve_de_moivre(params["r"], params["k"], params["d"], params["n"])
    if question_type == "nth_roots":
        return _solve_nth_root(params["rho"], params["k0"], params["d0"], params["n"])
    raise ValueError(f"unknown question_type: {question_type}")
