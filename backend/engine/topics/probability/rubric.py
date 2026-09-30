"""Probability uses the default points rubric unchanged (engine/core/rubric.py:
steps derived from the solver's checkpoints, implied credit for condensed
work). Put this topic's own scoring rules here when it needs any."""
from ...core.rubric import build_rubric, default_score_work as score_work

__all__ = ["build_rubric", "score_work"]
