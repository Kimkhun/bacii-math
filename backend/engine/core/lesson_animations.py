"""Lesson animations: the optional "Watch" video + "Explore" widget of a lesson.

A topic that has animated lessons keeps a ``data/animations.json`` next to its
``lessons.json``, keyed by the same lesson id::

    {"sinc_standard_limit": {
        "video": "limit/sinc_standard_limit",   # media path under the web's /animations
        "explorer": "sinc_standard_limit",      # interactive widget id (web registry)
        "version": "3f2a…", "duration": 74.2,   # written by animations/render.py
        "cues": [{"id": "approach", "start": 0.0, "end": 6.5,
                  "text_en": "…", "text_km": "…"}]}}

The videos themselves are rendered offline with Manim (``animations/``) and
carry no language: every word a student reads is a cue caption here, rendered
by the web under the video. So one video serves both languages, and fixing a
caption's wording never needs a re-render — only its timing comes from the
render (``start``/``end``/``duration``/``version`` are rewritten by
``animations/render.py``; ``id``/``text_*``/``video``/``explorer`` are authored).

Kept in its own file rather than inside ``lessons.json`` so the render step can
rewrite it mechanically without reformatting the hand-laid-out lesson text.

Formula tutorials (a worked example of one formula-sheet entry, shown on the
formula page) use the same block shape, but are keyed by formula id in a single
``engine/data/formula_animations.json`` rather than per topic.
"""
import json
from functools import lru_cache
from pathlib import Path

_FORMULA_ANIMATIONS = Path(__file__).resolve().parents[1] / "data" / "formula_animations.json"


@lru_cache(maxsize=None)
def load_animations(data_dir: Path) -> dict:
    """``{lesson_id: animation}`` for one topic's data dir; ``{}`` if it has none."""
    path = data_dir / "animations.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def with_animation(lesson: dict, data_dir: Path, lesson_id: str) -> dict:
    """``lesson`` plus its ``animation`` block, when one has been authored."""
    animation = load_animations(data_dir).get(lesson_id)
    return {**lesson, "animation": animation} if animation else lesson


@lru_cache(maxsize=1)
def _formula_animations() -> dict:
    if not _FORMULA_ANIMATIONS.exists():
        return {}
    with open(_FORMULA_ANIMATIONS, encoding="utf-8") as fh:
        return json.load(fh)


def formula_animation(formula_id: str) -> dict | None:
    """The tutorial animation for one formula-sheet entry, or None."""
    return _formula_animations().get(formula_id)
