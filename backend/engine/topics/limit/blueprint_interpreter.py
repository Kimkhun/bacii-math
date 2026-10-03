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

from sympy import Rational, S, Symbol, latex, sympify
from sympy.parsing.latex import parse_latex

logger = logging.getLogger(__name__)

# Search paths for blueprints file (docker container vs host workspace)
_BLUEPRINT_PATHS = [
    "/app/engine/topics/limit/data/blueprints.json",
    "/app/data/limit_blueprints.json",
    os.path.join(os.path.dirname(__file__), "data", "blueprints.json"),
    os.path.join(os.path.dirname(__file__), "data", "limit_blueprints.json"),
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "limit_blueprints.json"),
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
                    loaded = json.load(f)
                    # Reject corrupt control characters
                    for tid, bp in loaded.items():
                        for s in bp.get("steps", []) + bp.get("checkpoints", []):
                            if any(ch in s for ch in ("\r", "\t", "\f", "\b")):
                                raise ValueError(f"Corrupt control character in limit blueprint {tid}")
                    _CACHED_BLUEPRINTS = loaded
                    logger.info("Loaded %d limit blueprints from %s", len(_CACHED_BLUEPRINTS), normalized)
                    return _CACHED_BLUEPRINTS
            except Exception as e:
                logger.warning("Failed to load limit blueprints from %s: %e", normalized, e)

    _CACHED_BLUEPRINTS = {}
    return _CACHED_BLUEPRINTS


# Template ids renamed because they collided with a /practice dropdown group of
# the same name; questions saved before the rename still carry the old id.
_RENAMED_TEMPLATE_IDS = {
    "limit:trig:sinc_standard": "limit:trig:sinc_kx",
    "limit:trig:half_angle": "limit:trig:one_minus_cos",
}


def has_blueprint(template_id: str) -> bool:
    return get_blueprint(template_id) is not None


def get_blueprint(template_id: str) -> dict[str, Any] | None:
    blueprints = load_blueprints()
    return blueprints.get(_RENAMED_TEMPLATE_IDS.get(template_id, template_id))


