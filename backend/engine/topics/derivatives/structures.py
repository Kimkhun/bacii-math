"""Derivative structure registry — one entry per parameterized exercise shape.

Mirrors ``engine/topics/limit/structures.py``: every shape the derivatives
topic can produce is a named structure with a ``pattern`` (SymPy syntax,
``{a}``-style slots), a ``pattern_latex`` card header and a ``sampler`` that
draws clean integer slot values. A generated question records which
structure it came from (``params["template_id"]``) and its slot values
(``params["template_params"]``), so a per-structure blueprint (checkpoints,
rubric steps) can be looked up and instantiated for it later.

This registry is the derivatives topic's only question source: every
question is sampled from one of these structures. Two origins:

  * ``origin="sampler"`` — the procedural shapes that used to live inline in
    ``generator.py``'s ``_sample_<technique>`` functions (one structure per
    difficulty/``rng.choice`` branch). The samplers build the exact same
    expressions as before.
  * ``origin="curated"`` — shapes lifted from the textbook BAC II exercises
    that were previously replayed verbatim, now parameterized. Every one of
    those exercises is an instance of some structure here; ``source_labels``
    records which.

``category`` is the practice bucket (one of ``DERIVATIVE_TECHNIQUES``, the
skill/lesson key); ``rule`` is the main differentiation rule the derivation
uses, which is what a blueprint's steps actually follow.

Slot values are nested under ``params["template_params"]`` rather than
spread into ``params`` (as limits does): the grader treats a top-level param
name as a given, so a student line like ``a = 2`` would otherwise be skipped
as a restatement.
"""
import re

from sympy import Mul, Pow, Symbol, cancel, cos, exp, log, sin, sqrt, sympify, tan

_X = Symbol("x")

DERIVATIVE_TECHNIQUES = (
    "polynomial", "chain", "product", "quotient", "radical",
    "trigonometric", "exponential", "logarithm", "second_order",
)


def _nz(rng, lo, hi):
    return rng.choice([v for v in range(lo, hi + 1) if v != 0])


# ---------------------------------------------------------------------------
# Samplers. Each returns (expr, slot_values); `expr` must equal
# `instantiate(struct, slot_values)` (verified by the script).
# ---------------------------------------------------------------------------

# --- polynomial ---

def _poly_coeffs(rng, degree):
    return [_nz(rng, -5, 5)] + [rng.randint(-6, 6) for _ in range(degree)]


def _poly_expr(coeffs):
    degree = len(coeffs) - 1
    return sum(c * _X**(degree - i) for i, c in enumerate(coeffs))


def _poly_slots(coeffs):
    degree = len(coeffs) - 1
    return {f"a{degree - i}": c for i, c in enumerate(coeffs)}


def _s_poly_quadratic(rng):
    c = _poly_coeffs(rng, 2)
    return _poly_expr(c), _poly_slots(c)


def _s_poly_cubic(rng):
    c = _poly_coeffs(rng, 3)
    return _poly_expr(c), _poly_slots(c)


def _s_poly_quartic(rng):
    c = _poly_coeffs(rng, 4)
    return _poly_expr(c), _poly_slots(c)


def _s_poly_quartic_reciprocal(rng):
    c = _poly_coeffs(rng, 4)
    r = _nz(rng, -4, 4)
    return _poly_expr(c) + r / _X, {**_poly_slots(c), "r": r}


# --- chain (power of an expression) ---

def _s_chain_linear_power(rng):
    a, b, n = _nz(rng, 1, 5), _nz(rng, -6, 6), rng.randint(2, 5)
    return Pow(a * _X + b, n, evaluate=False), {"a": a, "b": b, "n": n}


def _s_chain_quadratic_power(rng):
    a, b = _nz(rng, 1, 5), _nz(rng, -6, 6)
    c, n = rng.randint(-5, 5), rng.randint(2, 4)
    return Pow(a * _X**2 + c * _X + b, n, evaluate=False), {"a": a, "b": b, "c": c, "n": n}


def _s_chain_cubic_power(rng):
    a, b = _nz(rng, 1, 5), _nz(rng, -6, 6)
    c, n = rng.randint(-5, 5), rng.randint(4, 9)
    return Pow(a * _X**3 + c * _X + b, n, evaluate=False), {"a": a, "b": b, "c": c, "n": n}


def _s_chain_full_cubic_power(rng):
    a, b, c, d = _nz(rng, 1, 3), _nz(rng, -4, 4), _nz(rng, -6, 6), _nz(rng, -3, 3)
    n = rng.choice([10, 12, 15, 20])
    return Pow(a * _X**3 + b * _X**2 + c * _X + d, n, evaluate=False), {"a": a, "b": b, "c": c, "d": d, "n": n}


def _s_chain_reciprocal_power(rng):
    k, a, b, n = _nz(rng, 1, 8), rng.choice([1, 2, -1, -2]), _nz(rng, -5, 5), rng.randint(1, 3)
    return k / Pow(a * _X + b, n, evaluate=False), {"k": k, "a": a, "b": b, "n": n}


# --- product ---

def _s_product_linear_quadratic(rng):
    a, b, c, d = _nz(rng, 1, 4), _nz(rng, -5, 5), _nz(rng, 1, 4), _nz(rng, -5, 5)
    return Mul(a * _X + b, c * _X**2 + d, evaluate=False), {"a": a, "b": b, "c": c, "d": d}


def _s_product_monomial_linear_power(rng):
    c, d = _nz(rng, 1, 4), _nz(rng, -5, 5)
    m, n = rng.randint(2, 3), rng.randint(2, 3)
    return Mul(_X**m, Pow(c * _X + d, n, evaluate=False), evaluate=False), {"m": m, "c": c, "d": d, "n": n}


def _s_product_two_linear_powers(rng):
    a, b, c, d = _nz(rng, 1, 4), _nz(rng, -5, 5), _nz(rng, 1, 4), _nz(rng, -5, 5)
    expr = Mul(Pow(a * _X + b, 2, evaluate=False), Pow(c * _X + d, 3, evaluate=False), evaluate=False)
    return expr, {"a": a, "b": b, "c": c, "d": d}


def _s_product_three_factors(rng):
    a = _nz(rng, -4, 4)
    b = rng.choice([v for v in range(-4, 5) if v not in (0, a)])
    return Mul(_X**2, _X + a, _X + b, evaluate=False), {"a": a, "b": b}


