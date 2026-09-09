"""Public generation API — do not rename. Backed by ``engine.core.dispatch``
(routing) and each ``engine.topics.<topic>.generator`` module."""
from .core.dispatch import TOPICS, formulas_for_skill, generate, variants_for_formula

__all__ = ["TOPICS", "formulas_for_skill", "generate", "variants_for_formula"]
