"""Combinatorics-counting generation: curated real BAC II / textbook exercises
loaded once from backend/data/probability_counting/*.json. SymPy recomputes
the count at solve time. Separate from the scenario-based probability
generator (engine/generator/probability.py), which handles draw/event
scenarios rather than raw combination/permutation evaluation."""
import json
import os

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "probability_counting")


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


_COUNTING_CURATED = _load()


def _build_curated_counting(item):
    params = dict(item)
    display = f"count {item['expr']} ({item.get('id')})"
    return {
        "topic": "probability",
        "question_type": "counting",
        "difficulty": item.get("difficulty", "medium"),
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": f"Evaluate: {item['expr']}",
        "prompt_latex": None,
        "source": "curated",
    }


def _generate_counting(rng, difficulty):
    pool = [t for t in _COUNTING_CURATED if t.get("difficulty") == difficulty]
    if not pool:
        pool = _COUNTING_CURATED
    if not pool:
        raise ValueError(f"no curated counting exercises for difficulty {difficulty}")
    return _build_curated_counting(rng.choice(pool))
