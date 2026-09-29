"""Template shapes for the curated-shape topics (continuity, conics,
vectors_space, differential_equations) — plus derivatives, whose cards come
straight from its structure registry instead.

Unlike ``complex``/``integral``/``limit`` — which fill symbolic slot templates —
these topics mix curated BAC II exercises from ``topics/<topic>/data/curated/*.json``
with per-shape procedural samplers in each topic's ``generator.py``, so there is
no single slot template to show.

For the admin template inventory we still want to show a *template* (the shape
of the exercise with placeholder letters), not one card per concrete exercise.
This module groups each topic's curated pool into a handful of shapes — one per
generation technique / exercise form — and emits one template card per shape,
with the concrete coefficients abstracted into slot letters. No numbers are set.

Each shape dict mirrors the fields ``_build_generic_topic_payload`` expects:
``id, question_type, difficulty, technique, pattern, pattern_latex,
sample_prompt(_latex), sample_answer(_latex), formula_tags, source_labels``.
The sample_* fields are intentionally empty — a shape is a template, not an
instance — and the admin card hides its sample block when they are absent.
"""
from __future__ import annotations

from collections import Counter

from ..topics.conics.generator import _CONICS_CURATED
from ..topics.continuity.generator import _CONTINUITY_CURATED
from ..topics.derivatives.generator import build_derivative_variants
from ..topics.derivatives.structures import all_derivative_structures
from ..topics.differential_equations.generator import _ODE_CURATED
from ..topics.vectors_space.generator import _VECTORS_CURATED

CURATED_SHAPE_TOPICS = (
    "derivatives",
    "continuity",
    "conics",
    "vectors_space",
    "differential_equations",
)


def _dominant_difficulty(items) -> str:
    if not items:
        return "medium"
    return Counter(i.get("difficulty", "medium") for i in items).most_common(1)[0][0]


def _card(topic, qt, shape_id, items, technique, pattern, pattern_latex):
    """Assemble one template card from the curated items that map to a shape."""
    return {
        "id": f"{topic}:{qt}:{shape_id}",
        "question_type": qt,
        "difficulty": _dominant_difficulty(items),
        "technique": technique,
        "pattern": pattern,
        "pattern_latex": pattern_latex,
        "sample_prompt": "",
        "sample_prompt_latex": None,
        "sample_answer": "",
        "sample_answer_latex": None,
        "formula_tags": [],
        "source_labels": [f"{len(items)} curated + procedurally generated"],
    }


# --- derivatives: one card per registry structure (``topics/derivatives/
# structures.py``), the topic's only question source. Unlike the curated
# shapes below, each card carries real worked samples like limit's cards. ---

def derivative_card(struct, seed=None):
    variants = build_derivative_variants(struct, count=3, seed=seed)
    sample = variants[0] if variants else {}
    return {
        "id": struct["id"],
        "question_type": struct["question_type"],
        "category": struct["category"],
        "difficulty": struct["difficulty"],
        "parameterizable": True,
        "technique": struct["title_en"],
        "description": struct["title_en"],
        "pattern": struct["pattern"],
        "pattern_latex": struct["pattern_latex"],
        "sample_prompt": sample.get("prompt", ""),
        "sample_prompt_latex": sample.get("prompt_latex"),
        "sample_answer": sample.get("answer_exact", ""),
        "sample_answer_latex": sample.get("answer_latex"),
        "sample_params": sample.get("params"),
        "variants": variants,
        "formula_tags": sample.get("formula_tags", []),
        "source_labels": struct["source_labels"],
    }


def _derivatives_shapes():
    return [derivative_card(s) for s in all_derivative_structures()]


# --- continuity: check-at-point vs. find-parameter ---

def _has_unknown(item) -> bool:
    return item.get("unknown") not in (None, "", "None")


def _continuity_shapes():
    check = [i for i in _CONTINUITY_CURATED if not _has_unknown(i)]
    find = [i for i in _CONTINUITY_CURATED if _has_unknown(i)]
    cards = []
    if check:
        cards.append(_card(
            "continuity", "check_continuity", "check_at_point", check,
            "Decide whether the piecewise function is continuous at the point",
            "piecewise continuity check",
            r"f(x) = \begin{cases} g(x) & x < a \\ h(x) & x \geq a \end{cases}"
            r",\quad \text{continuous at } x = a?",
        ))
    if find:
        cards.append(_card(
            "continuity", "check_continuity", "find_parameter", find,
            "Find the constant that makes the function continuous",
            "solve for continuity parameter",
            r"f(x) = \begin{cases} g(x) & x < a \\ h(x;\,k) & x \geq a \end{cases}"
            r",\quad \text{find } k",
        ))
    return cards


# --- conics: parabola / ellipse / hyperbola, from the squared-term coefficients ---

