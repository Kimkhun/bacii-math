"""The skill taxonomy: what a student can be good or bad *at*.

A **skill** is the finest grain of exercise the student experiences as "a kind
of problem" — not a topic ("limits") and not an individual question, but the
technique in between: `sin(x)/x` standard limits, integration by parts, the
cross product, second-order homogeneous ODEs. That is the level a suggestion
has to speak at to be actionable ("practise sin(x)/x limits", not "practise
limits"), so it is the level the tracker measures at.

Two things live here, and they must agree:

* ``SKILLS`` — the catalog, one entry per leaf skill, enumerated from the very
  registries the generators sample from (``LIMIT_TECHNIQUES``, the integral
  variant tables, the probability scenario catalog, and the curated pools'
  own discriminator field). Deriving it rather than hand-listing it is what
  keeps the taxonomy from drifting the moment someone adds a technique.
* ``skill_key_for`` — the inverse: given a stored ``Question``'s topic,
  question_type and params, which catalog entry was that? Every topic's
  generator records its discriminator in ``params`` (limit's ``technique`` /
  ``formula_name``, integral's and probability's ``variant``, the curated
  topics' ``kind`` / ``op`` / ``ask`` / ``order`` / ``unknown``), so the key
  can be recovered for questions answered long before this module existed.

Key format is ``topic/question_type`` or ``topic/question_type:variant`` — the
same ``question_type:variant`` encoding the practice page's type dropdown
already uses, so a skill key round-trips into a "practise this" link.

Topics whose only axis of variety *is* the question type (complex numbers,
function studies, past-exam questions) contribute one skill per question type
and no variant. Nothing else in the engine needs to special-case them.
"""
import re

from ..topics.conics.generator import _ASK_PHRASE, _CONICS_CURATED
from ..topics.continuity.generator import _CONTINUITY_CURATED
from ..topics.derivatives.generator import _DERIVATIVE_CURATED
from ..topics.differential_equations.generator import _KIND_LABEL, _ODE_CURATED
from ..topics.integral.generator import (
    _INDEFINITE_VARIANT_BY_DIFFICULTY,
    _INTEGRAL_VARIANT_BY_DIFFICULTY,
)
from ..topics.limit.structures import LIMIT_TECHNIQUES
from ..topics.probability import scenarios
from ..topics.probability.counting import _COUNTING_CURATED
from ..topics.vectors_space.generator import _OP_LABEL, _VECTORS_CURATED
from .shared import QUESTION_TYPES_BY_TOPIC

TOPIC_LABELS = {
    "complex": "Complex numbers",
    "limit": "Limits",
    "integral": "Integrals",
    "probability": "Probability & counting",
    "functions": "Function studies",
    "continuity": "Continuity",
    "derivatives": "Derivatives",
    "differential_equations": "Differential equations",
    "vectors_space": "Vectors in space",
    "conics": "Conics",
    "past_exam": "Past exams",
}

#: Topics whose questions are replays of a fixed paper rather than practice
#: material. They are tracked (an exam attempt is still evidence) but excluded
#: from the syllabus roll-up and never suggested — you can't "practise more
#: 2018 question 3" as a technique.
NON_PRACTICE_TOPICS = ("past_exam",)

_QUESTION_TYPE_LABELS = {
    "modulus": "Modulus |z|",
    "argument": "Argument arg(z)",
    "conjugate": "Conjugate z̄",
    "real_part": "Real part Re(z)",
    "imaginary_part": "Imaginary part Im(z)",
    "complex_arithmetic": "Complex arithmetic",
    "complex_power": "Powers of z",
    "de_moivre_power": "De Moivre's formula",
    "nth_roots": "n-th roots",
    "limit": "Limit",
    "definite_integral": "Definite integral",
    "indefinite_integral": "Indefinite integral",
    "probability": "Probability",
    "counting": "Counting",
    "study": "Curve study & area",
    "check_continuity": "Continuity",
    "compute_derivative": "Derivative",
    "solve_ode": "Differential equation",
    "vector_ops": "Vector operation",
    "classify_conic": "Conic",
    "2018_q1": "2018 — Q1 (probability)",
    "2018_q3": "2018 — Q3 (complex numbers)",
    "2018_q5_vectors": "2018 — Q5 (vectors)",
    "2018_q5_conic": "2018 — Q5 (conic)",
    "2018_q7": "2018 — Q7 (function study)",
}

