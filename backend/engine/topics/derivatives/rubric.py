"""Derivatives points rubric — full marks only for complete work.

Two rules differ from the default (``engine/core/rubric.py``):

  * No implied credit. A step earns its points only when the work shows
    its value; a right final answer with a skipped or wrong intermediate
    step (u', v', the inner derivative, ...) loses that step's points, so
    10/10 means every step and the answer are shown and correct.
  * A step written as a term of a sum is shown: ``y' = 4 - 2e^{-2x}``
    shows ``(e^{-2x})' = -2e^{-2x}``. Only literal terms count, so a step
    that disappears into the simplified answer (u' in the chain rule)
    still has to be written.
  * Chained lines count per part. ``y' = 2x(x+3)(x+4) + x^2(2x+7) = ...``
    is matched part by part ("="-separated), so steps written as one chain
    still earn their points.

A template's blueprint may have several methods (alternative solution
paths, ``engine/core/blueprints.py``); the work is scored against the one it
follows (`select_method`), and ``grading.analyze_work`` marks the lines
against that same method, so the ✓/✗ marks and the points always agree.
"""
import json
from functools import lru_cache

from sympy import latex

from ...core.dispatch import solve
from ...core.rubric import DEFAULT_QUESTION_POINTS, build_rubric, pick_method, score_rubric

__all__ = ["build_rubric", "score_work", "select_method"]


def _score(topic, question_type, params, lines, question_points, tolerance, part_label, method):
    rubric = build_rubric(topic, question_type, params, question_points, part_label, method)
    result = score_rubric(topic, question_type, params, rubric, lines, tolerance,
                          implied_credit=False, split_chains=True, term_credit=True)
    # What each step is, with this question's numbers, so a missed step can
    # be shown to the student ("not shown: (e^{-2x})' = -2e^{-2x}").
    for step, entry in zip(rubric, result["breakdown"]):
        if step.get("label_latex"):
            entry["label_latex"] = step["label_latex"]
        entry["expected"] = str(step["value"])
        entry["expected_latex"] = latex(step["value"])
    return result


def select_method(topic, question_type, params, lines, question_points=DEFAULT_QUESTION_POINTS,
                  tolerance=None, part_label=None):
    """The blueprint method the work follows (None with fewer than two)."""
    key = (topic, question_type, json.dumps(params, sort_keys=True, default=str),
           tuple(lines), question_points, tolerance, part_label)
    return _select_method_cached(key)


@lru_cache(maxsize=256)
def _select_method_cached(key):
    topic, question_type, params_json, lines, question_points, tolerance, part_label = key
    params = json.loads(params_json)
    methods = solve(topic, question_type, params).get("methods") or []
    if len(methods) < 2:
        return None
    return pick_method(methods, lambda m: _score(topic, question_type, params, list(lines),
                                                  question_points, tolerance, part_label, m))


def score_work(topic, question_type, params, lines, question_points=DEFAULT_QUESTION_POINTS,
               tolerance=None, part_label=None):
    """Score the work against the method it follows, reported as "method"."""
    method = select_method(topic, question_type, params, lines, question_points, tolerance, part_label)
    result = _score(topic, question_type, params, lines, question_points, tolerance, part_label, method)
    if method:
        result["method"] = method
    return result