def _conic_shape(item) -> str:
    expr = item.get("expr", "")
    # Coefficient signs of x^2 and y^2 decide the conic type. Curated exprs are
    # simple polynomials like "4*x**2+9*y**2-8*x+36*y+4"; a light scan of the
    # squared terms is enough (SymPy is the source of truth at solve time, this
    # only picks which template card to file the exercise under).
    import re
    def coeff(sym):
        m = re.search(rf"([+-]?\s*\d*)\*?{re.escape(sym)}\*\*2", expr)
        if not m:
            return 0
        raw = m.group(1).replace(" ", "")
        if raw in ("", "+"):
            return 1
        if raw == "-":
            return -1
        return int(raw)
    cx, cy = coeff("x"), coeff("y")
    if cx == 0 or cy == 0:
        return "parabola"
    if (cx > 0) == (cy > 0):
        return "ellipse"
    return "hyperbola"


_CONIC_SHAPES = [
    ("parabola", "Complete the square (one squared term): parabola",
     r"(x - h)^{2} = 4p\,(y - k)"),
    ("ellipse", "Complete the square (like-sign squared terms): ellipse",
     r"\frac{(x - h)^{2}}{a^{2}} + \frac{(y - k)^{2}}{b^{2}} = 1"),
    ("hyperbola", "Complete the square (opposite-sign squared terms): hyperbola",
     r"\frac{(x - h)^{2}}{a^{2}} - \frac{(y - k)^{2}}{b^{2}} = 1"),
]


def _conics_shapes():
    buckets: dict[str, list] = {}
    for item in _CONICS_CURATED:
        buckets.setdefault(_conic_shape(item), []).append(item)
    cards = []
    for shape_id, technique, pattern_latex in _CONIC_SHAPES:
        items = buckets.get(shape_id)
        if not items:
            continue
        cards.append(_card("conics", "classify_conic", shape_id, items,
                           technique, technique, pattern_latex))
    return cards


# --- vectors_space: one shape per operation ---

_VECTOR_SHAPES = [
    ("magnitude", "Magnitude of a vector between two points",
     r"A(a_1, a_2, a_3),\ B(b_1, b_2, b_3):\ \ |\overrightarrow{AB}|"),
    ("distance", "Distance between two points",
     r"A(a_1, a_2, a_3),\ B(b_1, b_2, b_3):\ \ AB"),
    ("dot", "Dot product of two vectors",
     r"\overrightarrow{AB} \cdot \overrightarrow{AC}"),
    ("cross_magnitude", "Magnitude of a cross product",
     r"|\overrightarrow{AB} \times \overrightarrow{AC}|"),
    ("triangle_area", "Area of a triangle from three points",
     r"\text{Area}(\triangle ABC) = \tfrac{1}{2}\,|\overrightarrow{AB} \times \overrightarrow{AC}|"),
    ("scalar_triple_product", "Scalar triple product",
     r"\vec{u} \cdot (\vec{v} \times \vec{w})"),
    ("find_m_orthogonal", "Find the parameter making two vectors orthogonal",
     r"\text{Find } m \text{ such that } \vec{u} \cdot \vec{v} = 0"),
]


def _vectors_shapes():
    buckets: dict[str, list] = {}
    for item in _VECTORS_CURATED:
        buckets.setdefault(item.get("op"), []).append(item)
    cards = []
    for shape_id, technique, pattern_latex in _VECTOR_SHAPES:
        items = buckets.get(shape_id)
        if not items:
            continue
        cards.append(_card("vectors_space", "vector_ops", shape_id, items,
                           technique, technique, pattern_latex))
    return cards


# --- differential_equations: one shape per ODE kind ---

_ODE_SHAPES = [
    ("first_order_linear_homogeneous", "First-order linear homogeneous",
     r"y' + a\,y = 0,\quad y(x_0) = y_0"),
    ("first_order_linear_nonhomogeneous", "First-order linear non-homogeneous",
     r"y' + a\,y = r,\quad y(x_0) = y_0"),
    ("second_order_homogeneous_constant_coeff", "Second-order homogeneous, constant coefficients",
     r"a\,y'' + b\,y' + c\,y = 0"),
    ("second_order_nonhomogeneous", "Second-order non-homogeneous",
     r"a\,y'' + b\,y' + c\,y = r(x)"),
]


def _ode_shapes():
    buckets: dict[str, list] = {}
    for item in _ODE_CURATED:
        buckets.setdefault(item.get("kind"), []).append(item)
    cards = []
    for shape_id, technique, pattern_latex in _ODE_SHAPES:
        items = buckets.get(shape_id)
        if not items:
            continue
        cards.append(_card("differential_equations", "solve_ode", shape_id, items,
                           technique, technique, pattern_latex))
    return cards


_BUILDERS = {
    "derivatives": _derivatives_shapes,
    "continuity": _continuity_shapes,
    "conics": _conics_shapes,
    "vectors_space": _vectors_shapes,
    "differential_equations": _ode_shapes,
}


def shapes_for(topic: str) -> list[dict]:
    """One template card per exercise shape for a curated-replay ``topic``.
    Returns [] for topics that are not curated-replay."""
    builder = _BUILDERS.get(topic)
    return builder() if builder else []
