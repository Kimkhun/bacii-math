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
from ...core.rubric import build_rubric, method_rubric

__all__ = ["build_rubric", "score_work", "select_method"]

score_work, select_method = method_rubric(implied_credit=False, split_chains=True, term_credit=True,
                                          prime_credit=True)
