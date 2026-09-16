"""Curated lessons for the integral sub-modules.

Bilingual static teaching content for definite and indefinite integral variants:
polynomial, power, linear_argument, trig, trig_sec, u_substitution, usub,
by_parts, expand, split, mixed_sum, indefinite_sum.
"""
import json
from functools import lru_cache
from pathlib import Path

_LESSONS_PATH = Path(__file__).with_name("data") / "lessons.json"


@lru_cache(maxsize=1)
def _lessons() -> dict:
    with open(_LESSONS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def lesson_variants() -> set[str]:
    """Variants that have an authored lesson."""
    return set(_lessons().keys())


def get_lesson(variant: str, question_type: str = "definite_integral") -> dict | None:
    """The authored lesson for one integral variant, or None."""
    lesson = _lessons().get(variant)
    if lesson is None:
        return None
    return {"topic": "integral", "question_type": question_type, "variant": variant, **lesson}
