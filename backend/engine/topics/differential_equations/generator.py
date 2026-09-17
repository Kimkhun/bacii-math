"""Differential-equation generation: curated real BAC II / textbook exercises
from data/curated/*.json mixed with equations built from chosen characteristic
roots and particular solutions. SymPy's dsolve recomputes the solution at solve time."""
import json
import os

from sympy import Symbol, cos, diff, expand, latex, sin, sympify

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


_KINDS = tuple(_KIND_LABEL)
_x = Symbol("x")

_ODE_TECHNIQUE = {
    "first_order_linear_homogeneous":
        "y' + ay = 0 has general solution y = Ce^{-ax}; use the initial condition to find C.",
    "first_order_linear_nonhomogeneous":
        "Solve y' + ay = 0, add a particular solution of the same form as the right-hand side, "
        "then use the initial condition to find C.",
    "second_order_homogeneous_constant_coeff":
        "Solve the characteristic equation r^2 + br + c = 0; distinct, repeated or complex roots give the "
        "form of the general solution, then use the initial conditions to find C1 and C2.",
    "second_order_nonhomogeneous":
        "General solution = homogeneous solution (from r^2 + br + c = 0) + a particular solution shaped like "
        "the right-hand side; then use the initial conditions to find C1 and C2.",
}


def _nz(rng, lo, hi):
    return rng.choice([v for v in range(lo, hi + 1) if v != 0])


def _roots(rng, difficulty):
    """(b, c) of r^2 + br + c from roots chosen first, so every solution is clean."""
    form = {"easy": "distinct", "medium": rng.choice(("distinct", "repeated")),
            "hard": rng.choice(("distinct", "repeated", "complex", "complex"))}[difficulty]
    if form == "distinct":
        r1, r2 = rng.sample([v for v in range(-4, 5)], 2)
        return -(r1 + r2), r1 * r2, form
    if form == "repeated":
        r = _nz(rng, -4, 4)
        return -2 * r, r * r, form
    alpha, beta = rng.randint(-2, 2), rng.randint(1, 4)
    return -2 * alpha, alpha * alpha + beta * beta, form


def _ode_lhs(kind, params, y_p):
    if kind.startswith("first"):
        return expand(diff(y_p, _x) + sympify(params["a"]) * y_p)
    return expand(diff(y_p, _x, 2) + sympify(params["b"]) * diff(y_p, _x) + sympify(params["c"]) * y_p)


def _avoid_trivial_ics(rng, ics, y_p, first_order):
    """Re-roll y(x0) when the initial conditions match the particular solution,
    which would zero every constant and make the answer just y_p."""
    x0 = sympify(ics["x0"])
    while True:
        same_value = sympify(ics["y0"]) == y_p.subs(_x, x0)
        same_slope = first_order or sympify(ics["yp0"]) == diff(y_p, _x).subs(_x, x0)
        if not (same_value and same_slope):
            return
        ics["y0"] = str(rng.randint(-3, 5))


def _sample_ode_item(rng, kind, difficulty):
    params = {"kind": kind, "difficulty": difficulty, "curated_technique": _ODE_TECHNIQUE[kind]}
    ics = {"x0": "0", "y0": str(rng.randint(-3, 5))}
    if kind == "first_order_linear_homogeneous":
        params["a"] = str(_nz(rng, -4, 4) if difficulty == "easy" else _nz(rng, -6, 6))
        if ics["y0"] == "0":
            ics["y0"] = str(_nz(rng, -3, 5))
    elif kind == "first_order_linear_nonhomogeneous":
        a = _nz(rng, -4, 4)
        params["a"] = str(a)
        if difficulty == "easy":
            y_p = _nz(rng, -5, 5)
        elif difficulty == "medium":
            y_p = rng.choice((_nz(rng, -5, 5), _nz(rng, -3, 3) * _x + rng.randint(-4, 4)))
        else:
            y_p = rng.choice((_nz(rng, -3, 3) * _x + rng.randint(-4, 4),
                              _nz(rng, -3, 3) * cos(_x) + rng.randint(-3, 3) * sin(_x)))
        params["rhs"] = str(_ode_lhs(kind, params, sympify(y_p)))
        _avoid_trivial_ics(rng, ics, sympify(y_p), first_order=True)
    else:
        b, c, form = _roots(rng, difficulty)
        params["b"], params["c"] = str(b), str(c)
        ics["yp0"] = str(rng.randint(-5, 5))
        if form == "complex" and b == 0 and rng.random() < 0.4:
            ics["x0"] = "pi/2"
        if kind == "second_order_nonhomogeneous":
            if c == 0:
                c = 1
                params["c"] = "1"
            y_p = rng.choice([
                _nz(rng, -5, 5),
                _nz(rng, -3, 3) * _x + rng.randint(-4, 4),
                _nz(rng, -2, 2) * _x**2 + rng.randint(-3, 3) * _x + rng.randint(-3, 3),
            ] + ([_nz(rng, -3, 3) * cos(2 * _x) + rng.randint(-2, 2) * sin(2 * _x)]
                 if not (b == 0 and c == 4) else []))
            params["rhs"] = str(_ode_lhs(kind, params, sympify(y_p)))
            _avoid_trivial_ics(rng, ics, sympify(y_p), first_order=False)
        else:
            _avoid_trivial_ics(rng, ics, sympify(0), first_order=False)
    params["ics"] = ics
    return params


def generate_ode_for_kind(rng, kind, difficulty="medium"):
    problem = _build_curated_ode(_sample_ode_item(rng, kind, difficulty))
    label = _KIND_LABEL[kind]
    problem["z_display"] = problem["z_latex"] = label
    problem["prompt"] = f"Solve the differential equation: {label} with the given initial conditions."
    problem["source"] = "generated"
    return problem


def _generate_differential_equations(rng, difficulty, question_type=None, variant=None):
    """Half real curated exercises, half procedurally sampled ones. `variant` is
    a `kind` (first/second order, homogeneous or not); unknown variants are ignored."""
    if question_type not in (None, "solve_ode"):
        raise ValueError(f"question_type {question_type} does not match topic differential_equations")
    kind = variant if variant in _KINDS else None
    curated = [t for t in _ODE_CURATED
               if t.get("difficulty") == difficulty and (kind is None or t.get("kind") == kind)]
    if curated and rng.random() < 0.5:
        return _build_curated_ode(rng.choice(curated))
    return generate_ode_for_kind(rng, kind or rng.choice(_KINDS), difficulty)
