"""Derivative generation: curated real BAC II / textbook exercises loaded once
from data/curated/*.json. SymPy recomputes the derivative
at solve time."""
import json
import os

from sympy import Symbol, latex, sympify

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


def _build_curated_derivative(item):
    params = dict(item)
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


def _generate_derivatives(rng, difficulty, question_type=None):
    if question_type not in (None, "compute_derivative"):
        raise ValueError(f"question_type {question_type} does not match topic derivatives")
    pool = [t for t in _DERIVATIVE_CURATED if t.get("difficulty") == difficulty]
    if not pool:
        pool = _DERIVATIVE_CURATED
    if not pool:
        raise ValueError(f"no curated derivative exercises for difficulty {difficulty}")
    return _build_curated_derivative(rng.choice(pool))
