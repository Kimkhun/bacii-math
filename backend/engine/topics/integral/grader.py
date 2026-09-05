"""Integrals use the generic grading core unchanged (the indefinite-integral
"any F(x)+C" rule is a one-line dispatch on ``question_type`` inline in
``engine.core.grading``, not a distinct rule)."""
from ...core.grading import analyze_work, grade, grade_part, parse_answer

__all__ = ["analyze_work", "grade", "grade_part", "parse_answer"]
