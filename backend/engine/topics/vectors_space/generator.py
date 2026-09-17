"""3D vector generation: curated real BAC II / textbook exercises from
data/curated/*.json mixed with procedurally sampled integer points/vectors.
SymPy Matrix operations recompute the result at solve time."""
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


_OPS = tuple(_OP_LABEL)

#: |v| is an integer for these (a, b, c): 1+4+4=9, 4+9+36=49, 1+16+64=81, ...
_CLEAN_LENGTHS = ((1, 2, 2), (2, 3, 6), (1, 4, 8), (4, 4, 7), (2, 6, 9), (6, 6, 7), (2, 2, 1), (3, 4, 12))

_TECHNIQUE = {
    "magnitude": "Compute vector AB by subtracting coordinates, then its magnitude |v| = sqrt(x^2+y^2+z^2).",
    "distance": "The distance between two points is the magnitude of the vector joining them.",
    "dot": "Build vectors AB and AC, then compute u.v = x1x2 + y1y2 + z1z2.",
    "cross_magnitude": "Build vectors AB and AC, compute AB x AC component by component, then its magnitude.",
    "triangle_area": "Compute AB x AC; the triangle's area is half its magnitude.",
    "scalar_triple_product": "Compute v x w, then dot it with u; the result is 0 exactly when the vectors are coplanar.",
    "find_m_orthogonal": "Set the dot product u.v equal to 0 and solve the resulting linear equation for m.",
}


def _span(difficulty):
    return {"easy": 5, "medium": 6, "hard": 8}[difficulty]


def _pt(rng, r):
    return [rng.randint(-r, r) for _ in range(3)]


def _clean_vector(rng):
    comps = list(rng.choice(_CLEAN_LENGTHS))
    rng.shuffle(comps)
    return [c * rng.choice((1, -1)) for c in comps]


def _cross(u, v):
    return [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]


def _sample_vector_item(rng, op, difficulty):
    r = _span(difficulty)
    item = {"op": op, "difficulty": difficulty, "curated_technique": _TECHNIQUE[op]}
    if op in ("magnitude", "distance"):
        A = _pt(rng, r)
        clean = difficulty == "easy" or (difficulty == "medium" and rng.random() < 0.5)
        d = _clean_vector(rng) if clean else _pt(rng, r)
        while d == [0, 0, 0]:
            d = _pt(rng, r)
        item.update(A=A, B=[a + b for a, b in zip(A, d)])
    elif op == "dot":
        item.update(A=_pt(rng, r), B=_pt(rng, r), C=_pt(rng, r))
    elif op in ("cross_magnitude", "triangle_area"):
        while True:
            A, B, C = _pt(rng, r), _pt(rng, r), _pt(rng, r)
            ab = [b - a for a, b in zip(A, B)]
            ac = [c - a for a, c in zip(A, C)]
            if _cross(ab, ac) != [0, 0, 0]:
                break
        item.update(A=A, B=B, C=C)
    elif op == "scalar_triple_product":
        u, v = _pt(rng, r // 2 + 1), _pt(rng, r // 2 + 1)
        if rng.random() < 0.25:
            s, t = rng.randint(-2, 2), rng.randint(-2, 2)
            w = [s * a + t * b for a, b in zip(u, v)]
        else:
            w = _pt(rng, r // 2 + 1)
        item.update(u=u, v=v, w=w)
    elif op == "find_m_orthogonal":
        while True:
            u, v = _pt(rng, r), _pt(rng, r)
            i = rng.randrange(3)
            if difficulty == "hard":
                j = rng.choice([k for k in range(3) if k != i])
                coeff = v[i] + u[j]
                rest = sum(u[k] * v[k] for k in range(3) if k not in (i, j))
                u_out, v_out = list(u), list(v)
                u_out[i], v_out[j] = "m", "m"
            else:
                coeff = u[i]
                rest = sum(u[k] * v[k] for k in range(3) if k != i)
                u_out, v_out = list(u), list(v)
                v_out[i] = "m"
            if coeff != 0 and rest % coeff == 0 and -rest // coeff != 0 and abs(rest // coeff) <= 9:
                break
        item.update(u=u_out, v=v_out, unknown="m")
    else:
        raise ValueError(f"unknown vector op: {op}")
    return item


def generate_vector_for_op(rng, op, difficulty="medium"):
    problem = _build_curated_vector(_sample_vector_item(rng, op, difficulty))
    problem["z_display"] = problem["z_latex"] = _OP_LABEL[op]
    problem["source"] = "generated"
    return problem


def _generate_vectors_space(rng, difficulty, question_type=None, variant=None):
    """Half real curated exercises, half procedurally sampled ones. `variant` is
    an `op` (magnitude, dot, cross_magnitude, ...); unknown variants are ignored."""
    if question_type not in (None, "vector_ops"):
        raise ValueError(f"question_type {question_type} does not match topic vectors_space")
    op = variant if variant in _OPS else None
    curated = [t for t in _VECTORS_CURATED
               if t.get("difficulty") == difficulty and (op is None or t.get("op") == op)]
    if curated and rng.random() < 0.5:
        return _build_curated_vector(rng.choice(curated))
    return generate_vector_for_op(rng, op or rng.choice(_OPS), difficulty)
