"""Curated lessons for the derivatives sub-modules.

Bilingual static teaching content for first and second derivatives.
Keyed by variant ('order_1' / 'order_2').
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
    """Variants (e.g. order_1, order_2) that have an authored lesson."""
    return set(_lessons().keys())


def get_lesson(variant: str) -> dict | None:
    """The authored lesson for one derivative variant (order_1 or order_2)."""
    lesson = _lessons().get(variant)
    if lesson is None:
        return None
    return {"topic": "derivatives", "question_type": "compute_derivative", "variant": variant, **lesson}
