"""Public points-rubric API — do not rename. Each topic owns its scoring
rules in ``engine/topics/<topic>/rubric.py`` (a module exposing
``build_rubric`` and ``score_work``, optionally ``select_method``); this
module routes a call to the question's topic. Most topics reuse the default
policy from ``engine/core/rubric.py``; derivatives has its own (full marks
only for complete work, alternative solution methods)."""
import importlib

from .core.rubric import DEFAULT_QUESTION_POINTS
from .core.shared import QUESTION_TYPES_BY_TOPIC

__all__ = ["DEFAULT_QUESTION_POINTS", "build_rubric", "score_work", "select_method", "topic_rubric"]


def topic_rubric(topic):
    """The topic's own rubric module."""
    if topic not in QUESTION_TYPES_BY_TOPIC:
        raise ValueError(f"unknown topic: {topic}")
    return importlib.import_module(f".topics.{topic}.rubric", __package__)


def build_rubric(topic, question_type, params, question_points=DEFAULT_QUESTION_POINTS, part_label=None):
    return topic_rubric(topic).build_rubric(topic, question_type, params, question_points, part_label)


def score_work(topic, question_type, params, lines, question_points=DEFAULT_QUESTION_POINTS,
               tolerance=None, part_label=None):
    return topic_rubric(topic).score_work(topic, question_type, params, lines, question_points,
                                          tolerance, part_label)


def select_method(topic, question_type, params, lines, tolerance=None):
    """Which blueprint method the work follows, per the topic's own rubric
    (None when the topic has no method selection)."""
    select = getattr(topic_rubric(topic), "select_method", None)
    return select(topic, question_type, params, lines, tolerance=tolerance) if select else None
