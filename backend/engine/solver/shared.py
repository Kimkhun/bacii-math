"""Shared helpers for the topic solvers: question-type constants, complex-number
string formatting, and the small SymPy utilities every ``solver/*`` module uses.

Imports only SymPy so ``engine.structures`` (and the host verify scripts) can
load this package without the Google LLM client stack.
"""
from sympy import E, Symbol, latex, oo, pi, sqrt


QUESTION_TYPES = (
    "modulus", "argument", "conjugate", "real_part", "imaginary_part",
    "complex_arithmetic", "complex_power", "de_moivre_power", "nth_roots",
)

QUESTION_TYPES_BY_TOPIC = {
    "complex": QUESTION_TYPES,
    "limit": ("limit",),
    "integral": ("definite_integral", "indefinite_integral"),
    "probability": ("probability", "counting"),
    "functions": ("study",),
    "continuity": ("check_continuity",),
    "derivatives": ("compute_derivative",),
    "differential_equations": ("solve_ode",),
    "vectors_space": ("vector_ops",),
    "conics": ("classify_conic",),
}

def format_z(a, b):
    if b == 0:
        return str(a)
    if a == 0:
        if b == 1:
            return "i"
        if b == -1:
            return "-i"
        return f"{b}i"
    imag = "" if abs(b) == 1 else str(abs(b))
    sign = "+" if b > 0 else "-"
    return f"{a} {sign} {imag}i"

def z_latex(a, b):
    if b == 0:
        return str(a)
    imag = "" if abs(b) == 1 else str(abs(b))
    if a == 0:
        return ("-" if b < 0 else "") + (imag or "1") + "i"
    sign = "+" if b > 0 else "-"
    return f"{a} {sign} {(imag or '1')}i"

def _calc_locals(var):
    return {var: Symbol(var), "pi": pi, "oo": oo, "sqrt": sqrt, "e": E}

def inline_latex(value) -> str:
    """Wrap a value's LaTeX form in \\( \\) inline-math delimiters, for embedding in
    step 'detail' text that the frontend renders with KaTeX's auto-render."""
    return f"\\({latex(value)}\\)"

def _formula_tags(steps):
    """Ordered, de-duplicated formula ids used across a solution's steps."""
    return list(dict.fromkeys(s["formula"] for s in steps))