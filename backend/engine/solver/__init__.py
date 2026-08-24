"""SymPy-based solving for complex, limit, integral, and probability questions.
``solve()`` returns a solution dict; ``serialize()`` makes it JSON-safe."""
from .shared import (
    QUESTION_TYPES,
    QUESTION_TYPES_BY_TOPIC,
    _calc_locals,
    _formula_tags,
    format_z,
    inline_latex,
    z_latex,
)
from .solver import serialize, solve

__all__ = [
    "QUESTION_TYPES",
    "QUESTION_TYPES_BY_TOPIC",
    "_calc_locals",
    "_formula_tags",
    "format_z",
    "inline_latex",
    "serialize",
    "solve",
    "z_latex",
]
