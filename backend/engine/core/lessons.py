"""Lesson lookup: the authored "how this exercise works" write-up for a skill.

A lesson is keyed by a **skill key** (``topic/question_type`` or
``topic/question_type:variant`` — the same key ``engine/core/skills.py``
produces), so the profile can ask "does this skill have a lesson?" and "give me
the lesson for this skill" without knowing which topic owns the content.

Lessons are authored once per topic and served verbatim (never LLM-generated),
so ``LESSON_SKILL_KEYS`` can be computed at import time and used as a cheap
``has_lesson`` check on every skill row of the profile. Only the complex-numbers
topic is populated today; adding a topic means importing its ``lessons`` module
here and extending the dispatch.
"""
from ..topics.complex import lessons as complex_lessons

#: Every skill key that currently has an authored lesson. Complex numbers only
#: for now — variantless, so the key is just ``complex/<question_type>``.
LESSON_SKILL_KEYS: set[str] = {
    f"complex/{qt}" for qt in complex_lessons.lesson_question_types()
}


def _split(skill_key: str) -> tuple[str, str]:
    """(topic, question_type) from a skill key, dropping any ``:variant``."""
    topic, _, rest = skill_key.partition("/")
    question_type = rest.partition(":")[0]
    return topic, question_type


def has_lesson(skill_key: str) -> bool:
    return skill_key in LESSON_SKILL_KEYS


def get_lesson(skill_key: str) -> dict | None:
    """The authored lesson for a skill key, or ``None`` if there isn't one."""
    topic, question_type = _split(skill_key)
    if topic == "complex":
        return complex_lessons.get_lesson(question_type)
    return None
