"""Curated lessons for the probability & counting sub-modules.

Bilingual static teaching content for counting techniques (combination, permutation,
factorial, mixed) and probability word-problem scenarios.
"""
import json
from functools import lru_cache
from pathlib import Path

_LESSONS_PATH = Path(__file__).with_name("data") / "lessons.json"


@lru_cache(maxsize=1)
def _lessons() -> dict:
    with open(_LESSONS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def lesson_keys() -> set[str]:
    """Keys (scenarios or counting kinds) that have an authored lesson."""
    return set(_lessons().keys())


def get_lesson(key: str, question_type: str = "probability") -> dict | None:
    """The authored lesson for one counting/probability variant, or None."""
    lesson = _lessons().get(key)
    if lesson is None:
        return None
    return {"topic": "probability", "question_type": question_type, "variant": key, **lesson}