_LIMIT_LABELS = {
    "direct_substitution": "Direct substitution",
    "factoring_0_0": "Factoring a 0/0 form",
    "rationalization_conjugate_finite": "Conjugate rationalisation",
    "trig_identity_0_0": "Trig identity on 0/0",
    "sinc_standard_limit": "Standard limit sin(x)/x",
    "angle_addition_0_0": "Angle-addition identity",
    "rationalization_sinc_combo": "Conjugate + sin(x)/x combo",
    "exponential_sinc_combo": "Exponential + sin(x)/x combo",
    "half_angle_sinc_combo": "Half-angle + sin(x)/x combo",
    "exponential_standard_limit": "Standard limit (eˣ−1)/x",
    "conjugate_infinity": "Conjugate at infinity",
    "log_limit_infinity": "Logarithmic limit at infinity",
    "rational_function_infinity": "Rational function at infinity",
    "log_limit_zero": "Logarithmic limit at 0",
    "indeterminate_one_infinity": "Indeterminate 1^∞",
}

_INTEGRAL_LABELS = {
    "polynomial": "Polynomial",
    "linear_argument": "Linear argument f(ax+b)",
    "mixed_sum": "Mixed sum",
    "trig": "Trigonometric",
    "u_substitution": "u-substitution",
    "by_parts": "Integration by parts",
    "power": "Power rule",
    "expand": "Expand then integrate",
    "split": "Split the fraction",
    "usub": "u-substitution",
    "trig_sec": "Trigonometric (sec²)",
    "indefinite_sum": "Sum of several term types",
}

#: Variants the indefinite-integral generator can *emit* but doesn't list in
#: its per-difficulty table (curated multi-term shapes it mixes into the
#: "power"/"trig_sec" draws). Without these, real questions would fall back to
#: the bare question-type skill and their evidence would be pooled with
#: everything else.
_INTEGRAL_EXTRA_VARIANTS = {"indefinite_integral": {"indefinite_sum": "medium"}}

_CONTINUITY_LABELS = {
    "check_at_point": "Check continuity at a point",
    "find_parameter": "Find the parameter that makes it continuous",
}

_DERIVATIVE_LABELS = {
    "order_1": "First derivative",
    "order_2": "Second derivative",
}

_VECTOR_LABELS = {
    "magnitude": "Magnitude of a vector |AB|",
    "distance": "Distance between two points",
    "dot": "Dot product AB · AC",
    "cross_magnitude": "Cross product magnitude |AB × AC|",
    "triangle_area": "Area of a triangle",
    "scalar_triple_product": "Scalar triple product u · (v × w)",
    "find_m_orthogonal": "Find m making two vectors orthogonal",
}

_CONIC_LABELS = {
    "vertex_x": "vertex (x)",
    "vertex_y": "vertex (y)",
    "focus_x": "focus (x)",
    "focus_y": "focus (y)",
    "p": "focal parameter p",
    "directrix": "directrix",
    "center_x": "centre (x)",
    "center_y": "centre (y)",
    "a": "semi-major / transverse axis a",
    "b": "semi-minor / conjugate axis b",
    "c": "focal distance c",
}

_PROBABILITY_LABELS = {
    "exercise_bag_split_atleast": "Balls drawn from one bag",
    "exercise_two_bag_odd_even": "Two bags of numbered balls",
    "exercise_two_box_colors": "Two boxes of coloured balls",
    "exercise_banknotes": "Banknotes drawn from a box",
    "exercise_pens": "Pens drawn from a bag",
    "exercise_students": "Students chosen from a class",
}

_COUNTING_LABELS = {
    "combination": "Combinations C(n, r)",
    "permutation": "Permutations P(n, r)",
    "factorial": "Factorials",
    "mixed": "Mixed counting expression",
}


