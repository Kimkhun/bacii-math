"""Conics generation: curated real BAC II / textbook exercises loaded once
from backend/data/conics_curated/*.json. SymPy recompletes the square and
reclassifies the conic at solve time."""
import json
import os

from sympy import Symbol, expand, latex, sympify

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "conics_curated")

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


def _generate_conics(rng, difficulty, question_type=None):
    if question_type not in (None, "classify_conic"):
        raise ValueError(f"question_type {question_type} does not match topic conics")
    pool = [t for t in _CONICS_CURATED if t.get("difficulty") == difficulty]
    if not pool:
        pool = _CONICS_CURATED
    if not pool:
        raise ValueError(f"no curated conic exercises for difficulty {difficulty}")
    return _build_curated_conic(rng.choice(pool))
