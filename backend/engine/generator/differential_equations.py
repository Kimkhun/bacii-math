"""Differential-equation generation: curated real BAC II / textbook exercises
loaded once from backend/data/differential_equations_curated/*.json. SymPy's
dsolve recomputes the solution at solve time."""
import json
import os

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "differential_equations_curated")

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


def _build_curated_ode(item):
    params = dict(item)
    display = f"{_KIND_LABEL.get(item['kind'], item['kind'])} ({item.get('id')})"
    return {
        "topic": "differential_equations",
        "question_type": "solve_ode",
        "difficulty": item.get("difficulty", "medium"),
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": f"Solve the differential equation: {display}"
        + (" with the given initial conditions." if item.get("ics") else " (find the general solution)."),
        "prompt_latex": None,
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