def _conic_label(ask):
    """Plain-English name for a conic feature. Falls back to stripping the
    LaTeX out of the prompt phrase so a newly curated `ask` still reads."""
    if ask in _CONIC_LABELS:
        return _CONIC_LABELS[ask]
    phrase = _ASK_PHRASE.get(ask)
    if not phrase:
        return ask.replace("_", " ")
    text = re.sub(r"\\text\{([^}]*)\}", r"\1", phrase)
    text = re.sub(r"\\[a-zA-Z]+", "", text).replace("{", "").replace("}", "")
    return " ".join(text.split())


def counting_variant(expr):
    """Which counting technique an expression like ``C(4,2)*P(3,2)`` exercises."""
    text = str(expr or "")
    has_c, has_p = "C(" in text, "P(" in text
    if has_c and has_p:
        return "mixed"
    if has_c:
        return "combination"
    if has_p:
        return "permutation"
    if "!" in text or "factorial" in text:
        return "factorial"
    return "mixed"


def continuity_variant(params):
    unknown = params.get("unknown")
    return "find_parameter" if unknown not in (None, "None", "") else "check_at_point"


def _curated_variants(pool, field):
    """Distinct values of a curated pool's discriminator field, in first-seen
    order, each with the easiest difficulty it appears at (that's the one a
    "practise this" link should start the student on)."""
    seen = {}
    for item in pool:
        value = item.get(field)
        if value in (None, "", "None"):
            continue
        value = str(value)
        rank = {"easy": 0, "medium": 1, "hard": 2}.get(item.get("difficulty"), 1)
        if value not in seen or rank < seen[value][0]:
            seen[value] = (rank, item.get("difficulty", "medium"))
    return [(v, d) for v, (_, d) in seen.items()]


def make_key(topic, question_type, variant=None):
    base = f"{topic}/{question_type}"
    return f"{base}:{variant}" if variant else base


def _skill(topic, question_type, variant, label, difficulty="medium", forceable=True):
    return {
        "key": make_key(topic, question_type, variant),
        "topic": topic,
        "topic_label": TOPIC_LABELS.get(topic, topic.replace("_", " ").capitalize()),
        "question_type": question_type,
        "variant": variant,
        "label": label,
        "difficulty": difficulty,
        "forceable": forceable,
        "practice": bool(topic not in NON_PRACTICE_TOPICS),
    }


def _build_catalog():
    out = []

    def qt_label(qt):
        return _QUESTION_TYPE_LABELS.get(qt, qt.replace("_", " ").capitalize())

    for topic, question_types in QUESTION_TYPES_BY_TOPIC.items():
        for qt in question_types:
            if topic == "limit":
                for tid, meta in LIMIT_TECHNIQUES.items():
                    out.append(_skill(
                        topic, qt, tid, _LIMIT_LABELS.get(tid, tid.replace("_", " ").capitalize()),
                        meta.get("difficulty", "medium"), forceable=bool(meta.get("parameterizable")),
                    ))
            elif topic == "integral":
                table = (
                    _INTEGRAL_VARIANT_BY_DIFFICULTY if qt == "definite_integral"
                    else _INDEFINITE_VARIANT_BY_DIFFICULTY
                )
                # A variant can be offered at several difficulties; keep the easiest.
                first_at = {}
                for diff in ("easy", "medium", "hard"):
                    for v in table.get(diff, []):
                        first_at.setdefault(v, diff)
                for v, diff in _INTEGRAL_EXTRA_VARIANTS.get(qt, {}).items():
                    first_at.setdefault(v, diff)
                for v, diff in first_at.items():
                    out.append(_skill(
                        topic, qt, v, f"{qt_label(qt)} — {_INTEGRAL_LABELS.get(v, v)}", diff,
                    ))
            elif topic == "probability" and qt == "probability":
                for sid, meta in scenarios.SCENARIOS.items():
                    label = _PROBABILITY_LABELS.get(
                        sid, sid.replace("exercise_", "").replace("_", " ").capitalize()
                    )
                    out.append(_skill(topic, qt, sid, label, meta.get("difficulty", "medium")))
            elif topic == "probability" and qt == "counting":
                for v, diff in _curated_variants(
                    [{**c, "kind": counting_variant(c.get("expr"))} for c in _COUNTING_CURATED], "kind"
                ):
                    out.append(_skill(topic, qt, v, _COUNTING_LABELS.get(v, v), diff))
            elif topic == "differential_equations":
                for v, diff in _curated_variants(_ODE_CURATED, "kind"):
                    out.append(_skill(topic, qt, v, _KIND_LABEL.get(v, v), diff))
            elif topic == "vectors_space":
                for v, diff in _curated_variants(_VECTORS_CURATED, "op"):
                    out.append(_skill(topic, qt, v, _VECTOR_LABELS.get(v, _OP_LABEL.get(v, v)), diff))
            elif topic == "conics":
                for v, diff in _curated_variants(_CONICS_CURATED, "ask"):
                    out.append(_skill(topic, qt, v, f"Conic — {_conic_label(v)}", diff))
            elif topic == "continuity":
                pool = [{**c, "kind": continuity_variant(c)} for c in _CONTINUITY_CURATED]
                for v, diff in _curated_variants(pool, "kind"):
                    out.append(_skill(topic, qt, v, _CONTINUITY_LABELS.get(v, v), diff))
            elif topic == "derivatives":
                pool = [{**c, "kind": f"order_{c.get('order', 1)}"} for c in _DERIVATIVE_CURATED]
                for v, diff in _curated_variants(pool, "kind"):
                    out.append(_skill(topic, qt, v, _DERIVATIVE_LABELS.get(v, v), diff))
            else:
                # complex, functions, past_exam: the question type *is* the skill.
                difficulty = "hard" if topic == "past_exam" else "medium"
                out.append(_skill(topic, qt, None, qt_label(qt), difficulty))
    return out


