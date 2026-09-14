"""Curated lessons for the vectors in space sub-modules.

Bilingual static teaching content for 3D vector operations:
magnitude, distance, dot, cross_magnitude, triangle_area,
scalar_triple_product, and find_m_orthogonal.
"""
import json
from functools import lru_cache
from pathlib import Path

_LESSONS_PATH = Path(__file__).with_name("data") / "lessons.json"


@lru_cache(maxsize=1)
def _lessons() -> dict:
    with open(_LESSONS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def lesson_ops() -> set[str]:
    """Operation keys that have an authored lesson."""
    return set(_lessons().keys())


def get_lesson(op: str) -> dict | None:
    """The authored lesson for one vector operation, or None."""
    lesson = _lessons().get(op)
    if lesson is None:
        return None
    return {"topic": "vectors_space", "question_type": "vector_ops", "op": op, **lesson}
