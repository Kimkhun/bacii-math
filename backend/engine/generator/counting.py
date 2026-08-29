"""Combinatorics-counting generation: curated real BAC II / textbook exercises
loaded once from backend/data/probability_counting/*.json. SymPy recomputes
the count at solve time. Separate from the scenario-based probability
generator (engine/generator/probability.py), which handles draw/event
scenarios rather than raw combination/permutation evaluation."""
import json
import os
import re

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "probability_counting")

_COMB_NOTATION = re.compile(r"\bC\(\s*(\d+)\s*,\s*(\d+)\s*\)")
_PERM_NOTATION = re.compile(r"\bP\(\s*(\d+)\s*,\s*(\d+)\s*\)")


def _display_latex(expr):
    """Render the C(n,r)/P(n,r) expression as LaTeX binomial/permutation
    notation WITHOUT evaluating it — sympy's binomial()/factorial() eagerly
    compute on concrete integers, which would leak the answer into the
    question text, so this is pure string substitution instead."""
    text = _COMB_NOTATION.sub(r"\\binom{\1}{\2}", expr)
    text = _PERM_NOTATION.sub(r"A_{\1}^{\2}", text)
    text = text.replace("*", r" \times ")
    return text


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
        "prompt_latex": rf"\text{{Evaluate: }} {_display_latex(item['expr'])}",
        "source": "curated",
    }


def _generate_counting(rng, difficulty):
    pool = [t for t in _COUNTING_CURATED if t.get("difficulty") == difficulty]
    if not pool:
        pool = _COUNTING_CURATED
    if not pool:
        raise ValueError(f"no curated counting exercises for difficulty {difficulty}")
    return _build_curated_counting(rng.choice(pool))
