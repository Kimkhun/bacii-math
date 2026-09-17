"""Combinatorics-counting: a probability question_type distinct from the
scenario-based draw/event exercises (``solver.py``/``generator.py``).

Generation mixes curated real BAC II / textbook exercises from
``data/counting/*.json`` with sampled C(n,r)/P(n,r) expressions; solving uses SymPy's ``binomial``/``factorial`` to
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


_COUNTING_TECHNIQUES = ("combination", "permutation")


def _sample_combination(rng, difficulty):
    if difficulty == "easy":
        n = rng.randint(4, 10)
        return f"C({n},{rng.randint(1, n - 1)})", "Combination: choose r items from n unordered, C(n,r) = n!/(r!(n-r)!)."
    if difficulty == "medium":
        if rng.random() < 0.5:
            n = rng.randint(8, 15)
            return f"C({n},{rng.randint(2, 4)})", "Combination: choose r items from n unordered."
        a, b = rng.sample(range(4, 10), 2)
        k = rng.randint(2, min(a, b))
        return f"C({a},{k})+C({b},{k})", "Sum rule: the two selection cases are mutually exclusive, so add their counts."
    form = rng.choice(["product", "complement", "sum_of_products"])
    if form == "product":
        a, b = rng.randint(4, 9), rng.randint(3, 8)
        return (f"C({a},{rng.randint(1, 3)})*C({b},{rng.randint(1, 3)})",
                "Product rule: make the two independent choices and multiply their counts.")
    if form == "complement":
        n = rng.randint(7, 12)
        k = rng.randint(3, 5)
        m = rng.randint(k, n - 2)
        return (f"C({n},{k})-C({m},{k})",
                "Complement counting: count every selection, then subtract the ones that break the condition.")
    a, b = rng.randint(4, 7), rng.randint(3, 6)
    return (f"C({a},2)*C({b},1)+C({a},3)",
            "Split into exclusive cases, count each with the product rule, then add.")


def _sample_permutation(rng, difficulty):
    if difficulty == "easy":
        n = rng.randint(4, 8)
        return f"P({n},{rng.randint(1, 3)})", "Permutation: arrange r items chosen in order from n, P(n,r) = n!/(n-r)!."
    if difficulty == "medium":
        n = rng.randint(6, 10)
        return f"P({n},{rng.randint(2, 4)})", "Permutation: the order of the chosen items matters."
    a, b = rng.sample(range(4, 10), 2)
    k = rng.randint(2, 3)
    return (f"P({a},{k})+P({b},{k})",
            "Sum rule over two exclusive ordered-arrangement cases.")


_COUNTING_SAMPLERS = {"combination": _sample_combination, "permutation": _sample_permutation}


def generate_counting_for_technique(rng, technique, difficulty="medium"):
    expr, narration = _COUNTING_SAMPLERS[technique](rng, difficulty)
    problem = _build_curated_counting({"difficulty": difficulty, "expr": expr, "curated_technique": narration})
    problem["z_display"] = problem["z_latex"] = f"count {expr}"
    problem["source"] = "generated"
    return problem


def _generate_counting(rng, difficulty, variant=None):
    """Half real curated exercises, half procedurally sampled ones. `variant` is
    the technique the expression exercises ("combination" or "permutation",
    see engine.core.skills). Unknown variants are ignored."""
    from engine.core.skills import counting_variant
    technique = variant if variant in _COUNTING_TECHNIQUES else None
    curated = [t for t in _COUNTING_CURATED
               if t.get("difficulty") == difficulty
               and (technique is None or counting_variant(t.get("expr")) == technique)]
    if curated and rng.random() < 0.5:
        return _build_curated_counting(rng.choice(curated))
    return generate_counting_for_technique(rng, technique or rng.choice(_COUNTING_TECHNIQUES), difficulty)
