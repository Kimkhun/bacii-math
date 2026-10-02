"""Integrals use the default points policy (``engine/core/rubric.py``:
implied credit for condensed work), scored against the blueprint method the
work follows when a template has several (``core.rubric.method_rubric``)."""
from ...core.rubric import build_rubric, method_rubric

__all__ = ["build_rubric", "score_work", "select_method"]

score_work, select_method = method_rubric()
