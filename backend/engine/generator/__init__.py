"""Random problem generation for complex, limit, integral, and probability
questions (SymPy stays the source of truth for every answer)."""
from .generator import TOPICS, generate, variants_for_formula

__all__ = ["TOPICS", "generate", "variants_for_formula"]