# --- quotient ---

def _irreducible(num, den):
    reduced = cancel(num / den)
    return not (reduced.is_number or reduced.is_polynomial(_X))


def _s_quotient_linear_linear(rng):
    while True:
        a, b, c, d = _nz(rng, -5, 5), rng.randint(-6, 6), _nz(rng, 1, 4), _nz(rng, -6, 6)
        num, den = a * _X + b, c * _X + d
        if _irreducible(num, den):
            return num / den, {"a": a, "b": b, "c": c, "d": d}


def _s_quotient_quadratic_linear(rng):
    while True:
        a, b, c, d = _nz(rng, -5, 5), rng.randint(-6, 6), _nz(rng, 1, 4), _nz(rng, -6, 6)
        num, den = a * _X**2 + b, c * _X + d
        if _irreducible(num, den):
            return num / den, {"a": a, "b": b, "c": c, "d": d}


def _s_quotient_trinomial_quadratic(rng):
    while True:
        a, b, c, d = _nz(rng, -5, 5), rng.randint(-6, 6), _nz(rng, 1, 4), _nz(rng, -6, 6)
        e = rng.randint(-5, 5)
        num, den = a * _X**2 + e * _X + b, c * _X**2 + d
        if _irreducible(num, den):
            return num / den, {"a": a, "b": b, "c": c, "d": d, "e": e}


def _s_quotient_trinomial_linear(rng):
    while True:
        a, b, c = _nz(rng, 1, 3), rng.randint(-4, 4), _nz(rng, -5, 5)
        p, q = rng.choice([1, 2, -1, -2]), _nz(rng, -4, 4)
        num, den = a * _X**2 + b * _X + c, p * _X + q
        if _irreducible(num, den):
            return num / den, {"a": a, "b": b, "c": c, "p": p, "q": q}


def _s_quotient_linear_quadratic(rng):
    while True:
        a, b, c, d = _nz(rng, 1, 4), _nz(rng, -5, 5), rng.choice([1, 2]), _nz(rng, -9, 9)
        num, den = a * _X + b, c * _X**2 + d
        if _irreducible(num, den):
            return num / den, {"a": a, "b": b, "c": c, "d": d}


# --- radical ---

def _s_radical_sqrt_linear(rng):
    a, b = _nz(rng, 1, 9), _nz(rng, -9, 9)
    return sqrt(a * _X + b), {"a": a, "b": b}


def _s_radical_sqrt_quadratic(rng):
    a, b = _nz(rng, 1, 9), abs(_nz(rng, -9, 9))
    c = rng.randint(-5, 5)
    return sqrt(a * _X**2 + c * _X + b), {"a": a, "b": b, "c": c}


def _s_radical_linear_times_sqrt(rng):
    a, b = _nz(rng, 1, 9), abs(_nz(rng, -9, 9))
    p, q = _nz(rng, 1, 3), _nz(rng, -4, 4)
    return Mul(p * _X + q, sqrt(a * _X**2 + b), evaluate=False), {"a": a, "b": b, "p": p, "q": q}


def _s_radical_sum_of_sqrts(rng):
    a, b, c, d = _nz(rng, 1, 5), _nz(rng, -6, 6), _nz(rng, 1, 5), _nz(rng, -6, 6)
    return sqrt(a * _X + b) + sqrt(c * _X + d), {"a": a, "b": b, "c": c, "d": d}


def _s_radical_linear_plus_sqrt(rng):
    k, a, b = _nz(rng, -3, 3), _nz(rng, 1, 4), _nz(rng, 1, 9)
    return k * _X + sqrt(a * _X**2 + b), {"k": k, "a": a, "b": b}


# --- trigonometric ---

def _s_trig_sin_cos_sum(rng):
    k, m, a, b = _nz(rng, 1, 5), _nz(rng, 1, 5), _nz(rng, -5, 5), _nz(rng, -5, 5)
    return a * sin(k * _X) + b * cos(m * _X), {"a": a, "b": b, "k": k, "m": m}


def _s_trig_x_times_cos(rng):
    a, k = abs(_nz(rng, -5, 5)), _nz(rng, 1, 5)
    return a * Mul(_X, cos(k * _X), evaluate=False), {"a": a, "k": k}


def _s_trig_sin_squared(rng):
    a, k = _nz(rng, -5, 5), _nz(rng, 1, 5)
    return a * sin(k * _X)**2, {"a": a, "k": k}


def _s_trig_tan_linear(rng):
    k, b = _nz(rng, 1, 5), _nz(rng, -5, 5)
    return tan(k * _X + b), {"k": k, "b": b}


def _s_trig_cos_power(rng):
    a, k, n = _nz(rng, -5, 5), _nz(rng, 1, 5), rng.randint(2, 3)
    return a * cos(k * _X)**n, {"a": a, "k": k, "n": n}


def _s_trig_sin_times_cos(rng):
    k, m = _nz(rng, 1, 5), _nz(rng, 1, 5)
    return Mul(sin(k * _X), cos(m * _X), evaluate=False), {"k": k, "m": m}


def _s_trig_sin_over_shifted_cos(rng):
    a, k = abs(_nz(rng, -5, 5)), _nz(rng, 1, 5)
    return sin(k * _X) / (a + cos(k * _X)), {"a": a, "k": k}


def _s_trig_cos_of_quadratic(rng):
    a, b = _nz(rng, -5, 5), _nz(rng, -5, 5)
    return cos(a * _X**2 + b), {"a": a, "b": b}


def _s_trig_x_squared_times_sin(rng):
    a, k = abs(_nz(rng, -5, 5)), _nz(rng, 1, 5)
    return a * Mul(_X**2, sin(k * _X), evaluate=False), {"a": a, "k": k}


def _s_trig_x_squared_times_cos(rng):
    a, k = _nz(rng, 1, 4), _nz(rng, 1, 4)
    return a * Mul(_X**2, cos(k * _X), evaluate=False), {"a": a, "k": k}


def _s_trig_binomial_squared(rng):
    k, m = _nz(rng, 1, 4), _nz(rng, 1, 4)
    return Pow(sin(k * _X) - cos(m * _X), 2, evaluate=False), {"k": k, "m": m}


