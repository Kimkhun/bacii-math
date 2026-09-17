"""Lesson lookup: the authored "how this exercise works" write-up for a skill.

A lesson is keyed by a **skill key** (``topic/question_type`` or
``topic/question_type:variant`` — the same key ``engine/core/skills.py``
produces), so the profile can ask "does this skill have a lesson?" and "give me
the lesson for this skill" without knowing which topic owns the content.

Lessons are authored once per topic and served verbatim (never LLM-generated),
so ``LESSON_SKILL_KEYS`` can be computed at import time and used as a cheap
``has_lesson`` check on every skill row of the profile. Populated for all practice
topics (complex, limit, derivatives, continuity, differential_equations,
vectors_space, conics, probability, integral).
"""
from ..topics.complex import lessons as complex_lessons
from ..topics.conics import lessons as conics_lessons
from ..topics.continuity import lessons as continuity_lessons
from ..topics.derivatives import lessons as derivatives_lessons
from ..topics.derivatives.generator import DERIVATIVE_TECHNIQUES
from ..topics.differential_equations import lessons as ode_lessons
from ..topics.integral import lessons as integral_lessons
from ..topics.limit import lessons as limit_lessons
from ..topics.probability import lessons as prob_lessons
from ..topics.vectors_space import lessons as vectors_lessons

#: Every skill key that currently has an authored lesson.
LESSON_SKILL_KEYS: set[str] = (
    {f"complex/{qt}" for qt in complex_lessons.lesson_question_types()}
    | {f"limit/limit:{tech}" for tech in limit_lessons.lesson_techniques()}
    # derivatives lessons are authored per order (order_1/order_2), but skill
    # keys are now per differentiation technique; every technique maps onto
    # whichever order lesson covers it (second_order -> order_2, else order_1).
    | {f"derivatives/compute_derivative:{v}" for v in DERIVATIVE_TECHNIQUES}
    | {f"continuity/check_continuity:{v}" for v in continuity_lessons.lesson_variants()}
    | {f"differential_equations/solve_ode:{k}" for k in ode_lessons.lesson_kinds()}
    | {f"vectors_space/vector_ops:{op}" for op in vectors_lessons.lesson_ops()}
    | {f"conics/classify_conic:{ask}" for ask in conics_lessons.lesson_asks()}
    | {f"probability/counting:{k}" for k in ("combination", "permutation", "factorial", "mixed")}
    | {f"probability/probability:{k}" for k in prob_lessons.lesson_keys() if k not in ("combination", "permutation", "factorial", "mixed")}
    | {f"integral/definite_integral:{v}" for v in integral_lessons.lesson_variants()}
    | {f"integral/indefinite_integral:{v}" for v in integral_lessons.lesson_variants()}
)



def _split(skill_key: str) -> tuple[str, str, str | None]:
    """(topic, question_type, variant) from a skill key."""
    topic, _, rest = skill_key.partition("/")
    qt, has_v, variant = rest.partition(":")
    return topic, qt, variant if has_v else None


def has_lesson(skill_key: str) -> bool:
    return skill_key in LESSON_SKILL_KEYS


def get_lesson(skill_key: str) -> dict | None:
    """The authored lesson for a skill key, or ``None`` if there isn't one."""
    topic, question_type, variant = _split(skill_key)
    if topic == "complex":
        return complex_lessons.get_lesson(question_type)
    if topic == "limit":
        technique = variant or question_type
        return limit_lessons.get_lesson(technique)
    if topic == "derivatives":
        order = "order_2" if variant == "second_order" else "order_1"
        return derivatives_lessons.get_lesson(order)
    if topic == "continuity":
        var = variant or "check_at_point"
        return continuity_lessons.get_lesson(var)
    if topic == "differential_equations":
        kind = variant or "first_order_linear_homogeneous"
        return ode_lessons.get_lesson(kind)
    if topic == "vectors_space":
        op = variant or "magnitude"
        return vectors_lessons.get_lesson(op)
    if topic == "conics":
        ask = variant or "vertex_x"
        return conics_lessons.get_lesson(ask)
    if topic == "probability":
        key = variant or "exercise_bag_split_atleast"
        return prob_lessons.get_lesson(key, question_type)
    if topic == "integral":
        var = variant or "polynomial"
        return integral_lessons.get_lesson(var, question_type)
    return None
