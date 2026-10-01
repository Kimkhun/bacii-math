"""Curated lessons for the limit sub-modules.

Bilingual static teaching content for all 15 limit techniques.
Keyed by technique id (e.g. 'direct_substitution', 'factoring_0_0', etc.).
"""
import json
from functools import lru_cache
from pathlib import Path

from ...core.lesson_animations import with_animation
from .structures import LIMIT_STRUCTURES

_LESSONS_PATH = Path(__file__).with_name("data") / "lessons.json"


@lru_cache(maxsize=1)
def _lessons() -> dict:
    with open(_LESSONS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def lesson_techniques() -> set[str]:
    """Technique IDs that have an authored lesson."""
    return set(_lessons().keys())


# Generated questions record their *template* id in ``params.technique``
# (e.g. ``limit:trig:sinc_standard``), while lessons are authored per solution
# technique (``sinc_standard_limit``). Templates map onto a lesson by their
# (category, subfamily), with per-template overrides where a family mixes
# techniques. Families with no matching lesson are simply absent.
_LESSON_BY_FAMILY = {
    ("rational", "direct"): "direct_substitution",
    ("rational", "powers"): "factoring_0_0",
    ("rational", "quadratics"): "factoring_0_0",
    ("rational", "binomial"): "factoring_0_0",
    ("rational", "infinity"): "rational_function_infinity",
    ("infinity", "rational"): "rational_function_infinity",
    ("infinity", "conjugate"): "conjugate_infinity",
    ("radical", "sqrt"): "rationalization_conjugate_finite",
    ("radical", "cbrt"): "rationalization_conjugate_finite",
    ("radical", "double_and_split"): "rationalization_conjugate_finite",
    ("trig", "sinc_standard"): "sinc_standard_limit",
    ("trig", "change_var"): "sinc_standard_limit",
    ("trig", "half_angle"): "half_angle_sinc_combo",
    ("trig", "double_angle"): "trig_identity_0_0",
    ("trig", "quadratic"): "trig_identity_0_0",
    ("trig", "sum_product"): "angle_addition_0_0",
    ("trig", "radical_trig"): "rationalization_sinc_combo",
    ("exponential", "zero"): "exponential_standard_limit",
    ("exponential", "trig_combo"): "exponential_sinc_combo",
    ("exponential", "one_inf"): "indeterminate_one_infinity",
    ("logarithmic", "zero"): "log_limit_zero",
    ("logarithmic", "growth_zero"): "log_limit_zero",
    ("logarithmic", "infinity"): "log_limit_infinity",
    ("logarithmic", "rational"): "log_limit_infinity",
}
_LESSON_BY_TEMPLATE = {
    "limit:trig:angle_addition_linear_pi3": "angle_addition_0_0",
    "limit:trig:angle_addition_reciprocal_pi3": "angle_addition_0_0",
}
_TEMPLATE_LESSONS = {
    s["id"]: _LESSON_BY_TEMPLATE.get(s["id"]) or _LESSON_BY_FAMILY.get((s["category"], s["subfamily"]))
    for s in LIMIT_STRUCTURES
}


def lesson_technique(technique_or_template: str) -> str | None:
    """The lesson technique id for a technique id or a template id."""
    if technique_or_template in _lessons():
        return technique_or_template
    return _TEMPLATE_LESSONS.get(technique_or_template)


def get_lesson(technique: str) -> dict | None:
    """The authored lesson for one limit technique (or template id), or None."""
    technique = lesson_technique(technique)
    if technique is None:
        return None
    lesson = _lessons().get(technique)
    if lesson is None:
        return None
    payload = {"topic": "limit", "question_type": "limit", "technique": technique, **lesson}
    return with_animation(payload, _LESSONS_PATH.parent, technique)
