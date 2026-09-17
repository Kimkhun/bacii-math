"""Continuity generation: curated real BAC II / textbook exercises from
data/curated/*.json mixed with piecewise functions built around a known limit.
SymPy recomputes every limit (or solved parameter) at solve time."""
import json
import os

from sympy import Rational, Symbol, cos, exp, expand, latex, log, sin, sympify, tan

_x = Symbol("x")

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


def _nz(rng, lo, hi):
    return rng.choice([v for v in range(lo, hi + 1) if v != 0])


def _plain(expr):
    return str(expr).replace(" ", "")


def _fmt(expr):
    return str(expand(expr)).replace(" ", "")


def _left_with_limit(rng, difficulty):
    """(left branch, its limit, point, narration) — the left branch is built so
    its limit at the point is a known clean value."""
    if difficulty == "easy":
        p = rng.randint(-3, 4)
        if rng.random() < 0.5:
            a, b = _nz(rng, -4, 4), rng.randint(-5, 5)
            return _fmt(a * _x + b), a * p + b, p, "Polynomial branches are continuous: substitute the point."
        q = rng.choice([v for v in range(-5, 6) if v != -p])
        num = _fmt((_x - p) * (_x + q))
        return (f"({num})/({_fmt(_x - p)})", p + q, p,
                "Factor the numerator and cancel (x - point) before taking the limit.")
    if difficulty == "medium":
        k = _nz(rng, 1, 6)
        form = rng.choice(("sin", "exp", "log", "tan", "factor"))
        if form == "factor":
            p = _nz(rng, -4, 4)
            m = _nz(rng, 1, 3)
            num = _fmt(m * (_x**2 - p**2))
            return f"({num})/({_fmt(_x - p)})", 2 * m * p, p, "Factor the difference of squares and cancel."
        left = {"sin": sin(k * _x) / _x, "exp": (exp(k * _x) - 1) / _x,
                "log": log(1 + k * _x) / _x, "tan": tan(k * _x) / _x}[form]
        return _plain(left), k, 0, "Use the standard limit at 0 (sin u/u, (e^u - 1)/u, ln(1+u)/u, tan u/u all tend to 1)."
    k, m = _nz(rng, 1, 4), _nz(rng, 1, 3)
    form = rng.choice(("one_minus_cos", "x_sin_over_cos", "sin_over_sin", "exp_over_sin"))
    if form == "one_minus_cos":
        return (_plain((1 - cos(k * _x)) / _x**2), Rational(k * k, 2), 0,
                "Use 1 - cos u ~ u^2/2 near 0.")
    if form == "x_sin_over_cos":
        return (_plain(_x * sin(k * _x) / (1 - cos(m * _x))), Rational(2 * k, m * m), 0,
                "Rewrite with the standard limits sin u/u -> 1 and (1 - cos u)/u^2 -> 1/2.")
    if form == "sin_over_sin":
        m = rng.choice([v for v in range(1, 5) if v != k])
        return (_plain(sin(k * _x) / sin(m * _x)), Rational(k, m), 0,
                "Divide top and bottom by x and use sin u/u -> 1.")
    return (_plain((exp(k * _x) - 1) / sin(m * _x)), Rational(k, m), 0,
            "Divide top and bottom by x and use (e^u - 1)/u -> 1 and sin u/u -> 1.")


def _sample_check_at_point(rng, difficulty):
    left, value, p, narration = _left_with_limit(rng, difficulty)
    continuous = rng.random() < 0.5
    target = value if continuous else value + _nz(rng, -3, 3)
    if difficulty == "easy" or rng.random() < 0.5:
        c = _nz(rng, -3, 3)
        right = _fmt(c * _x + (target - c * p))
    else:
        right = str(target)
    return {"left_expr": left, "right_expr": right, "point": str(p), "unknown": None,
            "curated_technique": narration + " Compare the left-hand and right-hand limits."}


def _sample_find_parameter(rng, difficulty):
    u = rng.choice(("a", "k", "m"))
    answer = _nz(rng, -5, 5)
    if difficulty != "hard":
        p = _nz(rng, -3, 3)
        b = rng.randint(-5, 5)
        c, d = _nz(rng, -2, 2), rng.randint(-4, 4)
        e = answer * p + b - (c * p * p + d * p)
        return {"left_expr": _fmt(Symbol(u) * _x + b), "right_expr": _fmt(c * _x**2 + d * _x + e),
                "point": str(p), "unknown": u,
                "curated_technique": f"Both branches are polynomials: set their values at the point equal and solve for {u}."}
    left, value, p, narration = _left_with_limit(rng, "medium" if rng.random() < 0.6 else "hard")
    m = _nz(rng, -3, 3)
    n = value - m * answer
    return {"left_expr": left, "right_expr": _plain(m * Symbol(u) + n), "point": str(p),
            "unknown": u,
            "curated_technique": narration + f" Set the limit equal to the value at the point and solve for {u}."}


_CONTINUITY_SAMPLERS = {"check_at_point": _sample_check_at_point, "find_parameter": _sample_find_parameter}


def generate_continuity_for_variant(rng, variant, difficulty="medium"):
    item = {"difficulty": difficulty, "var": "x", **_CONTINUITY_SAMPLERS[variant](rng, difficulty)}
    problem = _build_curated_continuity(item)
    problem["z_display"] = problem["z_latex"] = f"continuity at x = {item['point']}"
    problem["source"] = "generated"
    return problem


def _generate_continuity(rng, difficulty, question_type=None, variant=None):
    """Half real curated exercises, half procedurally sampled ones. `variant` is
    "check_at_point" (both branches given, decide continuity) or "find_parameter"
    (an unknown constant to solve for). Unknown variants are ignored rather than
    fatal, so a stale practice link still yields a question."""
    if question_type not in (None, "check_continuity"):
        raise ValueError(f"question_type {question_type} does not match topic continuity")
    chosen = variant if variant in _CONTINUITY_SAMPLERS else None
    curated = [t for t in _CONTINUITY_CURATED
               if t.get("difficulty") == difficulty
               and (chosen is None or _has_unknown(t) == (chosen == "find_parameter"))]
    if curated and rng.random() < 0.5:
        return _build_curated_continuity(rng.choice(curated))
    return generate_continuity_for_variant(rng, chosen or rng.choice(tuple(_CONTINUITY_SAMPLERS)), difficulty)