def _s_trig_linear_times_cos(rng):
    a, b, k = _nz(rng, -4, 4), _nz(rng, -5, 5), _nz(rng, 2, 5)
    return Mul(a * _X + b, cos(k * _X), evaluate=False), {"a": a, "b": b, "k": k}


def _s_trig_tan_over_linear(rng):
    k, a = _nz(rng, 1, 3), _nz(rng, -4, 4)
    return tan(k * _X) / (_X + a), {"k": k, "a": a}


def _s_trig_nested_composition(rng):
    k = _nz(rng, 1, 4)
    return cos(sin(k / _X)), {"k": k}


def _s_trig_quotient_sin_cos(rng):
    a, b = _nz(rng, 1, 5), _nz(rng, -4, 4)
    c, d = _nz(rng, 1, 5), _nz(rng, -3, 3)
    return (a + b * cos(_X)) / (c + d * sin(_X)), {"a": a, "b": b, "c": c, "d": d}


def _s_trig_squared_quotient(rng):
    a = _nz(rng, -3, 3)
    return Pow((sin(_X) + a) / cos(_X), 2, evaluate=False), {"a": a}


# --- exponential ---

def _s_exp_linear_combo(rng):
    k, a, b = _nz(rng, -4, 4), _nz(rng, -5, 5), _nz(rng, -6, 6)
    return a * exp(k * _X) + b * _X, {"a": a, "b": b, "k": k}


def _s_exp_linear_times_exp(rng):
    k, a, b = _nz(rng, -4, 4), abs(_nz(rng, -5, 5)), _nz(rng, -6, 6)
    return Mul(a * _X + b, exp(k * _X), evaluate=False), {"a": a, "b": b, "k": k}


def _s_exp_of_quadratic(rng):
    a, b = _nz(rng, -5, 5), _nz(rng, -6, 6)
    return exp(a * _X**2 + b * _X), {"a": a, "b": b}


def _s_exp_shifted_quotient(rng):
    k, a, b = abs(_nz(rng, -4, 4)), abs(_nz(rng, -5, 5)), abs(_nz(rng, -6, 6))
    return (exp(k * _X) - a) / (exp(k * _X) + b), {"a": a, "b": b, "k": k}


def _s_exp_quadratic_times_exp(rng):
    k, a, b = _nz(rng, -4, 4), abs(_nz(rng, -5, 5)), _nz(rng, -6, 6)
    return Mul(a * _X**2 + b, exp(k * _X), evaluate=False), {"a": a, "b": b, "k": k}


def _s_exp_trinomial_times_exp(rng):
    a, b, c, k = _nz(rng, 1, 3), _nz(rng, -4, 4), _nz(rng, -5, 5), _nz(rng, -3, 3)
    return Mul(a * _X**2 + b * _X + c, exp(k * _X), evaluate=False), {"a": a, "b": b, "c": c, "k": k}


def _s_exp_affine_quotient(rng):
    p, q, k, r = _nz(rng, 1, 4), rng.randint(-4, 4), _nz(rng, 1, 3), _nz(rng, 1, 5)
    if q == p * r:  # numerator would be p·(denominator): a constant quotient
        q = 0
    return (p * exp(k * _X) + q) / (exp(k * _X) + r), {"p": p, "q": q, "k": k, "r": r}


def _s_exp_times_sin(rng):
    k, m = _nz(rng, -3, 3), _nz(rng, 1, 4)
    return Mul(exp(k * _X), sin(m * _X), evaluate=False), {"k": k, "m": m}


def _s_exp_squared_quotient(rng):
    k, q, r = rng.choice([1, -1, 2, -2]), _nz(rng, -3, 3), _nz(rng, 1, 3)
    if q == r:
        q = -r
    return Pow((exp(k * _X) + q) / (exp(k * _X) + r), 2, evaluate=False), {"k": k, "q": q, "r": r}


# --- logarithm ---

def _s_log_of_linear(rng):
    a, b = _nz(rng, 1, 9), _nz(rng, 1, 9)
    return log(a * _X + b), {"a": a, "b": b}


def _s_log_plus_linear(rng):
    c, b = _nz(rng, -4, 4), _nz(rng, 1, 9)
    return c * log(_X) + b * _X, {"b": b, "c": c}


def _s_log_linear_times_log(rng):
    a, d = _nz(rng, 1, 9), _nz(rng, -5, 5)
    return Mul(a * _X + d, log(_X), evaluate=False), {"a": a, "d": d}


def _s_log_of_quadratic(rng):
    a, b, c = _nz(rng, 1, 9), _nz(rng, 1, 9), _nz(rng, -4, 4)
    return c * log(a * _X**2 + b), {"a": a, "b": b, "c": c}


def _s_log_plus_quadratic(rng):
    a, b, c = _nz(rng, 1, 9), _nz(rng, 1, 9), _nz(rng, -4, 4)
    return log(a * _X + b) + c * _X**2, {"a": a, "b": b, "c": c}


def _s_log_over_power(rng):
    a, d, n = _nz(rng, 1, 9), _nz(rng, -5, 5), rng.randint(1, 2)
    return (a * log(_X) + d) / _X**n, {"a": a, "d": d, "n": n}


def _s_log_of_quotient(rng):
    while True:
        a, b, c, d = _nz(rng, 1, 9), _nz(rng, 1, 9), _nz(rng, 1, 4), _nz(rng, -5, 5)
        if a * d != b * c:
            return log((a * _X + b) / (c * _X + d)), {"a": a, "b": b, "c": c, "d": d}


def _s_log_squared_minus_log(rng):
    a = _nz(rng, 1, 9)
    return Pow(log(_X), 2, evaluate=False) - a * log(_X), {"a": a}


def _s_log_x_log_plus_linear(rng):
    a, b = _nz(rng, 1, 4), _nz(rng, -4, 4)
    return a * _X * log(_X) + b * _X, {"a": a, "b": b}


def _s_log_trinomial_times_log(rng):
    a, b, c = _nz(rng, 1, 3), rng.randint(-4, 4), _nz(rng, 1, 5)
    return Mul(a * _X**2 + b * _X + c, log(_X), evaluate=False), {"a": a, "b": b, "c": c}


def _s_log_quadratic_minus_x2_log(rng):
    a, b = _nz(rng, -4, 4), _nz(rng, -3, 3)
    return a * _X**2 + b * _X**2 * log(_X), {"a": a, "b": b}


