"""3D vector generation: curated real BAC II / textbook exercises loaded once
from data/curated/*.json. SymPy Matrix operations
recompute the result at solve time."""
import json
import os

from sympy import Symbol, latex, sympify

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "data", "curated")

_OP_LABEL = {
    "magnitude": "|AB|", "distance": "AB", "dot": "AB . AC", "cross_magnitude": "|AB x AC|",
    "triangle_area": "area of triangle ABC", "scalar_triple_product": "u.(v x w)",
    "find_m_orthogonal": "m such that u.v = 0",
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


_VECTORS_CURATED = _load()


def _coords(vals, unknown=None):
    locals_ = {unknown: Symbol(unknown)} if unknown else {}
    parts = [latex(sympify(v, locals=locals_)) if isinstance(v, str) else str(v) for v in vals]
    return ", ".join(parts)


def _point(name, vals):
    return rf"{name}({_coords(vals)})"


def _build_prompt_latex(item):
    op = item["op"]
    if op in ("magnitude", "distance"):
        target = r"|\overrightarrow{AB}|" if op == "magnitude" else "AB"
        return rf"{_point('A', item['A'])},\ {_point('B', item['B'])}. \\[4pt] \text{{Find }} {target}."
    if op == "dot":
        return (rf"{_point('A', item['A'])},\ {_point('B', item['B'])},\ {_point('C', item['C'])}. "
                rf"\\[4pt] \text{{Find }} \overrightarrow{{AB}}\cdot\overrightarrow{{AC}}.")
    if op == "cross_magnitude":
        return (rf"{_point('A', item['A'])},\ {_point('B', item['B'])},\ {_point('C', item['C'])}. "
                rf"\\[4pt] \text{{Find }} |\overrightarrow{{AB}}\times\overrightarrow{{AC}}|.")
    if op == "triangle_area":
        return (rf"{_point('A', item['A'])},\ {_point('B', item['B'])},\ {_point('C', item['C'])}. "
                rf"\\[4pt] \text{{Find the area of triangle }} ABC.")
    if op == "scalar_triple_product":
        u, v, w = _coords(item["u"]), _coords(item["v"]), _coords(item["w"])
        return (rf"\vec u({u}),\ \vec v({v}),\ \vec w({w}). "
                rf"\\[4pt] \text{{Find }} \vec u\cdot(\vec v\times\vec w).")
    if op == "find_m_orthogonal":
        unknown = item["unknown"]
        u = _coords(item["u"], unknown)
        v = _coords(item["v"], unknown)
        return (rf"\vec u({u}),\ \vec v({v}). "
                rf"\\[4pt] \text{{Find }} {unknown} \text{{ such that }} \vec u\cdot\vec v = 0.")
    return None


def _build_curated_vector(item):
    params = dict(item)
    label = _OP_LABEL.get(item["op"], item["op"])
    display = f"{label} ({item.get('id')})"
    return {
        "topic": "vectors_space",
        "question_type": "vector_ops",
        "difficulty": item.get("difficulty", "medium"),
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": f"Compute {label} for the given points/vectors.",
        "prompt_latex": _build_prompt_latex(item),
        "source": "curated",
    }


def _generate_vectors_space(rng, difficulty, question_type=None):
    if question_type not in (None, "vector_ops"):
        raise ValueError(f"question_type {question_type} does not match topic vectors_space")
    pool = [t for t in _VECTORS_CURATED if t.get("difficulty") == difficulty]
    if not pool:
        pool = _VECTORS_CURATED
    if not pool:
        raise ValueError(f"no curated vector exercises for difficulty {difficulty}")
    return _build_curated_vector(rng.choice(pool))
