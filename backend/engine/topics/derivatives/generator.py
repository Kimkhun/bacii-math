"""Derivative generation: curated real BAC II / textbook exercises loaded once
from data/curated/*.json. SymPy recomputes the derivative
at solve time."""
import json
import os

from sympy import Mul, Pow, Symbol, cancel, cos, exp, latex, log, sin, sqrt, sympify, tan

_X = Symbol("x")

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "data", "curated")


def _load():
    pool = []
    try:
        files = sorted(f for f in os.listdir(_CATALOG_DIR) if f.endswith(".json"))
    except OSError:
        files = []
    for fname in files:
        try:
            with open(os.path.join(_CATALOG_DIR, fname), encoding="utf-8") as f:
                items = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(items, list):
            pool.extend(items)
    return pool


_DERIVATIVE_CURATED = _load()

#: One differentiation technique per curated exercise, classified from its
#: expression shape. Mirrors the buckets shown in the admin template
#: inventory (``engine/core/template_shapes.py``), which imports this
#: function rather than duplicating the classification logic.
DERIVATIVE_TECHNIQUES = (
    "polynomial", "chain", "product", "quotient", "radical",
    "trigonometric", "exponential", "logarithm", "second_order",
)


def _derivative_shape(item):
    if item.get("order", 1) == 2:
        return "second_order"
    expr = item.get("expr", "")
    if "log" in expr:
        return "logarithm"
    if "exp" in expr:
        return "exponential"
    if any(fn in expr for fn in ("sin", "cos", "tan")):
        return "trigonometric"
    if "sqrt" in expr:
        return "radical"
    if "/" in expr:
        return "quotient"
    if ")**" in expr:
        return "chain"
    if ")*" in expr or "*(" in expr:
        return "product"
    return "polynomial"


def _build_curated_derivative(item):
    params = dict(item)
    params["technique"] = _derivative_shape(item)
    order = item.get("order", 1)
    label = "second derivative" if order == 2 else "derivative"
    prime = "y''" if order == 2 else "y'"
    expr_l = latex(sympify(item["expr"], locals={item["var"]: Symbol(item["var"])}))
    display = f"{label} of y = {item['expr']} ({item.get('id')})"
    return {
        "topic": "derivatives",
        "question_type": "compute_derivative",
        "difficulty": item.get("difficulty", "medium"),
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": f"Compute the {label} of y = {item['expr']}.",
        "prompt_latex": rf"\text{{Compute }} {prime} \text{{ for }} y = {expr_l}.",
        "source": "curated",
    }


def _nz(rng, lo, hi):
    return rng.choice([v for v in range(lo, hi + 1) if v != 0])


def _sample_polynomial(rng, difficulty):
    degree = {"easy": 2, "medium": 3, "hard": 4}[difficulty]
    coeffs = [_nz(rng, -5, 5)] + [rng.randint(-6, 6) for _ in range(degree)]
    expr = sum(c * _X**(degree - i) for i, c in enumerate(coeffs))
    if difficulty == "hard":
        expr += _nz(rng, -4, 4) / _X
    return expr, 1, "Apply the power rule term by term: (xⁿ)' = n·xⁿ⁻¹."


def _sample_chain(rng, difficulty):
    a, b = _nz(rng, 1, 5), _nz(rng, -6, 6)
    if difficulty == "easy":
        inner, n = a * _X + b, rng.randint(2, 5)
    elif difficulty == "medium":
        inner, n = a * _X**2 + rng.randint(-5, 5) * _X + b, rng.randint(2, 4)
    else:
        inner, n = a * _X**3 + rng.randint(-5, 5) * _X + b, rng.randint(4, 9)
    expr = Pow(inner, n, evaluate=False)
    return expr, 1, "Chain rule: (uⁿ)' = n·u'·uⁿ⁻¹."