def _s_log_shifted_self_product(rng):
    a = _nz(rng, -5, 5)
    return Mul(_X + a, log(_X + a), evaluate=False), {"a": a}


def _s_log_of_x_plus_sqrt(rng):
    a = rng.randint(1, 9)
    return log(_X + sqrt(_X**2 + a)), {"a": a}


# --- second order ---

def _s_second_cubic(rng):
    a, b, c = _nz(rng, -5, 5), rng.randint(-6, 6), rng.randint(-6, 6)
    return a * _X**3 + b * _X**2 + c * _X, {"a": a, "b": b, "c": c}


def _s_second_sin_plus_square(rng):
    a, k = _nz(rng, -5, 5), _nz(rng, 1, 4)
    return a * sin(k * _X) + _X**2, {"a": a, "k": k}


def _s_second_exp_minus_cube(rng):
    a, k = _nz(rng, -5, 5), _nz(rng, 1, 4)
    return a * exp(k * _X) - _X**3, {"a": a, "k": k}


def _s_second_linear_times_exp(rng):
    a, b, c = abs(_nz(rng, -5, 5)), _nz(rng, -5, 5), _nz(rng, -3, 3)
    return Mul(a * _X + b, exp(c * _X), evaluate=False), {"a": a, "b": b, "c": c}


def _s_second_x2_log(rng):
    a = abs(_nz(rng, -5, 5))
    return a * Mul(_X**2, log(_X), evaluate=False), {"a": a}


def _s_second_exp_times_sin(rng):
    c, k = _nz(rng, -3, 3), _nz(rng, 1, 4)
    return Mul(exp(c * _X), sin(k * _X), evaluate=False), {"c": c, "k": k}


def _s_second_log_of_quadratic(rng):
    a, k = abs(_nz(rng, -5, 5)), _nz(rng, 1, 4)
    return log(a * _X**2 + k), {"a": a, "k": k}


def _s_second_linear_plus_exp(rng):
    a, b, k = _nz(rng, -5, 5), _nz(rng, -3, 3), _nz(rng, -3, 3)
    return a * _X + b * exp(k * _X), {"a": a, "b": b, "k": k}


def _s_second_quartic_plus_sin(rng):
    a, b, k = _nz(rng, -4, 4), _nz(rng, -3, 3), _nz(rng, 1, 5)
    return a * _X**4 + b * sin(k * _X), {"a": a, "b": b, "k": k}


def _s_second_exp_difference(rng):
    k = _nz(rng, 1, 3)
    return exp(k * _X) - exp(-k * _X), {"k": k}


def _s_second_x2_times_exp(rng):
    a, k = _nz(rng, 1, 4), _nz(rng, -3, 3)
    return a * Mul(_X**2, exp(k * _X), evaluate=False), {"a": a, "k": k}


def _s_second_x2_log_plus_x2(rng):
    a, b = _nz(rng, 1, 4), rng.choice([-2, -1, 1, 2, 3])
    return a * _X**2 * log(_X) + sympify(b) / 2 * _X**2, {"a": a, "b": b}


def _s_second_log_over_x2(rng):
    a, b = _nz(rng, -4, 4), rng.randint(-5, 5)
    return log(_X) / _X**2 + a * _X + b, {"a": a, "b": b}


# ---------------------------------------------------------------------------
# Registry.
# ---------------------------------------------------------------------------

def _st(id_, category, rule, difficulty, pattern, pattern_latex, title_en, sampler,
        narration, order=1, origin="sampler"):
    return {
        "id": f"deriv:{category}:{id_}",
        "question_type": "compute_derivative",
        "category": category,
        "rule": rule,
        "difficulty": difficulty,
        "order": order,
        "pattern": pattern,
        "pattern_latex": pattern_latex,
        "title_en": title_en,
        "var": "x",
        "sampler": sampler,
        "narration": narration,
        "origin": origin,
    }


_POWER = "Apply the power rule term by term: (xⁿ)' = n·xⁿ⁻¹."
_CHAIN = "Chain rule: (uⁿ)' = n·u'·uⁿ⁻¹."
_PRODUCT = "Product rule: (u·v)' = u'·v + u·v'."
_QUOTIENT = "Quotient rule: (u/v)' = (u'·v − u·v') / v²."
_SQRT = "Chain rule through the root: (√u)' = u' / (2√u)."
_TRIG = "Use (sin u)' = u'·cos u, (cos u)' = −u'·sin u, (tan u)' = u'/cos²u."
_EXP = "Use (eᵘ)' = u'·eᵘ, combined with the product/quotient rule where needed."
_LOG = "Use (ln u)' = u'/u, combined with the product/quotient rule where needed."
_SECOND = "Differentiate once to get y', then differentiate y' again to get y''."

