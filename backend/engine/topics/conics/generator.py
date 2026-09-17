"""Conics generation: curated real BAC II / textbook exercises from
data/curated/*.json mixed with conics sampled from their standard form (vertex
or centre and axes first, then expanded). SymPy recompletes the square and
reclassifies the conic at solve time."""
import json
import os

from sympy import Symbol, expand, latex, sympify

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "data", "curated")

_ASK_PHRASE = {
    "vertex_x": r"x\text{-coordinate of the vertex}", "vertex_y": r"y\text{-coordinate of the vertex}",
    "p": r"\text{focal parameter } p", "focus_x": r"x\text{-coordinate of the focus}",
    "focus_y": r"y\text{-coordinate of the focus}", "directrix": r"\text{directrix constant}",
    "center_x": r"x\text{-coordinate of the center}", "center_y": r"y\text{-coordinate of the center}",
    "a": r"a \text{ (semi-major/transverse axis length)}", "b": r"b \text{ (semi-minor/conjugate axis length)}",
    "c": r"c \text{ (focal distance)}",
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


_CONICS_CURATED = _load()


def _build_curated_conic(item):
    params = dict(item)
    display = f"conic {item['expr']} = 0, find {item['ask']} ({item.get('id')})"
    expr_l = latex(expand(sympify(item["expr"], locals={"x": Symbol("x"), "y": Symbol("y")})))
    ask_l = _ASK_PHRASE.get(item["ask"], item["ask"])
    prompt_latex = rf"\text{{Given the conic }} {expr_l} = 0, \\[4pt] \text{{find its }} {ask_l}."
    return {
        "topic": "conics",
        "question_type": "classify_conic",
        "difficulty": item.get("difficulty", "medium"),
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": f"Given the conic {item['expr']} = 0, find its {item['ask'].replace('_', ' ')}.",
        "prompt_latex": prompt_latex,
        "source": "curated",
    }


_X, _Y = Symbol("x"), Symbol("y")

_PARABOLA_ASKS = ("vertex_x", "vertex_y", "p", "focus_x", "focus_y", "directrix")
_CENTERED_ASKS = ("center_x", "center_y", "a", "b", "c")
_ASKS = _PARABOLA_ASKS + _CENTERED_ASKS

#: (a, b, c) with integer c: ellipse c² = a² − b², hyperbola c² = a² + b².
_ELLIPSE_TRIPLES = ((5, 4, 3), (5, 3, 4), (10, 8, 6), (10, 6, 8))
_HYPERBOLA_TRIPLES = ((3, 4, 5), (4, 3, 5), (6, 8, 10), (8, 6, 10), (5, 12, 13), (12, 5, 13))


def _offset(rng, difficulty, avoid_zero=False):
    r = {"easy": 3, "medium": 5, "hard": 6}[difficulty]
    values = [v for v in range(-r, r + 1) if not (avoid_zero and v == 0)]
    return rng.choice(values)


def _general_form(expr):
    return str(expand(expr)).replace(" ", "")


def _sample_parabola(rng, ask, difficulty):
    four_p = rng.choice((4, 8, -4, -8) if difficulty == "easy" else (2, 4, 8, 12, -2, -4, -8, -12))
    h = _offset(rng, difficulty, avoid_zero=ask in ("vertex_x", "focus_x", "directrix"))
    k = _offset(rng, difficulty, avoid_zero=ask in ("vertex_y", "focus_y"))
    scale = rng.choice((2, 3)) if difficulty == "hard" else 1
    axis = rng.choice(("x", "y"))
    if axis == "x":
        expr = scale * ((_Y - k) ** 2 - four_p * (_X - h))
        technique = "Complete the square in y, then isolate x to reach (y-k)^2 = 4p(x-h)."
    else:
        expr = scale * ((_X - h) ** 2 - four_p * (_Y - k))
        technique = "Complete the square in x, then isolate y to reach (x-h)^2 = 4p(y-k)."
    if scale != 1:
        technique += " Divide through by the leading coefficient first."
    return _general_form(expr), technique


def _sample_centered(rng, ask, difficulty):
    kind = rng.choice(("ellipse", "hyperbola"))
    triples = _ELLIPSE_TRIPLES if kind == "ellipse" else _HYPERBOLA_TRIPLES
    if ask == "c" or difficulty == "hard":
        a, b, _ = rng.choice(triples[:2] if difficulty == "easy" else triples)
    elif kind == "ellipse":
        b = rng.randint(2, 4)
        a = rng.randint(b + 1, 6)
    else:
        a, b = rng.randint(2, 5), rng.randint(2, 5)
    shifted = difficulty != "easy" or ask in ("center_x", "center_y")
    h = _offset(rng, difficulty, avoid_zero=ask == "center_x") if shifted else 0
    k = _offset(rng, difficulty, avoid_zero=ask == "center_y") if shifted else 0
    X2, Y2 = (_X - h) ** 2, (_Y - k) ** 2
    along_x = rng.random() < 0.5
    if kind == "ellipse":
        expr = (b**2 * X2 + a**2 * Y2 if along_x else a**2 * X2 + b**2 * Y2) - a**2 * b**2
        technique = ("Complete the square in x and y, divide by the constant to reach standard form; "
                     "a is the larger semi-axis and c = sqrt(a^2 - b^2).")
    else:
        expr = (b**2 * X2 - a**2 * Y2 if along_x else b**2 * Y2 - a**2 * X2) - a**2 * b**2
        technique = ("Complete the square in x and y to reach the standard hyperbola form; "
                     "a is under the positive term and c = sqrt(a^2 + b^2).")
    return _general_form(expr), technique


def generate_conic_for_ask(rng, ask, difficulty="medium"):
    sampler = _sample_parabola if ask in _PARABOLA_ASKS else _sample_centered
    expr, technique = sampler(rng, ask, difficulty)
    item = {"difficulty": difficulty, "expr": expr, "ask": ask, "curated_technique": technique}
    problem = _build_curated_conic(item)
    problem["z_display"] = problem["z_latex"] = f"conic {expr} = 0, find {ask}"
    problem["source"] = "generated"
    return problem


def _generate_conics(rng, difficulty, question_type=None, variant=None):
    """Half real curated exercises, half procedurally sampled ones. `variant` is
    an `ask` (vertex_x, center_y, focal parameter p, ...); unknown variants are ignored."""
    if question_type not in (None, "classify_conic"):
        raise ValueError(f"question_type {question_type} does not match topic conics")
    ask = variant if variant in _ASKS else None
    curated = [t for t in _CONICS_CURATED
               if t.get("difficulty") == difficulty and (ask is None or t.get("ask") == ask)]
    if curated and rng.random() < 0.5:
        return _build_curated_conic(rng.choice(curated))
    return generate_conic_for_ask(rng, ask or rng.choice(_ASKS), difficulty)
