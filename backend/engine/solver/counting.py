"""Combinatorics-counting solver (curated BAC II exercises): SymPy's
``binomial`` and ``factorial`` compute the real combination/permutation
counts; the curated JSON only supplies the C(n,r)/P(n,r) expression and the
exam-authored technique narration."""
import re

from sympy import binomial, factorial, latex, sympify

from .shared import _formula_tags

_COMB_NOTATION = re.compile(r"\bC\(\s*(\d+)\s*,\s*(\d+)\s*\)")
_PERM_NOTATION = re.compile(r"\bP\(\s*(\d+)\s*,\s*(\d+)\s*\)")


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
