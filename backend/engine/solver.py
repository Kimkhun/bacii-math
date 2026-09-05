"""Public solving API — do not rename. Backed by ``engine.core`` (the generic
dispatcher + question-type registry) and each ``engine.topics.<topic>.solver``
module (the actual SymPy computation, one package per topic)."""
from .core.dispatch import serialize, solve
from .core.shared import (
    QUESTION_TYPES,
    QUESTION_TYPES_BY_TOPIC,
    _calc_locals,
    _formula_tags,
    format_z,
    inline_latex,
    z_latex,
)

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
