"""Complex-number solvers, one module per exercise technique (see the topic
package's ``__init__.py`` for the file map).

Not yet templated here (heterogeneous forms/proof-style, no single-value
SymPy answer to grade against yet — see docs/generator-variants.md):
"write z in trig form" as its own multi-part exercise, quotient-in-trig-form,
complex equations, locus equations, geometric plotting, and the symmetric-sum
/ Vieta roots-of-unity identities.

``_solve_complex(question_type, params)`` is this topic's public entry point;
``engine.core.dispatch.solve()`` calls it.
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
