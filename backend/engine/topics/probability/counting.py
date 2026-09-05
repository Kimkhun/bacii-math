"""Combinatorics-counting: a probability question_type distinct from the
scenario-based draw/event exercises (``solver.py``/``generator.py``).

Generation loads curated real BAC II / textbook exercises once from
``data/counting/*.json``; solving uses SymPy's ``binomial``/``factorial`` to
compute the real combination/permutation count — the curated JSON only
supplies the C(n,r)/P(n,r) expression and the exam-authored technique
narration.
"""
import json
import os
import re

from sympy import binomial, factorial, latex, sympify

from ...core.shared import _formula_tags

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "data", "counting")

_COMB_NOTATION = re.compile(r"\bC\(\s*(\d+)\s*,\s*(\d+)\s*\)")
_PERM_NOTATION = re.compile(r"\bP\(\s*(\d+)\s*,\s*(\d+)\s*\)")


# ---------------------------------------------------------------------------
# Solving
# ---------------------------------------------------------------------------

def _step(title, detail, formula="counting"):
    return {"title": title, "detail": detail, "formula": formula}


def _to_sympy_expr(text):
    text = _COMB_NOTATION.sub(r"binomial(\1, \2)", text)
    text = _PERM_NOTATION.sub(r"(factorial(\1) / factorial(\1 - \2))", text)
    return sympify(text, locals={"binomial": binomial, "factorial": factorial})


def _solve_counting(params):
    raw = params["expr"]
    expr = _to_sympy_expr(raw)
    result = int(expr)

    steps = [
        _step("Set up the counting expression", f"Evaluate \\({raw.replace('*', ' \\times ')}\\)."),
        _step("Apply the technique", params.get("curated_technique", "")),
        _step("Result", f"The count is {result}."),
    ]
    checkpoints = [{"label": "count", "value": result, "formula": "counting"}]
    return {
        "answer_exact": result,
        "answer_decimal": float(result),
        "answer_latex": latex(result),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
    }


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

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
