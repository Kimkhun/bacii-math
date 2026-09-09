"""Curated limit exercises and the technique registry.

``_LIMIT_CURATED_TEMPLATES`` is the curated pool for limits: the 37 real BAC
II limit exercises (2014-2025), pre-sorted by solution technique into
``data/curated/{formula_name}.json`` (via ``scripts/verify_limits.py``'s
categorization) and parsed once at import time into ready-to-solve SymPy
expr/point pairs. Each entry carries the SymPy expr + point the
generator/solver replay to grade it (SymPy stays the source of truth for the
answer), plus the exam-authored technique text used as the step-by-step
narration.

``LIMIT_TECHNIQUES`` is the technique registry: one entry per solution
technique (not per parameterized shape). Flags parameterizability so the
generator can draw a dynamic sampler for parameterizable techniques or fall
back to curated-only BAC II templates for ones where coefficients don't
generalize cleanly.
"""
import glob
import json
import os
import re

from sympy import E, Symbol, oo, pi
from sympy.parsing.latex import parse_latex

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "curated")

_DIFFICULTY_BY_CATEGORY = {
    "direct_substitution": "easy",
    "factoring_0_0": "easy",
    "rationalization_conjugate_finite": "medium",
    "trig_identity_0_0": "medium",
    "sinc_standard_limit": "medium",
    "angle_addition_0_0": "medium",
    "rationalization_sinc_combo": "medium",
    "exponential_sinc_combo": "medium",
    "half_angle_sinc_combo": "medium",
    "exponential_standard_limit": "medium",
    "conjugate_infinity": "hard",
    "log_limit_infinity": "hard",
    "rational_function_infinity": "hard",
    "log_limit_zero": "hard",
    "indeterminate_one_infinity": "hard",
}

_PI_SYMBOL = Symbol("pi")
_E_SYMBOL = Symbol("e")


def _latex_to_sympy(latex_str):
    s = re.sub(r"\\sqrt(\d)", r"\\sqrt{\1}", latex_str.strip())
    expr = parse_latex(s)
    if _PI_SYMBOL in expr.free_symbols:
        expr = expr.subs(_PI_SYMBOL, pi)
    if _E_SYMBOL in expr.free_symbols:
        expr = expr.subs(_E_SYMBOL, E)
    return expr


