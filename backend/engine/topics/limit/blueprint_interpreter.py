"""Blueprint interpreter for limit derivations.

Loads AI-generated parameter-preserving derivation blueprints and substitutes
runtime variant parameters ({k}, {a}, {b}, etc.) to produce clean, granular,
word-free textbook derivations and exact SymPy grading checkpoints.
"""

import json
import logging
import os
import re
from typing import Any

from sympy import S, Symbol, latex, sympify
from sympy.parsing.latex import parse_latex

logger = logging.getLogger(__name__)

# Search paths for blueprints file (docker container vs host workspace)
_BLUEPRINT_PATHS = [
    "/app/data/limit_blueprints.json",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "limit_blueprints.json"),
    os.path.join(os.path.dirname(__file__), "data", "limit_blueprints.json"),
]

_CACHED_BLUEPRINTS: dict[str, dict[str, Any]] | None = None


def load_blueprints(force_reload: bool = False) -> dict[str, dict[str, Any]]:
    global _CACHED_BLUEPRINTS
    if _CACHED_BLUEPRINTS is not None and not force_reload:
        return _CACHED_BLUEPRINTS

    for path in _BLUEPRINT_PATHS:
        normalized = os.path.abspath(path)
        if os.path.exists(normalized):
            try:
                with open(normalized, encoding="utf-8") as f:
                    _CACHED_BLUEPRINTS = json.load(f)
                    logger.info("Loaded %d limit blueprints from %s", len(_CACHED_BLUEPRINTS), normalized)
                    return _CACHED_BLUEPRINTS
            except Exception as e:
                logger.warning("Failed to load limit blueprints from %s: %e", normalized, e)

    _CACHED_BLUEPRINTS = {}
    return _CACHED_BLUEPRINTS


def has_blueprint(template_id: str) -> bool:
    blueprints = load_blueprints()
    return template_id in blueprints


def get_blueprint(template_id: str) -> dict[str, Any] | None:
    blueprints = load_blueprints()
    return blueprints.get(template_id)


def _substitute_params_in_text(text: str, params: dict[str, Any]) -> str:
    """Substitute parameters like {k}, {a}, {b}, {c1}, etc. into text."""
    result = text
    # Sort keys by length descending so {c1} is replaced before {c}
    for k in sorted(params.keys(), key=len, reverse=True):
        val = params[k]
        val_str = str(val)
        result = result.replace(f"{{{k}}}", val_str)

    # Cleanups for common algebraic multiplier formatting
    # Replace e.g. 1\left( with \left( if leading multiplier is 1
    result = re.sub(r"(?<![0-9])1\s*\\left\(", r"\\left(", result)
    # Replace 1 \cdot with nothing
    result = re.sub(r"(?<![0-9])1\s*\\cdot\s*", "", result)
    result = re.sub(r"\s*\\cdot\s*1(?![0-9])", "", result)
    # Clean double operators
    result = result.replace("+ -", "- ").replace("- -", "+ ")
    result = result.replace("+-", "-").replace("--", "+")
    return result


def interpret_blueprint_steps(
    template_id: str,
    params: dict[str, Any],
    var: str,
    point: Any,
    point_latex: str,
    expr: Any,
    result: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | tuple[None, None]:
    """Substitute runtime parameters into the blueprint for template_id.

    Returns:
        (steps, checkpoints) if blueprint exists, otherwise (None, None).
    """
    bp = get_blueprint(template_id)
    if not bp:
        return None, None

    raw_steps = bp.get("steps", [])
    raw_checkpoints = bp.get("checkpoints", [])

    steps = []
    for step_latex in raw_steps:
        sub_latex = _substitute_params_in_text(step_latex, params)
        # Ensure it has KaTeX block display delimiters
        steps.append({
            "title": "",
            "detail": rf"\[ {sub_latex} \]",
            "formula": None,
        })

    # Build checkpoints
    checkpoints = []
    for raw_cp in raw_checkpoints:
        sub_cp = _substitute_params_in_text(raw_cp, params)
        parsed_val = None
        # Try parsing as sympy or latex
        try:
            parsed_val = parse_latex(sub_cp)
        except Exception:
            try:
                parsed_val = sympify(sub_cp)
            except Exception:
                parsed_val = None

        if parsed_val is not None:
            checkpoints.append({
                "label": "intermediate form",
                "value": parsed_val,
                "formula": template_id,
            })

    # Always ensure the final graded result is a checkpoint
    checkpoints.append({
        "label": "final value",
        "value": result,
        "formula": template_id,
    })

    return steps, checkpoints