def _sample_product(rng, difficulty):
    a, b, c, d = _nz(rng, 1, 4), _nz(rng, -5, 5), _nz(rng, 1, 4), _nz(rng, -5, 5)
    if difficulty == "easy":
        expr = Mul(a * _X + b, c * _X**2 + d, evaluate=False)
    elif difficulty == "medium":
        expr = Mul(_X**rng.randint(2, 3), Pow(c * _X + d, rng.randint(2, 3), evaluate=False), evaluate=False)
    else:
        expr = Mul(Pow(a * _X + b, 2, evaluate=False), Pow(c * _X + d, 3, evaluate=False), evaluate=False)
    return expr, 1, "Product rule: (u·v)' = u'·v + u·v'."


def _sample_quotient(rng, difficulty):
    for _ in range(50):
        a, b, c, d = _nz(rng, -5, 5), rng.randint(-6, 6), _nz(rng, 1, 4), _nz(rng, -6, 6)
        if difficulty == "easy":
            num, den = a * _X + b, c * _X + d
        elif difficulty == "medium":
            num, den = a * _X**2 + b, c * _X + d
        else:
            num = a * _X**2 + rng.randint(-5, 5) * _X + b
            den = c * _X**2 + d
        reduced = cancel(num / den)
        if reduced.is_number or reduced.is_polynomial(_X):
            continue
        return num / den, 1, "Quotient rule: (u/v)' = (u'·v − u·v') / v²."
    raise RuntimeError("could not sample quotient")


def _sample_radical(rng, difficulty):
    a, b = _nz(rng, 1, 9), _nz(rng, -9, 9)
    if difficulty == "easy":
        expr = sqrt(a * _X + b)
    elif difficulty == "medium":
        expr = sqrt(a * _X**2 + rng.randint(-5, 5) * _X + abs(b))
    else:
        expr = Mul(_nz(rng, 1, 3) * _X + _nz(rng, -4, 4), sqrt(a * _X**2 + abs(b)), evaluate=False)
    return expr, 1, "Chain rule through the root: (√u)' = u' / (2√u)."


def _sample_trigonometric(rng, difficulty):
    k, m = _nz(rng, 1, 5), _nz(rng, 1, 5)
    a, b = _nz(rng, -5, 5), _nz(rng, -5, 5)
    if difficulty == "easy":
        expr = a * sin(k * _X) + b * cos(m * _X)
    elif difficulty == "medium":
        expr = rng.choice([
            abs(a) * Mul(_X, cos(k * _X), evaluate=False),
            a * sin(k * _X)**2,
            tan(k * _X + b),
            a * cos(k * _X)**rng.randint(2, 3),
        ])
    else:
        expr = rng.choice([
            Mul(sin(k * _X), cos(m * _X), evaluate=False),
            sin(k * _X) / (abs(a) + cos(k * _X)),
            cos(a * _X**2 + b),
            abs(a) * Mul(_X**2, sin(k * _X), evaluate=False),
        ])
    return expr, 1, "Use (sin u)' = u'·cos u, (cos u)' = −u'·sin u, (tan u)' = u'/cos²u."


def _sample_exponential(rng, difficulty):
    k, a, b = _nz(rng, -4, 4), _nz(rng, -5, 5), _nz(rng, -6, 6)
    if difficulty == "easy":
        expr = a * exp(k * _X) + b * _X
    elif difficulty == "medium":
        expr = Mul(abs(a) * _X + b, exp(k * _X), evaluate=False)
    else:
        expr = rng.choice([
            exp(a * _X**2 + b * _X),
            (exp(abs(k) * _X) - abs(a)) / (exp(abs(k) * _X) + abs(b)),
            Mul(abs(a) * _X**2 + b, exp(k * _X), evaluate=False),
        ])
    return expr, 1, "Use (eᵘ)' = u'·eᵘ, combined with the product/quotient rule where needed."


