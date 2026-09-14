"""Curated lessons for the differential equations sub-modules.

Bilingual static teaching content for first and second order ODEs.
Keyed by kind (e.g. 'first_order_linear_homogeneous', 'second_order_homogeneous_constant_coeff', etc.).
"""
import json
from functools import lru_cache
from pathlib import Path

_LESSONS_PATH = Path(__file__).with_name("data") / "lessons.json"


@lru_cache(maxsize=1)
def _lessons() -> dict:
    with open(_LESSONS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def lesson_kinds() -> set[str]:
    """ODE kinds that have an authored lesson."""
    return set(_lessons().keys())


def get_lesson(kind: str) -> dict | None:
    """The authored lesson for one ODE kind, or None."""
    lesson = _lessons().get(kind)
    if lesson is None:
        return None
    return {"topic": "differential_equations", "question_type": "solve_ode", "kind": kind, **lesson}
