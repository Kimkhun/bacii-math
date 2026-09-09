"""Continuity generation: curated real BAC II / textbook exercises loaded once
from data/curated/*.json — the same curated-replay pattern
as limits. SymPy recomputes every limit (or solved parameter) at solve time."""
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


def _locals(item):
    locals_ = {item["var"]: Symbol(item["var"])}
    if item.get("unknown"):
        locals_[item["unknown"]] = Symbol(item["unknown"])
    return locals_


def _build_prompt_latex(item):
    var = item["var"]
    locals_ = _locals(item)
    point_l = latex(sympify(item["point"], locals=locals_))
    left_l = latex(sympify(item["left_expr"], locals=locals_))
    right_l = latex(sympify(item["right_expr"], locals=locals_))
    same_formula = item["left_expr"] == item["right_expr"]

    if same_formula:
        # Removable-discontinuity style: one formula off the point, an explicit
        # value (possibly itself an expression in the unknown) at the point.
        at_point = latex(sympify(item["target_value"], locals=locals_)) if item.get("target_value") else right_l
        piecewise = (
            rf"f({var}) = \begin{{cases}} {left_l} & {var} \neq {point_l} \\ "
            rf"{at_point} & {var} = {point_l} \end{{cases}}"
        )
    else:
        piecewise = (
            rf"f({var}) = \begin{{cases}} {left_l} & {var} < {point_l} \\ "
            rf"{right_l} & {var} \geq {point_l} \end{{cases}}"
        )

    if item.get("unknown"):
        lead = rf"\text{{Find }} {item['unknown']} \text{{ so that }} f \text{{ is continuous at }} {var} = {point_l}:"
    else:
        lead = rf"\text{{Determine whether }} f \text{{ is continuous at }} {var} = {point_l}:"
    return rf"{lead} \\[4pt] {piecewise}"


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
        "prompt_latex": _build_prompt_latex(item),
        "source": "curated",
    }


def _has_unknown(item):
    return item.get("unknown") not in (None, "", "None")


def _generate_continuity(rng, difficulty, question_type=None, variant=None):
    """`variant` targets one of the two shapes this topic really has:
    "check_at_point" (both branches given, decide continuity) or
    "find_parameter" (an unknown constant to solve for). Unknown variants are
    ignored rather than fatal, so a stale practice link still yields a question."""
    if question_type not in (None, "check_continuity"):
        raise ValueError(f"question_type {question_type} does not match topic continuity")
    pool = _CONTINUITY_CURATED
    if variant in ("check_at_point", "find_parameter"):
        want = variant == "find_parameter"
        pool = [t for t in pool if _has_unknown(t) == want] or _CONTINUITY_CURATED
    by_difficulty = [t for t in pool if t.get("difficulty") == difficulty]
    pool = by_difficulty or pool
    if not pool:
        raise ValueError(f"no curated continuity exercises for difficulty {difficulty}")
    return _build_curated_continuity(rng.choice(pool))
