"""Curated lessons for the limit sub-modules.

Bilingual static teaching content for all 15 limit techniques.
Keyed by technique id (e.g. 'direct_substitution', 'factoring_0_0', etc.).
"""
import json
from functools import lru_cache
from pathlib import Path

_LESSONS_PATH = Path(__file__).with_name("data") / "lessons.json"


@lru_cache(maxsize=1)
def _lessons() -> dict:
    with open(_LESSONS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def lesson_techniques() -> set[str]:
    """Technique IDs that have an authored lesson."""
    return set(_lessons().keys())


def get_lesson(technique: str) -> dict | None:
    """The authored lesson for one limit technique, or None."""
    lesson = _lessons().get(technique)
    if lesson is None:
        return None
    return {"topic": "limit", "question_type": "limit", "technique": technique, **lesson}
