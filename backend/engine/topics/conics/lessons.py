"""Curated lessons for the conics sub-modules.

Bilingual static teaching content for conic features:
vertex_x, vertex_y, focus_x, focus_y, p, directrix, center_x, center_y, a, b, c.
"""
import json
from functools import lru_cache
from pathlib import Path

_LESSONS_PATH = Path(__file__).with_name("data") / "lessons.json"


@lru_cache(maxsize=1)
def _lessons() -> dict:
    with open(_LESSONS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def lesson_asks() -> set[str]:
    """Conic ask keys that have an authored lesson."""
    return set(_lessons().keys())


def get_lesson(ask: str) -> dict | None:
    """The authored lesson for one conic feature ask, or None."""
    lesson = _lessons().get(ask)
    if lesson is None:
        return None
    return {"topic": "conics", "question_type": "classify_conic", "ask": ask, **lesson}