DERIVATIVE_STRUCTURES = [
    # --- polynomial ---
    _st("quadratic", "polynomial", "power", "easy",
        "{a2}*x**2 + {a1}*x + {a0}", r"y = a x^{2} + b x + c",
        "Quadratic polynomial", _s_poly_quadratic, _POWER),
    _st("cubic", "polynomial", "power", "medium",
        "{a3}*x**3 + {a2}*x**2 + {a1}*x + {a0}", r"y = a x^{3} + b x^{2} + c x + d",
        "Cubic polynomial", _s_poly_cubic, _POWER),
    _st("quartic_plus_reciprocal", "polynomial", "power", "hard",
        "{a4}*x**4 + {a3}*x**3 + {a2}*x**2 + {a1}*x + {a0} + {r}/x",
        r"y = a x^{4} + b x^{3} + c x^{2} + d x + e + \dfrac{r}{x}",
        "Quartic polynomial plus a reciprocal term", _s_poly_quartic_reciprocal, _POWER),
    _st("quartic", "polynomial", "power", "easy",
        "{a4}*x**4 + {a3}*x**3 + {a2}*x**2 + {a1}*x + {a0}",
        r"y = a x^{4} + b x^{3} + c x^{2} + d x + e",
        "Quartic polynomial", _s_poly_quartic, _POWER, origin="curated"),

    # --- chain ---
    _st("linear_power", "chain", "chain_power", "easy",
        "({a}*x + {b})**{n}", r"y = (a x + b)^{n}",
        "Power of a linear expression", _s_chain_linear_power, _CHAIN),
    _st("quadratic_power", "chain", "chain_power", "medium",
        "({a}*x**2 + {c}*x + {b})**{n}", r"y = (a x^{2} + c x + b)^{n}",
        "Power of a quadratic", _s_chain_quadratic_power, _CHAIN),
    _st("cubic_power", "chain", "chain_power", "hard",
        "({a}*x**3 + {c}*x + {b})**{n}", r"y = (a x^{3} + c x + b)^{n}",
        "High power of a cubic", _s_chain_cubic_power, _CHAIN),
    _st("full_cubic_high_power", "chain", "chain_power", "hard",
        "({a}*x**3 + {b}*x**2 + {c}*x + {d})**{n}", r"y = (a x^{3} + b x^{2} + c x + d)^{n}",
        "Very high power of a full cubic", _s_chain_full_cubic_power,
        "Apply the chain rule with a high power: (u^n)' = n u' u^{n-1}.", origin="curated"),
    _st("reciprocal_power", "chain", "chain_power", "easy",
        "{k}/({a}*x + {b})**{n}", r"y = \dfrac{k}{(a x + b)^{n}}",
        "Constant over a power of a linear expression", _s_chain_reciprocal_power,
        "Rewrite as a power k(ax+b)^{-n} and apply the chain rule.", origin="curated"),

    # --- product ---
    _st("linear_times_quadratic", "product", "product", "easy",
        "({a}*x + {b})*({c}*x**2 + {d})", r"y = (a x + b)(c x^{2} + d)",
        "Linear times quadratic", _s_product_linear_quadratic, _PRODUCT),
    _st("monomial_times_linear_power", "product", "product", "medium",
        "x**{m}*({c}*x + {d})**{n}", r"y = x^{m}(c x + d)^{n}",
        "Power of x times a power of a linear expression", _s_product_monomial_linear_power, _PRODUCT),
    _st("two_linear_powers", "product", "product", "hard",
        "({a}*x + {b})**2*({c}*x + {d})**3", r"y = (a x + b)^{2}(c x + d)^{3}",
        "Product of two powers of linear expressions", _s_product_two_linear_powers, _PRODUCT),
    _st("three_factors", "product", "product", "hard",
        "x**2*(x + {a})*(x + {b})", r"y = x^{2}(x + a)(x + b)",
        "Product of three factors", _s_product_three_factors,
        "Expand or apply the product rule repeatedly across the three factors.", origin="curated"),

    # --- quotient ---
    _st("linear_over_linear", "quotient", "quotient", "easy",
        "({a}*x + {b})/({c}*x + {d})", r"y = \dfrac{a x + b}{c x + d}",
        "Linear over linear", _s_quotient_linear_linear, _QUOTIENT),
    _st("quadratic_over_linear", "quotient", "quotient", "medium",
        "({a}*x**2 + {b})/({c}*x + {d})", r"y = \dfrac{a x^{2} + b}{c x + d}",
        "Quadratic over linear", _s_quotient_quadratic_linear, _QUOTIENT),
    _st("trinomial_over_quadratic", "quotient", "quotient", "hard",
        "({a}*x**2 + {e}*x + {b})/({c}*x**2 + {d})", r"y = \dfrac{a x^{2} + e x + b}{c x^{2} + d}",
        "Trinomial over quadratic", _s_quotient_trinomial_quadratic, _QUOTIENT),
    _st("trinomial_over_linear", "quotient", "quotient", "medium",
        "({a}*x**2 + {b}*x + {c})/({p}*x + {q})", r"y = \dfrac{a x^{2} + b x + c}{p x + q}",
        "Trinomial over linear", _s_quotient_trinomial_linear, _QUOTIENT, origin="curated"),
    _st("linear_over_quadratic", "quotient", "quotient", "medium",
        "({a}*x + {b})/({c}*x**2 + {d})", r"y = \dfrac{a x + b}{c x^{2} + d}",
        "Linear over quadratic", _s_quotient_linear_quadratic, _QUOTIENT, origin="curated"),

    # --- radical ---
    _st("sqrt_linear", "radical", "chain_sqrt", "easy",
        "sqrt({a}*x + {b})", r"y = \sqrt{a x + b}",
        "Square root of a linear expression", _s_radical_sqrt_linear, _SQRT),
    _st("sqrt_quadratic", "radical", "chain_sqrt", "medium",
        "sqrt({a}*x**2 + {c}*x + {b})", r"y = \sqrt{a x^{2} + c x + b}",
        "Square root of a quadratic", _s_radical_sqrt_quadratic, _SQRT),
    _st("linear_times_sqrt", "radical", "product", "hard",
        "({p}*x + {q})*sqrt({a}*x**2 + {b})", r"y = (p x + q)\sqrt{a x^{2} + b}",
        "Linear times a square root", _s_radical_linear_times_sqrt, _SQRT),
    _st("sum_of_sqrts", "radical", "chain_sqrt", "medium",
        "sqrt({a}*x + {b}) + sqrt({c}*x + {d})", r"y = \sqrt{a x + b} + \sqrt{c x + d}",
        "Sum of two square roots", _s_radical_sum_of_sqrts,
        r"Apply the chain rule to each square-root term: (\sqrt u)'=u'/(2\sqrt u).", origin="curated"),
    _st("linear_plus_sqrt", "radical", "chain_sqrt", "hard",
        "{k}*x + sqrt({a}*x**2 + {b})", r"y = k x + \sqrt{a x^{2} + b}",
        "Linear term plus a square root", _s_radical_linear_plus_sqrt,
        "Apply the chain rule to the square-root term, then simplify the sum.", origin="curated"),

    # --- trigonometric ---
    _st("sin_cos_sum", "trigonometric", "trig_basic", "easy",
        "{a}*sin({k}*x) + {b}*cos({m}*x)", r"y = a\sin(k x) + b\cos(m x)",
        "Linear combination of sine and cosine", _s_trig_sin_cos_sum, _TRIG),
    _st("x_times_cos", "trigonometric", "product", "medium",
        "{a}*x*cos({k}*x)", r"y = a x\cos(k x)",
        "x times a cosine", _s_trig_x_times_cos, _TRIG),
    _st("sin_squared", "trigonometric", "chain_power", "medium",
        "{a}*sin({k}*x)**2", r"y = a\sin^{2}(k x)",
        "Square of a sine", _s_trig_sin_squared, _TRIG),
    _st("tan_linear", "trigonometric", "chain", "medium",
        "tan({k}*x + {b})", r"y = \tan(k x + b)",
        "Tangent of a linear expression", _s_trig_tan_linear, _TRIG),
    _st("cos_power", "trigonometric", "chain_power", "medium",
        "{a}*cos({k}*x)**{n}", r"y = a\cos^{n}(k x)",
        "Power of a cosine", _s_trig_cos_power, _TRIG),
    _st("sin_times_cos", "trigonometric", "product", "hard",
        "sin({k}*x)*cos({m}*x)", r"y = \sin(k x)\cos(m x)",
        "Sine times cosine", _s_trig_sin_times_cos, _TRIG),
    _st("sin_over_shifted_cos", "trigonometric", "quotient", "hard",
        "sin({k}*x)/({a} + cos({k}*x))", r"y = \dfrac{\sin(k x)}{a + \cos(k x)}",
        "Sine over a shifted cosine", _s_trig_sin_over_shifted_cos, _TRIG),
    _st("cos_of_quadratic", "trigonometric", "chain", "hard",
        "cos({a}*x**2 + {b})", r"y = \cos(a x^{2} + b)",
        "Cosine of a quadratic", _s_trig_cos_of_quadratic, _TRIG),
    _st("x_squared_times_sin", "trigonometric", "product", "hard",
        "{a}*x**2*sin({k}*x)", r"y = a x^{2}\sin(k x)",
        "x squared times a sine", _s_trig_x_squared_times_sin, _TRIG),
    _st("x_squared_times_cos", "trigonometric", "product", "medium",
        "{a}*x**2*cos({k}*x)", r"y = a x^{2}\cos(k x)",
        "x squared times a cosine", _s_trig_x_squared_times_cos,
        r"Apply the product rule to x^2 and \cos x.", origin="curated"),
    _st("binomial_squared", "trigonometric", "chain_power", "hard",
        "(sin({k}*x) - cos({m}*x))**2", r"y = \big(\sin(k x) - \cos(m x)\big)^{2}",
        "Square of a sine-cosine difference", _s_trig_binomial_squared,
        "Apply the chain rule to the squared trig binomial.", origin="curated"),
    _st("linear_times_cos", "trigonometric", "product", "hard",
        "({a}*x + {b})*cos({k}*x)", r"y = (a x + b)\cos(k x)",
        "Linear times a cosine", _s_trig_linear_times_cos,
        r"Apply the product rule combined with the chain rule on \cos(kx).", origin="curated"),
    _st("tan_over_linear", "trigonometric", "quotient", "hard",
        "tan({k}*x)/(x + {a})", r"y = \dfrac{\tan(k x)}{x + a}",
        "Tangent over a linear expression", _s_trig_tan_over_linear,
        r"Apply the quotient rule with (\tan x)'=1+\tan^2x.", origin="curated"),
    _st("nested_composition", "trigonometric", "chain", "medium",
        "cos(sin({k}/x))", r"y = \cos\!\left(\sin\dfrac{k}{x}\right)",
        "Nested composition (three layers)", _s_trig_nested_composition,
        "Apply the chain rule twice, from the outside in.", origin="curated"),
    _st("quotient_sin_cos", "trigonometric", "quotient", "medium",
        "({a} + {b}*cos(x))/({c} + {d}*sin(x))", r"y = \dfrac{a + b\cos x}{c + d\sin x}",
        "Quotient of trigonometric expressions", _s_trig_quotient_sin_cos,
        "Apply the quotient rule with trig derivatives on both numerator and denominator.",
        origin="curated"),
    _st("squared_quotient", "trigonometric", "chain_power", "hard",
        "((sin(x) + {a})/cos(x))**2", r"y = \left(\dfrac{\sin x + a}{\cos x}\right)^{2}",
        "Square of a trigonometric quotient", _s_trig_squared_quotient,
        "Apply the chain rule to the squared quotient, then the quotient rule inside.",
        origin="curated"),

    # --- exponential ---
    _st("linear_combo", "exponential", "exp_basic", "easy",
        "{a}*exp({k}*x) + {b}*x", r"y = a e^{k x} + b x",
        "Exponential plus a linear term", _s_exp_linear_combo, _EXP),
    _st("linear_times_exp", "exponential", "product", "medium",
        "({a}*x + {b})*exp({k}*x)", r"y = (a x + b)e^{k x}",
        "Linear times an exponential", _s_exp_linear_times_exp, _EXP),
    _st("exp_of_quadratic", "exponential", "chain", "hard",
        "exp({a}*x**2 + {b}*x)", r"y = e^{a x^{2} + b x}",
        "Exponential of a quadratic", _s_exp_of_quadratic, _EXP),
    _st("shifted_quotient", "exponential", "quotient", "hard",
        "(exp({k}*x) - {a})/(exp({k}*x) + {b})", r"y = \dfrac{e^{k x} - a}{e^{k x} + b}",
        "Quotient of shifted exponentials", _s_exp_shifted_quotient, _EXP),
    _st("quadratic_times_exp", "exponential", "product", "hard",
        "({a}*x**2 + {b})*exp({k}*x)", r"y = (a x^{2} + b)e^{k x}",
        "Quadratic times an exponential", _s_exp_quadratic_times_exp, _EXP),
    _st("trinomial_times_exp", "exponential", "product", "hard",
        "({a}*x**2 + {b}*x + {c})*exp({k}*x)", r"y = (a x^{2} + b x + c)e^{k x}",
        "Trinomial times an exponential", _s_exp_trinomial_times_exp,
        "Apply the product rule to a quadratic factor times e^x.", origin="curated"),
    _st("affine_quotient", "exponential", "quotient", "medium",
        "({p}*exp({k}*x) + {q})/(exp({k}*x) + {r})", r"y = \dfrac{p e^{k x} + q}{e^{k x} + r}",
        "Quotient of affine exponentials", _s_exp_affine_quotient,
        "Apply the quotient rule with (e^{kx})'=k e^{kx}.", origin="curated"),
    _st("exp_times_sin", "exponential", "product", "hard",
        "exp({k}*x)*sin({m}*x)", r"y = e^{k x}\sin(m x)",
        "Exponential times a sine", _s_exp_times_sin,
        r"Apply the product rule to e^{kx} and \sin(mx).", origin="curated"),
    _st("squared_quotient", "exponential", "chain_power", "hard",
        "((exp({k}*x) + {q})/(exp({k}*x) + {r}))**2",
        r"y = \left(\dfrac{e^{k x} + q}{e^{k x} + r}\right)^{2}",
        "Square of an exponential quotient", _s_exp_squared_quotient,
        "Apply the chain rule to the squared quotient, then the quotient rule inside.",
        origin="curated"),

    # --- logarithm ---
    _st("log_of_linear", "logarithm", "chain", "easy",
        "log({a}*x + {b})", r"y = \ln(a x + b)",
        "Logarithm of a linear expression", _s_log_of_linear, _LOG),
    _st("log_plus_linear", "logarithm", "log_basic", "easy",
        "{c}*log(x) + {b}*x", r"y = c\ln x + b x",
        "Logarithm plus a linear term", _s_log_plus_linear, _LOG),
    _st("linear_times_log", "logarithm", "product", "medium",
        "({a}*x + {d})*log(x)", r"y = (a x + d)\ln x",
        "Linear times a logarithm", _s_log_linear_times_log, _LOG),
    _st("log_of_quadratic", "logarithm", "chain", "medium",
        "{c}*log({a}*x**2 + {b})", r"y = c\ln(a x^{2} + b)",
        "Logarithm of a quadratic", _s_log_of_quadratic, _LOG),
    _st("log_plus_quadratic", "logarithm", "chain", "medium",
        "log({a}*x + {b}) + {c}*x**2", r"y = \ln(a x + b) + c x^{2}",
        "Logarithm plus a quadratic term", _s_log_plus_quadratic, _LOG),
    _st("log_over_power", "logarithm", "quotient", "hard",
        "({a}*log(x) + {d})/x**{n}", r"y = \dfrac{a\ln x + d}{x^{n}}",
        "Logarithmic expression over a power of x", _s_log_over_power, _LOG),
    _st("log_of_quotient", "logarithm", "log_split", "hard",
        "log(({a}*x + {b})/({c}*x + {d}))", r"y = \ln\dfrac{a x + b}{c x + d}",
        "Logarithm of a quotient", _s_log_of_quotient, _LOG),
    _st("log_squared_minus_log", "logarithm", "chain_power", "hard",
        "log(x)**2 - {a}*log(x)", r"y = \ln^{2}x - a\ln x",
        "Square of a logarithm minus a logarithm", _s_log_squared_minus_log, _LOG),
    _st("x_log_plus_linear", "logarithm", "product", "medium",
        "{a}*x*log(x) + {b}*x", r"y = a x\ln x + b x",
        "x ln x plus a linear term", _s_log_x_log_plus_linear,
        r"Apply the product rule with (\ln x)'=1/x.", origin="curated"),
    _st("trinomial_times_log", "logarithm", "product", "hard",
        "({a}*x**2 + {b}*x + {c})*log(x)", r"y = (a x^{2} + b x + c)\ln x",
        "Trinomial times a logarithm", _s_log_trinomial_times_log,
        r"Apply the product rule to a quadratic factor times \ln x.", origin="curated"),
    _st("quadratic_plus_x2_log", "logarithm", "product", "medium",
        "{a}*x**2 + {b}*x**2*log(x)", r"y = a x^{2} + b x^{2}\ln x",
        "x squared plus x squared ln x", _s_log_quadratic_minus_x2_log,
        r"Apply the product rule to the x^2 \ln x term, then combine with the power rule.",
        origin="curated"),
    _st("shifted_self_product", "logarithm", "product", "medium",
        "(x + {a})*log(x + {a})", r"y = (x + a)\ln(x + a)",
        "(x + a) times ln(x + a)", _s_log_shifted_self_product,
        r"Apply the product rule with (\ln(x+a))'=1/(x+a).", origin="curated"),
    _st("log_of_x_plus_sqrt", "logarithm", "chain", "hard",
        "log(x + sqrt(x**2 + {a}))", r"y = \ln\!\left(x + \sqrt{x^{2} + a}\right)",
        "Logarithm of x plus a square root", _s_log_of_x_plus_sqrt,
        "Apply the chain rule to the log of a sum involving a square root.", origin="curated"),

    # --- second order ---
    _st("cubic", "second_order", "second", "easy",
        "{a}*x**3 + {b}*x**2 + {c}*x", r"y = a x^{3} + b x^{2} + c x",
        "Second derivative of a cubic", _s_second_cubic, _SECOND, order=2),
    _st("sin_plus_square", "second_order", "second", "medium",
        "{a}*sin({k}*x) + x**2", r"y = a\sin(k x) + x^{2}",
        "Second derivative of a sine plus x squared", _s_second_sin_plus_square, _SECOND, order=2),
    _st("exp_minus_cube", "second_order", "second", "medium",
        "{a}*exp({k}*x) - x**3", r"y = a e^{k x} - x^{3}",
        "Second derivative of an exponential minus x cubed", _s_second_exp_minus_cube, _SECOND, order=2),
    _st("linear_times_exp", "second_order", "second", "hard",
        "({a}*x + {b})*exp({c}*x)", r"y = (a x + b)e^{c x}",
        "Second derivative of linear times exponential", _s_second_linear_times_exp, _SECOND, order=2),
    _st("x2_log", "second_order", "second", "hard",
        "{a}*x**2*log(x)", r"y = a x^{2}\ln x",
        "Second derivative of x squared ln x", _s_second_x2_log, _SECOND, order=2),
    _st("exp_times_sin", "second_order", "second", "hard",
        "exp({c}*x)*sin({k}*x)", r"y = e^{c x}\sin(k x)",
        "Second derivative of exponential times sine", _s_second_exp_times_sin, _SECOND, order=2),
    _st("log_of_quadratic", "second_order", "second", "hard",
        "log({a}*x**2 + {k})", r"y = \ln(a x^{2} + k)",
        "Second derivative of a logarithm of a quadratic", _s_second_log_of_quadratic, _SECOND, order=2),
    _st("linear_plus_exp", "second_order", "second", "medium",
        "{a}*x + {b}*exp({k}*x)", r"y = a x + b e^{k x}",
        "Second derivative of a linear term plus an exponential", _s_second_linear_plus_exp,
        "Differentiate twice: y''=(y')'.", order=2, origin="curated"),
    _st("quartic_plus_sin", "second_order", "second", "medium",
        "{a}*x**4 + {b}*sin({k}*x)", r"y = a x^{4} + b\sin(k x)",
        "Second derivative of x to the fourth plus a sine", _s_second_quartic_plus_sin,
        r"Differentiate twice, applying the chain rule to \sin(kx) each time.", order=2, origin="curated"),
    _st("exp_difference", "second_order", "second", "hard",
        "exp({k}*x) - exp(-{k}*x)", r"y = e^{k x} - e^{-k x}",
        "Second derivative of a difference of exponentials", _s_second_exp_difference,
        "Differentiate twice, applying the chain rule to each exponential.", order=2, origin="curated"),
    _st("x2_times_exp", "second_order", "second", "hard",
        "{a}*x**2*exp({k}*x)", r"y = a x^{2}e^{k x}",
        "Second derivative of x squared times an exponential", _s_second_x2_times_exp,
        "Differentiate the first derivative again (apply the product rule twice).", order=2, origin="curated"),
    _st("x2_log_plus_x2", "second_order", "second", "hard",
        "{a}*x**2*log(x) + {b}/2*x**2", r"y = a x^{2}\ln x + \dfrac{b}{2}x^{2}",
        "Second derivative of x squared ln x plus x squared", _s_second_x2_log_plus_x2,
        "Differentiate twice, simplifying the logarithmic term each time.", order=2, origin="curated"),
    _st("log_over_x2", "second_order", "second", "hard",
        "log(x)/x**2 + {a}*x + {b}", r"y = \dfrac{\ln x}{x^{2}} + a x + b",
        "Second derivative of ln x over x squared plus a linear term", _s_second_log_over_x2,
        "Differentiate twice, applying the quotient rule on the first pass.", order=2, origin="curated"),
]

