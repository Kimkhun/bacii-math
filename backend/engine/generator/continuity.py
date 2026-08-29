"""Continuity generation: curated real BAC II / textbook exercises loaded once
from backend/data/continuity_curated/*.json — the same curated-replay pattern
as limits. SymPy recomputes every limit (or solved parameter) at solve time."""
import json
import os

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "continuity_curated")


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


_CONTINUITY_CURATED = _load()


def _build_prompt(item):
    var = item["var"]
    point = item["point"]
    if item.get("unknown"):
        return (
            f"Find {item['unknown']} so that the piecewise function is continuous at "
            f"{var} = {point}: for {var} < {point}, f({var}) = {item['left_expr']}; "
            f"for {var} ≥ {point}, f({var}) = {item['right_expr']}."
        )
    return (
        f"Check the continuity of the piecewise function at {var} = {point}: "
        f"for {var} < {point}, f({var}) = {item['left_expr']}; "
        f"for {var} ≥ {point}, f({var}) = {item['right_expr']}."
    )


def _build_curated_continuity(item):
    params = dict(item)
    display = f"continuity at {item['var']} = {item['point']} ({item.get('id')})"
    return {
        "topic": "continuity",
        "question_type": "check_continuity",
        "difficulty": item.get("difficulty", "medium"),
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": _build_prompt(item),
        "prompt_latex": None,
        "source": "curated",
    }


def _generate_continuity(rng, difficulty, question_type=None):
    if question_type not in (None, "check_continuity"):
        raise ValueError(f"question_type {question_type} does not match topic continuity")
    pool = [t for t in _CONTINUITY_CURATED if t.get("difficulty") == difficulty]
    if not pool:
        pool = _CONTINUITY_CURATED
    if not pool:
        raise ValueError(f"no curated continuity exercises for difficulty {difficulty}")
    return _build_curated_continuity(rng.choice(pool))
