"""Curated lessons for the complex-numbers sub-modules.

A **lesson** is the short "how this kind of exercise works" write-up a student
sees behind the *Lesson* button on their profile — one per practisable exercise
type (question type), not per individual question. Unlike explanations of a
graded attempt, a lesson is **not** LLM-generated: it is authored once, stored
in ``data/lessons.json``, and served verbatim to every student. That keeps the
teaching content stable, reviewable, and free of per-request model cost.

Content is bilingual (``*_en`` / ``*_km``); the web layer picks the field for
the reader's current language. LaTeX in ``latex`` / ``answer_latex`` / formula
notes is rendered with KaTeX on the client, so it must be bare LaTeX (no ``$``
delimiters).

Keyed by ``question_type`` — the same discriminator the complex generator and
``engine/core/skills.py`` already use, so a lesson round-trips against a skill
key of the form ``complex/<question_type>``.
"""
import json
from functools import lru_cache
from pathlib import Path

_LESSONS_PATH = Path(__file__).with_name("data") / "lessons.json"


@lru_cache(maxsize=1)
def _lessons() -> dict:
    with open(_LESSONS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def lesson_question_types() -> set[str]:
    """Question types that have an authored lesson."""
    return set(_lessons().keys())


def get_lesson(question_type: str) -> dict | None:
    """The authored lesson for one complex question type, or ``None``.

    Returns a copy with ``topic``/``question_type`` stamped on so the payload is
    self-describing, matching the shape the web ``LessonModal`` expects.
    """
    lesson = _lessons().get(question_type)
    if lesson is None:
        return None
    return {"topic": "complex", "question_type": question_type, **lesson}
