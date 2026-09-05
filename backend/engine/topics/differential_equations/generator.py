"""Differential-equation generation: curated real BAC II / textbook exercises
loaded once from data/curated/*.json. SymPy's
dsolve recomputes the solution at solve time."""
import json
import os

from sympy import Symbol, latex, sympify

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "data", "curated")

_KIND_LABEL = {
    "first_order_linear_homogeneous": "y' + a y = 0",
    "first_order_linear_nonhomogeneous": "y' + a y = g(x)",
    "second_order_homogeneous_constant_coeff": "y'' + b y' + c y = 0",
    "second_order_nonhomogeneous": "y'' + b y' + c y = g(x)",
}


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


_ODE_CURATED = _load()


def _term(coeff_str, symbol, first):
    """Render one 'coeff * symbol' term with a leading sign, e.g. '- 4y'' or
    '+ y'. Returns '' if the coefficient is zero."""
    c = sympify(coeff_str)
    if c == 0:
        return ""
    sign = "-" if c < 0 else ("" if first else "+")
    mag = abs(c)
    mag_str = "" if mag == 1 else latex(mag)
    spacer = " " if not first else ""
    return f"{spacer}{sign} {mag_str}{symbol}".replace("  ", " ")


def _equation_latex(item):
    kind = item["kind"]
    locals_ = {"x": Symbol("x")}
    if kind in ("first_order_linear_homogeneous", "first_order_linear_nonhomogeneous"):
        a_term = _term(item["a"], "y", first=False)
        lhs = f"y'{a_term}" if a_term else "y'"
        rhs = "0" if kind == "first_order_linear_homogeneous" else latex(sympify(item.get("rhs", 0), locals=locals_))
        return rf"{lhs} = {rhs}"

    b_term = _term(item["b"], "y'", first=False)
    c_term = _term(item["c"], "y", first=False)
    lhs = f"y''{b_term}{c_term}"
    rhs = latex(sympify(item.get("rhs", 0), locals=locals_)) if kind == "second_order_nonhomogeneous" else "0"
    return rf"{lhs} = {rhs}"


def _ics_latex(ics):
    if not ics:
        return None
    x0_l = latex(sympify(ics["x0"]))
    y0_l = latex(sympify(ics["y0"]))
    parts = [rf"y({x0_l}) = {y0_l}"]
    if ics.get("yp0") is not None:
        yp0_l = latex(sympify(ics["yp0"]))
        parts.append(rf"y'({x0_l}) = {yp0_l}")
    return r",\ ".join(parts)


def _build_curated_ode(item):
    params = dict(item)
    display = f"{_KIND_LABEL.get(item['kind'], item['kind'])} ({item.get('id')})"
    eq_l = _equation_latex(item)
    ics_l = _ics_latex(item.get("ics"))
    prompt_latex = rf"\text{{Solve: }} {eq_l}" + (rf"\\[4pt] \text{{with }} {ics_l}." if ics_l else r"\text{ (general solution).}")
    return {
        "topic": "differential_equations",
        "question_type": "solve_ode",
        "difficulty": item.get("difficulty", "medium"),
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": f"Solve the differential equation: {display}"
        + (" with the given initial conditions." if item.get("ics") else " (find the general solution)."),
        "prompt_latex": prompt_latex,
        "source": "curated",
    }


def _generate_differential_equations(rng, difficulty, question_type=None):
    if question_type not in (None, "solve_ode"):
        raise ValueError(f"question_type {question_type} does not match topic differential_equations")
    pool = [t for t in _ODE_CURATED if t.get("difficulty") == difficulty]
    if not pool:
        pool = _ODE_CURATED
    if not pool:
        raise ValueError(f"no curated differential-equation exercises for difficulty {difficulty}")
    return _build_curated_ode(rng.choice(pool))