def _sample_logarithm(rng, difficulty):
    a, b = _nz(rng, 1, 9), _nz(rng, 1, 9)
    if difficulty == "easy":
        expr = rng.choice([log(a * _X + b), _nz(rng, -4, 4) * log(_X) + b * _X])
    elif difficulty == "medium":
        c = _nz(rng, -4, 4)
        expr = rng.choice([
            Mul(a * _X + _nz(rng, -5, 5), log(_X), evaluate=False),
            c * log(a * _X**2 + b),
            log(a * _X + b) + c * _X**2,
        ])
    else:
        c, d = _nz(rng, 1, 4), _nz(rng, -5, 5)
        expr = rng.choice([
            (a * log(_X) + d) / _X**rng.randint(1, 2),
            log((a * _X + b) / (c * _X + d)) if a * d != b * c else log(_X) / _X,
            Pow(log(_X), 2, evaluate=False) - a * log(_X),
        ])
    return expr, 1, "Use (ln u)' = u'/u, combined with the product/quotient rule where needed."


def _sample_second_order(rng, difficulty):
    a, k = _nz(rng, -5, 5), _nz(rng, 1, 4)
    if difficulty == "easy":
        expr = a * _X**3 + rng.randint(-6, 6) * _X**2 + rng.randint(-6, 6) * _X
    elif difficulty == "medium":
        expr = rng.choice([a * sin(k * _X) + _X**2, a * exp(k * _X) - _X**3])
    else:
        expr = rng.choice([
            Mul(abs(a) * _X + _nz(rng, -5, 5), exp(_nz(rng, -3, 3) * _X), evaluate=False),
            abs(a) * Mul(_X**2, log(_X), evaluate=False),
            Mul(exp(_nz(rng, -3, 3) * _X), sin(k * _X), evaluate=False),
            log(abs(a) * _X**2 + k),
        ])
    return expr, 2, "Differentiate once to get y', then differentiate y' again to get y''."


_DERIVATIVE_SAMPLERS = {
    "polynomial": _sample_polynomial,
    "chain": _sample_chain,
    "product": _sample_product,
    "quotient": _sample_quotient,
    "radical": _sample_radical,
    "trigonometric": _sample_trigonometric,
    "exponential": _sample_exponential,
    "logarithm": _sample_logarithm,
    "second_order": _sample_second_order,
}


def generate_derivative_for_technique(rng, technique, difficulty="medium"):
    """One procedurally-sampled exercise for a differentiation technique."""
    expr, order, narration = _DERIVATIVE_SAMPLERS[technique](rng, difficulty)
    item = {
        "id": f"gen_{technique}",
        "difficulty": difficulty,
        "var": "x",
        "expr": str(expr),
        "order": order,
        "curated_technique": narration,
    }
    problem = _build_curated_derivative(item)
    problem["params"]["technique"] = technique
    problem["params"].pop("id", None)
    problem["z_display"] = problem["z_latex"] = problem["z_display"].rsplit(" (", 1)[0]
    problem["source"] = "generated"
    return problem


def _generate_derivatives(rng, difficulty, question_type=None, variant=None):
    """Half real curated BAC II exercises, half procedurally sampled ones.
    `variant` is a differentiation technique (see `DERIVATIVE_TECHNIQUES`) or
    the legacy "order_1"/"order_2". Unknown variants are ignored."""
    if question_type not in (None, "compute_derivative"):
        raise ValueError(f"question_type {question_type} does not match topic derivatives")
    if variant and variant.startswith("order_"):
        pool = [t for t in _DERIVATIVE_CURATED if f"order_{t.get('order', 1)}" == variant]
        pool = [t for t in pool if t.get("difficulty") == difficulty] or pool
        if pool:
            return _build_curated_derivative(rng.choice(pool))
        variant = "second_order" if variant == "order_2" else None

    technique = variant if variant in DERIVATIVE_TECHNIQUES else None
    curated = [
        t for t in _DERIVATIVE_CURATED
        if t.get("difficulty") == difficulty and (technique is None or _derivative_shape(t) == technique)
    ]
    if curated and rng.random() < 0.5:
        return _build_curated_derivative(rng.choice(curated))
    return generate_derivative_for_technique(rng, technique or rng.choice(DERIVATIVE_TECHNIQUES), difficulty)