def _find_group(s, open_idx):
    """s[open_idx] must be '{'. Return (content, index_after_closing_brace)."""
    depth = 0
    for i in range(open_idx, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[open_idx + 1:i], i + 1
    raise ValueError("unbalanced braces")


def _extract_lim(latex_str):
    """Pull (point_latex, expr_latex) out of a '\\lim_{x\\to POINT} EXPR[, given ...]'
    prompt. Returns None if the structure can't be found."""
    m = re.search(r"\\lim_\{", latex_str)
    if not m:
        return None
    content, close_idx = _find_group(latex_str, m.end() - 1)
    mm = re.match(r"x\s*\\to\s*(.+)", content)
    if not mm:
        return None
    point_latex = mm.group(1)
    # Drop a trailing "given ..." hint clause (e.g. "\ \text{given }...").
    expr_latex = re.split(r",?\s*\\,?\\text\{", latex_str[close_idx:])[0].strip()
    return point_latex, expr_latex


def _to_point(point_latex):
    p = point_latex.strip()
    if p in (r"+\infty", r"\infty"):
        return oo
    if p == r"-\infty":
        return -oo
    return _latex_to_sympy(p)


def _load_limit_curated():
    items = []
    for fpath in sorted(glob.glob(os.path.join(_DATA_DIR, "*.json"))):
        try:
            data = json.load(open(fpath, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        category = data["formula_name"]
        difficulty = _DIFFICULTY_BY_CATEGORY.get(category, "medium")
        for ex in data.get("exercises", []):
            found = _extract_lim(ex["prompt_latex"])
            if not found:
                continue
            point_latex, expr_latex = found
            try:
                point = _to_point(point_latex)
                expr = _latex_to_sympy(expr_latex)
            except Exception:
                # A handful of exam prompts don't round-trip through
                # antlr's LaTeX grammar (e.g. an implicit "find a" ask
                # rather than a plain limit) — skip, don't crash the pool.
                continue
            items.append({
                "id": ex["id"],
                "formula_name": category,
                "difficulty": difficulty,
                "var": "x",
                "expr": expr,
                "point": point,
                "answer_latex": ex["answer_latex"],
                "technique": ex["technique"],
                "formula_latex": ex.get("formula_latex", ""),
            })
    return items


_LIMIT_CURATED_TEMPLATES = _load_limit_curated()


LIMIT_TECHNIQUES = {
    "direct_substitution": {
        "difficulty": "easy",
        "parameterizable": True,
        "description": "Evaluate by substituting the target point directly into polynomial, rational, or exponential expressions.",
    },
    "factoring_0_0": {
        "difficulty": "easy",
        "parameterizable": True,
        "description": "0/0 indeterminate form resolved by factoring the common (x-c) root from numerator and denominator, cancelling, and substituting.",
    },
    "rationalization_conjugate_finite": {
        "difficulty": "medium",
        "parameterizable": True,
        "description": "0/0 at a finite point involving a square root: multiply by the conjugate to rationalize, then cancel and substitute.",
    },
    "trig_identity_0_0": {
        "difficulty": "medium",
        "parameterizable": False,
        "description": "0/0 at a finite point using a Pythagorean/trig identity (e.g. sin^2x-1, 1-cos^2x) to factor and cancel. Curated-only: "
                        "the identity only collapses cleanly at specific angles (sin/cos = 0, +-1), so it doesn't generalize to free coefficients.",
    },
    "sinc_standard_limit": {
        "difficulty": "medium",
        "parameterizable": True,
        "description": "0/0 at x=0 using the standard limit sin(kx)/(kx) -> 1, possibly after a linear substitution.",
    },
    "angle_addition_0_0": {
        "difficulty": "medium",
        "parameterizable": False,
        "description": "0/0 at x=pi/3 (or similar): rewrite a linear combination a*sin x + b*cos x via the angle-addition identity as "
                        "R*sin(x - phi), then apply the sinc limit. Curated-only: only specific (a, b, point) triples form a known angle.",
    },
    "rationalization_sinc_combo": {
        "difficulty": "medium",
        "parameterizable": True,
        "description": "0/0 at x=0 combining conjugate rationalization of a square-root numerator with the standard sinc limit sin x / x -> 1.",
    },
    "exponential_sinc_combo": {
        "difficulty": "medium",
        "parameterizable": True,
        "description": "0/0 at x=0 combining a continuous exponential factor with the standard sinc-squared limit (sin x / x)^2 -> 1.",
    },
    "half_angle_sinc_combo": {
        "difficulty": "medium",
        "parameterizable": True,
        "description": "0/0 at x=0 combining sin x factoring with the half-angle limit (1-cos x)/x^2 -> 1/2 and/or the sinc limit.",
    },
    "exponential_standard_limit": {
        "difficulty": "medium",
        "parameterizable": True,
        "description": "0/0 at x=0 using the standard exponential limit (e^{kx}-1)/x -> k.",
    },
    "conjugate_infinity": {
        "difficulty": "hard",
        "parameterizable": True,
        "description": "Infinity minus infinity at infinity involving a square root: multiply and divide by the conjugate to collapse the "
                        "difference, then divide by the dominant power.",
    },
    "log_limit_infinity": {
        "difficulty": "hard",
        "parameterizable": True,
        "description": "Indeterminate form at infinity involving logarithms: reduce to the standard limit ln(1+u)/u -> 1 as u -> 0.",
    },
    "rational_function_infinity": {
        "difficulty": "hard",
        "parameterizable": True,
        "description": "Infinity/infinity at infinity for a rational function: the limit of same-degree polynomial ratios equals the ratio "
                        "of leading coefficients.",
    },
    "log_limit_zero": {
        "difficulty": "hard",
        "parameterizable": False,
        "description": "Indeterminate limit as x->0 involving logarithms (e.g. x*ln(x) -> 0).",
    },
    "indeterminate_one_infinity": {
        "difficulty": "hard",
        "parameterizable": False,
        "description": "1^infinity indeterminate forms resolved via standard exponential limits.",
    },
}


def all_limit_techniques():
    return dict(LIMIT_TECHNIQUES)


def limit_source_label_map():
    """exam exercise id -> technique id, for every curated limit exercise."""
    return {item["id"]: item["formula_name"] for item in _LIMIT_CURATED_TEMPLATES}
