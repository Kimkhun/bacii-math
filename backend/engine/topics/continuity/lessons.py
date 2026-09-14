"""Curated lessons for the continuity sub-modules.

Bilingual static teaching content for checking continuity at a point
and finding parameters for continuity.
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
    """Variants that have an authored lesson ('check_at_point', 'find_parameter')."""
    return set(_lessons().keys())


def get_lesson(variant: str) -> dict | None:
    """The authored lesson for one continuity variant, or None."""
    lesson = _lessons().get(variant)
    if lesson is None:
        return None
    return {"topic": "continuity", "question_type": "check_continuity", "variant": variant, **lesson}