def _substitute_params_in_text(text: str, params: dict[str, Any]) -> str:
    """Substitute parameters like {k}, {a}, {b}, {c1}, etc. into text smartly.

    Resolves algebraic coefficients like 3{k}, glued parameters like {c1}{a}^2 -> 3 * 1^2,
    reduces unsimplified fractions like \\dfrac{{k}x}{2} -> 2x when k=4, and cleans redundant 1x -> x.
    """
    s = text

    # Handle digit + glued params with power: (\d+)\s*\{p1\}\s*\{p2\}\^(\d+) -> d * (v1 * (v2 ** p))
    # e.g. 2{k}{a}^2 -> 2 * 2 * 9 = 36, 3{k}{a}^2 -> 3 * 1 * 4 = 12, 6{k}{a}^2 -> 6 * k * a^2
    def repl_digit_glued_pow(m):
        d = int(m.group(1))
        p1, p2, p = m.group(2), m.group(3), int(m.group(4))
        if p1 in params and p2 in params:
            v1, v2 = params[p1], params[p2]
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                return str(d * int(v1) * (int(v2) ** p))
        return m.group(0)

    s = re.sub(r"(\d+)\s*\{([a-zA-Z0-9_]+)\}\s*\{([a-zA-Z0-9_]+)\}\^(\d+)", repl_digit_glued_pow, s)

    # Handle digit + glued params: (\d+)\s*\{p1\}\s*\{p2\} -> d * v1 * v2
    def repl_digit_glued(m):
        d = int(m.group(1))
        p1, p2 = m.group(2), m.group(3)
        if p1 in params and p2 in params:
            v1, v2 = params[p1], params[p2]
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                return str(d * int(v1) * int(v2))
        return m.group(0)

    s = re.sub(r"(\d+)\s*\{([a-zA-Z0-9_]+)\}\s*\{([a-zA-Z0-9_]+)\}", repl_digit_glued, s)

    # Handle power + power glued params: \{p1\}\^(\d+)\s*\{p2\}\^(\d+) -> (v1**p1) * (v2**p2)
    # e.g. {a}^3 {b}^2 -> 27 * 4 = 108
    def repl_glued_pow_pow(m):
        p1, pow1, p2, pow2 = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
        if p1 in params and p2 in params:
            v1, v2 = params[p1], params[p2]
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                return str((int(v1) ** pow1) * (int(v2) ** pow2))
        return m.group(0)

    s = re.sub(r"\{([a-zA-Z0-9_]+)\}\^(\d+)\s*\{([a-zA-Z0-9_]+)\}\^(\d+)", repl_glued_pow_pow, s)

    # Handle glued parameter braces: {p1}{p2}^(\d+) -> (val1 * (val2 ** p))
    def repl_glued_pow(m):
        p1, p2, p = m.group(1), m.group(2), int(m.group(3))
        if p1 in params and p2 in params:
            v1, v2 = params[p1], params[p2]
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                return str(int(v1) * (int(v2) ** p))
        return m.group(0)

    s = re.sub(r"\{([a-zA-Z0-9_]+)\}\s*\{([a-zA-Z0-9_]+)\}\^(\d+)", repl_glued_pow, s)

    # Handle glued parameter braces: {p1}{p2} -> (val1 * val2)
    def repl_glued(m):
        p1, p2 = m.group(1), m.group(2)
        if p1 in params and p2 in params:
            v1, v2 = params[p1], params[p2]
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                return str(int(v1) * int(v2))
        return m.group(0)

    s = re.sub(r"\{([a-zA-Z0-9_]+)\}\s*\{([a-zA-Z0-9_]+)\}", repl_glued, s)

    for k, val in params.items():
        if isinstance(val, (int, float)):
            # Reduce \dfrac{{k}x}{den} -> (val // den)x or \dfrac{val x}{den}
            def repl_kx_den(m):
                coeff = int(val)
                den = int(m.group(1))
                if coeff % den == 0:
                    reduced = coeff // den
                    if reduced == 1:
                        return "x"
                    elif reduced == -1:
                        return "-x"
                    else:
                        return f"{reduced}x"
                return f"\\dfrac{{{coeff}x}}{{{den}}}"

            s = re.sub(rf"\\d?frac\{{\{{{k}\}}\s*x\}}{{(\d+)}}", repl_kx_den, s)

            # Reduce inline slash {k}x/den -> (val // den)x
            def repl_kx_slash(m):
                coeff = int(val)
                den = int(m.group(1))
                if coeff % den == 0:
                    reduced = coeff // den
                    if reduced == 1:
                        return "x"
                    elif reduced == -1:
                        return "-x"
                    else:
                        return f"{reduced}x"
                return f"{coeff}x/{den}"

            s = re.sub(rf"\{{{k}\}}\s*x/(\d+)", repl_kx_slash, s)

            # Reduce \dfrac{{k}}{den} -> integer if divisible
            def repl_k_den(m):
                coeff = int(val)
                den = int(m.group(1))
                if coeff % den == 0:
                    return str(coeff // den)
                return f"\\dfrac{{{coeff}}}{{{den}}}"

            s = re.sub(rf"\\d?frac\{{\{{{k}\}}\}}{{(\d+)}}", repl_k_den, s)

            # Handle multiplied power: (\d+)\{k\}\^(\d+) -> e.g. 3{k}^2 -> 3 * val^2
            def repl_digit_k_pow(m):
                d = int(m.group(1))
                p = int(m.group(2))
                return str(d * (int(val) ** p))

            s = re.sub(rf"(\d+)\{{{k}\}}\^(\d+)", repl_digit_k_pow, s)

            # Handle multiplied coefficient: (\d+)\{k\} -> e.g. 2{a}, 3{k} -> d * val
            def repl_digit_k(m):
                d = int(m.group(1))
                return str(d * int(val))

            s = re.sub(rf"(\d+)\{{{k}\}}", repl_digit_k, s)

            # Handle exponentiation: \{k\}\^(\d+) -> val^p
            def repl_k_pow(m):
                p = int(m.group(1))
                return str(int(val) ** p)

            s = re.sub(rf"\{{{k}\}}\^(\d+)", repl_k_pow, s)

    # Standard replacement of remaining {param} keys (longer keys first)
    for k, val in sorted(params.items(), key=lambda item: len(item[0]), reverse=True):
        s = s.replace(f"{{{k}}}", str(val))

    # Cleanups for common algebraic multiplier formatting
    s = re.sub(r"(?<![0-9])1\s*\\left\(", r"\\left(", s)
    # A leading factor 1 (not an exponent/subscript 1 or the end of a number)
    s = re.sub(r"(?<![0-9.^_])1\s*\\cdot\s*", "", s)
    # A trailing factor 1, (1), 1^2, (1)^{3}: only a whole factor, never the
    # "(1" that opens a sum like "(1 + \cos x)", and its power goes with it
    s = re.sub(r"\s*\\cdot\s*(?:\(1\)|1)(?:\^(?:\{\d+\}|\d+))?(?![0-9.])", "", s)

    # Clean redundant coefficient 1 for standalone variables (e.g. 1x -> x, \cos(1x) -> \cos(x), 1t/2 -> t/2)
    s = re.sub(r"(?<![0-9])1([a-zA-Z])(?![a-zA-Z])", r"\1", s)

    # Clean double operators
    s = s.replace("+ -", "- ").replace("- -", "+ ")
    s = s.replace("+-", "-").replace("--", "+")

    # If an equality ends with unreduced numerical fraction '= \dfrac{a}{b}' where a is divisible by b
    def repl_final_frac(m):
        num = int(m.group(1))
        den = int(m.group(2))
        if den != 0 and num % den == 0:
            return f"= {num // den}"
        return m.group(0)

    s = re.sub(r"=\s*\\d?frac\{(\d+)\}\{(\d+)\}", repl_final_frac, s)
    return s


def _clean_evaluation_line(s: str, result_latex: str) -> str:
    """Standardize final evaluation arithmetic:
    1. Reduce product terms like C \\cdot \\frac{N}{D} \\cdot (1)^2:
       e.g. 2 \\cdot \\frac{4}{4} \\cdot (1)^2 -> 2
            2 \\cdot \\frac{16}{4} \\cdot (1)^2 -> 8
            6 \\cdot \\frac{1}{4} \\cdot (1)^2 -> \\frac{3}{2}
            4 \\cdot \\frac{9}{4} \\cdot (1)^2 -> 9
    2. Reduce standalone fraction constants like \\frac{4}{4} -> 1, \\frac{16}{4} -> 4.
    3. Branch on term types:
       - Case A (All terms are integers, e.g. '= 2 + 8 = ...'):
         Drop any awkward forced fraction like \\frac{4 + 16}{2}, rendering directly as:
         '= 2 + 8 = 10'
       - Case B (Fractions present, e.g. '= \\frac{3}{2} - 9 = \\frac{3 - 18}{2} = -\\frac{15}{2}'):
         Keep the common denominator step and conclude with exact result_latex.
    """
    def repl_prod(m):
        if m.lastindex == 3:
            c = int(m.group(1)) if m.group(1) else 1
            num = int(m.group(2))
            den = int(m.group(3))
        else:
            c = 1
            num = int(m.group(1))
            den = int(m.group(2))
        r = Rational(c * num, den)
        if r.q == 1:
            return str(r.p)
        return rf"\dfrac{{{r.p}}}{{{r.q}}}"

    s = re.sub(r"(\d+)\s*\\cdot\s*\\d?frac\{(\d+)\}\{(\d+)\}\s*\\cdot\s*\(1\)\^2", repl_prod, s)
    s = re.sub(r"\\d?frac\{(\d+)\}\{(\d+)\}\s*\\cdot\s*\(1\)\^2", repl_prod, s)

    # Reduce standalone fraction constants like \dfrac{4}{4} -> 1, \dfrac{16}{4} -> 4
    def repl_frac_const(m):
        num = int(m.group(1))
        den = int(m.group(2))
        if den != 0 and num % den == 0:
            return str(num // den)
        return m.group(0)

    s = re.sub(r"\\d?frac\{(\d+)\}\{(\d+)\}", repl_frac_const, s)

    # Clean double operators
    s = s.replace("+ -", "- ").replace("- -", "+ ")
    s = s.replace("+-", "-").replace("--", "+")

    # Case A: Check for integer addition/subtraction on left: '= N1 [+-] N2 = ...'
    m_int = re.search(r"=\s*(\d+)\s*([+-])\s*(\d+)\s*=", s)
    if m_int:
        n1 = int(m_int.group(1))
        op = m_int.group(2)
        n2 = int(m_int.group(3))
        ans = n1 + n2 if op == "+" else n1 - n2
        return f"= {n1} {op} {n2} = {ans}"

    # Case B: Has fractions or other terms
    if result_latex:
        norm_s = s.replace("\\dfrac", "\\frac").rstrip()
        norm_res = result_latex.replace("\\dfrac", "\\frac").strip()
        if not norm_s.endswith(norm_res):
            s = f"{s} = {result_latex}"

    return s


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
    result_latex = latex(result, ln_notation=True) if result is not None else ""
    for i, step_latex in enumerate(raw_steps):
        sub_latex = _substitute_params_in_text(step_latex, params)

        # On the final step, ensure clean evaluation arithmetic and exact result
        if i == len(raw_steps) - 1:
            sub_latex = _clean_evaluation_line(sub_latex, result_latex)

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