SKILLS = _build_catalog()
SKILLS_BY_KEY = {s["key"]: s for s in SKILLS}


def _variant_for(topic, question_type, params):
    params = params or {}
    if topic == "limit":
        return params.get("technique") or params.get("formula_name")
    if topic == "integral":
        return params.get("variant")
    if topic == "probability":
        if question_type == "counting":
            return counting_variant(params.get("expr"))
        return params.get("variant") or params.get("scenario_id")
    if topic == "differential_equations":
        return params.get("kind")
    if topic == "vectors_space":
        return params.get("op")
    if topic == "conics":
        return params.get("ask")
    if topic == "continuity":
        return continuity_variant(params)
    if topic == "derivatives":
        order = params.get("order")
        return f"order_{order}" if order not in (None, "") else None
    return None


def skill_key_for(topic, question_type, params=None):
    """The catalog key for a stored question. Falls back to the bare
    ``topic/question_type`` when the variant isn't one the catalog knows (an
    old row, or a curated exercise whose discriminator was added later), so a
    question always lands somewhere rather than being dropped."""
    variant = _variant_for(topic, question_type, params)
    key = make_key(topic, question_type, str(variant) if variant else None)
    if key in SKILLS_BY_KEY:
        return key
    return make_key(topic, question_type)


def resolve(key):
    """Catalog entry for a key, or a synthetic one for keys the catalog has
    since dropped — stored progress must never crash the profile."""
    entry = SKILLS_BY_KEY.get(key)
    if entry is not None:
        return entry
    topic, _, rest = key.partition("/")
    question_type, _, variant = rest.partition(":")
    label = _QUESTION_TYPE_LABELS.get(question_type, question_type.replace("_", " ").capitalize())
    if variant:
        label = f"{label} — {variant.replace('_', ' ')}"
    return _skill(topic, question_type, variant or None, label, forceable=False)


def skills_for_topic(topic):
    return [s for s in SKILLS if s["topic"] == topic]


def practice_topics():
    """Topics that count toward the syllabus roll-up, in catalog order."""
    seen = []
    for s in SKILLS:
        if s["practice"] and s["topic"] not in seen:
            seen.append(s["topic"])
    return seen


def practice_target(key):
    """The ``generate`` arguments that force a question for this skill."""
    s = resolve(key)
    return {
        "topic": s["topic"],
        "question_type": s["question_type"],
        "variant": s["variant"] if s["forceable"] else None,
        "difficulty": s["difficulty"],
    }