STRUCTURES_BY_ID = {s["id"]: s for s in DERIVATIVE_STRUCTURES}


# ---------------------------------------------------------------------------
# Provenance: the textbook exercises (page_number ids) each structure was
# lifted from or reproduces. Informational only — shown on the admin card.
# ---------------------------------------------------------------------------

_SOURCE_LABELS = {
    "deriv:polynomial:cubic": ["p22_1", "p22_1c"],
    "deriv:polynomial:quadratic": ["p22_1b"],
    "deriv:polynomial:quartic": ["p22_1d"],
    "deriv:chain:quadratic_power": ["p22_2", "p22_2b"],
    "deriv:chain:full_cubic_high_power": ["p22_2c"],
    "deriv:radical:sum_of_sqrts": ["p22_3"],
    "deriv:radical:sqrt_quadratic": ["p22_3b"],
    "deriv:radical:linear_plus_sqrt": ["p22_3c"],
    "deriv:quotient:linear_over_quadratic": ["p22_4"],
    "deriv:quotient:trinomial_over_linear": ["p22_4b", "p22_4c", "p121_28"],
    "deriv:product:monomial_times_linear_power": ["p22_5"],
    "deriv:product:three_factors": ["p22_5b"],
    "deriv:chain:reciprocal_power": ["p22_6", "p22_6b"],
    "deriv:trigonometric:sin_cos_sum": ["p24_7", "p24_7b"],
    "deriv:trigonometric:sin_squared": ["p24_8"],
    "deriv:trigonometric:binomial_squared": ["p24_8b", "p121_30"],
    "deriv:trigonometric:x_squared_times_cos": ["p24_9"],
    "deriv:trigonometric:linear_times_cos": ["p24_9b"],
    "deriv:trigonometric:tan_over_linear": ["p24_10"],
    "deriv:exponential:linear_combo": ["p24_11"],
    "deriv:exponential:linear_times_exp": ["p24_12", "p24_12b"],
    "deriv:exponential:trinomial_times_exp": ["p24_12c"],
    "deriv:exponential:affine_quotient": ["p24_13", "p121_33"],
    "deriv:exponential:exp_times_sin": ["p24_14"],
    "deriv:logarithm:x_log_plus_linear": ["p24_15"],
    "deriv:logarithm:trinomial_times_log": ["p24_15b"],
    "deriv:logarithm:log_over_power": ["p24_16"],
    "deriv:logarithm:log_squared_minus_log": ["p24_16b", "p52_24"],
    "deriv:logarithm:log_of_quotient": ["p24_17", "p52_26"],
    "deriv:second_order:linear_plus_exp": ["p26_18"],
    "deriv:second_order:quartic_plus_sin": ["p26_19"],
    "deriv:second_order:exp_difference": ["p26_20"],
    "deriv:second_order:x2_times_exp": ["p26_21"],
    "deriv:second_order:x2_log_plus_x2": ["p26_22"],
    "deriv:second_order:log_over_x2": ["p26_23"],
    "deriv:logarithm:quadratic_plus_x2_log": ["p52_25"],
    "deriv:chain:cubic_power": ["p121_27"],
    "deriv:trigonometric:nested_composition": ["p121_29"],
    "deriv:trigonometric:quotient_sin_cos": ["p121_31"],
    "deriv:trigonometric:squared_quotient": ["p121_32"],
    "deriv:exponential:squared_quotient": ["p121_34"],
    "deriv:logarithm:shifted_self_product": ["p121_35"],
    "deriv:logarithm:log_of_x_plus_sqrt": ["p121_36"],
}

for _s in DERIVATIVE_STRUCTURES:
    _s["source_labels"] = _SOURCE_LABELS.get(_s["id"], [])


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

_SLOT_RE = re.compile(r"\{(\w+)\}")


def slot_names(struct):
    return list(dict.fromkeys(_SLOT_RE.findall(struct["pattern"])))


def instantiate(struct, slot_values):
    """The structure's pattern with `slot_values` substituted — symbolically
    (slots become SymPy symbols, then `.subs`), never by pasting text, so
    negative or multi-digit values can't corrupt the expression."""
    names = slot_names(struct)
    missing = [n for n in names if n not in slot_values]
    if missing:
        raise KeyError(f"{struct['id']}: missing slot values {missing}")
    symbols = {n: Symbol(f"_slot_{n}") for n in names}
    text = _SLOT_RE.sub(lambda m: f"_slot_{m.group(1)}", struct["pattern"])
    expr = sympify(text, locals={"x": _X, **{f"_slot_{n}": s for n, s in symbols.items()}})
    return expr.subs({symbols[n]: sympify(slot_values[n]) for n in names})


def all_derivative_structures():
    return list(DERIVATIVE_STRUCTURES)
