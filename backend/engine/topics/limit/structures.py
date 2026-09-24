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
import zlib

from sympy import E, Symbol, expand, latex, oo, pi, sympify
from sympy.parsing.latex import parse_latex

from .rational_structures import RATIONAL_STRUCTURES
from .radical_structures import RADICAL_STRUCTURES
from .trig_structures import TRIG_STRUCTURES
from .exponential_structures import EXPONENTIAL_STRUCTURES
from .logarithmic_structures import LOGARITHMIC_STRUCTURES

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
                "expr_latex": expr_latex,
                "prompt_latex": ex.get("prompt_latex", ""),
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


# Symbolic slot-form template per technique — the limit analogue of integral's
# ``build_pattern_latex`` (``\int a x^2 + b x + c\,dx``). Limit techniques don't
# expose a machine-fillable slot pattern (the samplers emit concrete instances),
# so these are authored to mirror each sampler / curated family faithfully:
# coefficients as slot letters, the indeterminate form the technique resolves.
# Rendered in the admin template card's header, just like integral's pattern.
TEMPLATE_LATEX = {
    "direct_substitution": r"\lim_{x \to a} \dfrac{P(x)}{Q(x)}",
    "factoring_0_0": r"\lim_{x \to c} \dfrac{a x^{2} + b x + d}{e x^{2} + f x + g}\ \left(\tfrac{0}{0}\right)",
    "rationalization_conjugate_finite": r"\lim_{x \to a} \dfrac{x^{n} - a^{n}}{\sqrt{x + c} - d}",
    "trig_identity_0_0": r"\lim_{x \to a} \dfrac{\sin^{2} x - 1}{\sin x + 1}",
    "sinc_standard_limit": r"\lim_{x \to 0} \dfrac{c\,\sin(k x)}{x}",
    "angle_addition_0_0": r"\lim_{x \to a} \dfrac{a\sin x + b\cos x}{p x + q}\ \left(\tfrac{0}{0}\right)",
    "rationalization_sinc_combo": r"\lim_{x \to 0} \dfrac{\sqrt{a + x} - \sqrt{a - x}}{\sin(k x)}",
    "exponential_sinc_combo": r"\lim_{x \to 0} \dfrac{\left(e^{a x} + e^{-a x}\right)\sin^{2}(k x)}{2 x^{2}}",
    "half_angle_sinc_combo": r"\lim_{x \to 0} \dfrac{\sin(k x)\,\left(1 - \cos(m x)\right)}{x^{3}}",
    "exponential_standard_limit": r"\lim_{x \to 0} \dfrac{e^{a x} - 1}{e^{b x} - 1}",
    "conjugate_infinity": r"\lim_{x \to +\infty} \left(\sqrt{k^{2} x^{2} + b x + c} - (k x + d)\right)",
    "log_limit_infinity": r"\lim_{x \to +\infty} c\,x\left(\ln(x + k) - \ln x\right)",
    "rational_function_infinity": r"\lim_{x \to +\infty} \dfrac{a x^{2} + b x}{c x^{2} + d}",
    "log_limit_zero": r"\lim_{x \to 0^{+}} x\,\ln x",
    "indeterminate_one_infinity": r"\lim_{x \to a} f(x)^{g(x)}\ \left(1^{\infty}\right)",
}


def all_limit_techniques():
    return dict(LIMIT_TECHNIQUES)


def limit_source_label_map():
    """exam exercise id -> technique id, for every curated limit exercise."""
    return {item["id"]: item["formula_name"] for item in _LIMIT_CURATED_TEMPLATES}


# ---------------------------------------------------------------------------
# Parameterized Limit Structures (mirroring integral/structures.py)
# ---------------------------------------------------------------------------

def _sample_r1_linear(rng):
    a = rng.choice([2, 3, 4, 5])
    return f"(x**2 - {a*a})/(x - {a})", str(a), {"a": a}

def _sample_r1_quad(rng):
    a = rng.choice([2, 3, 4, 5])
    return f"(x**2 - {a*a})/(x**2 - {a}*x)", str(a), {"a": a}

def _sample_r2_diff_cubes(rng):
    a = rng.choice([1, 2, 3])
    return f"(x**3 - {a**3})/(x**2 - {a**2})", str(a), {"a": a}

def _sample_r2_sum_cubes(rng):
    a = rng.choice([1, 2, 3])
    b = rng.choice([1, 2])
    c = rng.choice([1, 3, 5])
    den = expand(sympify(f"(x + ({a}))*({b}*x + ({c}))"))
    return f"(x**3 + {a**3})/({den})", str(-a), {"a": a, "b": b, "c": c}

def _sample_r3_quad_linear(rng):
    c = rng.choice([-3, -2, 2, 3])
    b = rng.choice([-4, -1, 1, 4])
    num = expand(sympify(f"(x - ({c}))*(x + ({b}))"))
    den = expand(sympify(f"x - ({c})"))
    return f"({num})/({den})", str(c), {"c": c, "b": b}

def _sample_r3_quad_quad(rng):
    c = rng.choice([-2, -1, 1, 2, 3])
    a = rng.choice([-3, 1, 3])
    b = rng.choice([-4, -1, 2])
    num = expand(sympify(f"(x - ({c}))*(x + ({a}))"))
    den = expand(sympify(f"(x - ({c}))*(x + ({b}))"))
    return f"({num})/({den})", str(c), {"c": c, "a": a, "b": b}

def _sample_r4_quartic(rng):
    a = rng.choice([1, 2, 3])
    return f"(x**4 - {a**4})/(x - {a})", str(a), {"a": a}

def _sample_r5_shifted(rng):
    a = rng.choice([2, 3, 4])
    n = rng.choice([2, 3])
    return f"((x + {a})**{n} - {a**n})/x", "0", {"a": a, "n": n}

def _sample_r6_high_degree(rng):
    n = rng.choice([5, 10, 20, 50, 2015])
    return f"(x**{n} - 1)/(x - 1)", "1", {"n": n}

def _sample_c1_sqrt_num(rng):
    mode = rng.choice(["standard", "linear_minus_sqrt"])
    if mode == "linear_minus_sqrt":
        pairs = [(3, 2, 3), (4, 3, 4), (2, 1, 2), (5, 4, 5)]
        p, a, b = rng.choice(pairs)
        return f"(x - sqrt({a}*x + {b}))/(x - {p})", str(p), {"p": p, "a": a, "b": b}
    p = rng.choice([2, 3, 4, 7])
    d = rng.choice([1, 2, 3])
    c = d * d - p
    return f"(sqrt(x + ({c})) - {d})/(x - {p})", str(p), {"p": p, "d": d, "c": c}

def _sample_c1_sqrt_den(rng):
    mode = rng.choice(["linear", "cubic"])
    p = rng.choice([2, 3, 4])
    d = rng.choice([2, 3])
    c = d * d - p
    if mode == "cubic":
        return f"(x**3 - {p**3})/(sqrt(x + ({c})) - {d})", str(p), {"p": p, "d": d, "c": c}
    return f"(x - {p})/(sqrt(x + ({c})) - {d})", str(p), {"p": p, "d": d, "c": c}

def _sample_c2_two_sqrts(rng):
    a = rng.choice([1, 2, 3, 5])
    k = rng.choice([1, 2, 4])
    return f"(sqrt({a} + x) - sqrt({a} - x))/({k}*x)", "0", {"a": a, "k": k}

def _sample_c3_double_conj(rng):
    p = rng.choice([2, 3])
    b, d = 2, 3
    a = b * b - p
    c = d * d - p
    return f"(sqrt(x + ({a})) - {b})/(sqrt(x + ({c})) - {d})", str(p), {"p": p, "a": a, "b": b, "c": c, "d": d}

def _sample_c4_cbrt(rng):
    p = rng.choice([0, 1, 2])
    d = rng.choice([1, 2])
    c = d**3 - p
    return f"((x + ({c}))**(1/3) - {d})/(x - {p})", str(p), {"p": p, "d": d, "c": c}

def _sample_c5_split(rng):
    a = rng.choice([1, 2])
    k = rng.choice([1, 2])
    return f"((x + {a**3})**(1/3) - sqrt(x + {a**2}))/({k}*x)", "0", {"a": a, "k": k}

def _sample_inf_conjugate(rng):
    k = rng.choice([1, 2, 3])
    b = rng.choice([-4, 2, 4])
    c = rng.choice([1, 4, 9])
    d = rng.choice([-2, 0, 2])
    # A perfect-square radicand (b^2 == 4k^2c) collapses the root to |kx + m| and hangs SymPy.
    while b * b == 4 * k * k * c:
        b = rng.choice([-4, 2, 4])
        c = rng.choice([1, 4, 9])
    return f"sqrt({k*k}*x**2 + {b}*x + {c}) - ({k}*x + ({d}))", "oo", {"k": k, "b": b, "c": c, "d": d}

def _sample_inf_rational(rng):
    a, b = rng.choice([2, 3, 4]), rng.choice([1, 5])
    c, d = rng.choice([1, 2, 3]), rng.choice([2, 7])
    return f"({a}*x**2 + {b}*x)/({c}*x**2 + {d})", "oo", {"a": a, "b": b, "c": c, "d": d}

def _sample_trig_sinc(rng):
    k = rng.choice([2, 3, 4, 5])
    c = rng.choice([1, 2, 3])
    return f"{c}*sin({k}*x)/x" if c != 1 else f"sin({k}*x)/x", "0", {"k": k, "c": c}

def _sample_trig_half_angle(rng):
    m = rng.choice([2, 3, 4])
    b = rng.choice([1, 2])
    return f"(1 - cos({m}*x))/({b}*x**2)", "0", {"m": m, "b": b}

def _sample_exp_standard(rng):
    a = rng.choice([2, 3, 4])
    b = rng.choice([1, 5])
    return f"(exp({a}*x) - 1)/(exp({b}*x) - 1)", "0", {"a": a, "b": b}

def _sample_e1_diff_ratio(rng):
    """(e^{ax} - e^{bx})/x, (e^{ax} - 1)/x, or (e^{ax} + cx - 1)/x."""
    variant = rng.choice(["diff", "single", "linear_sum"])
    if variant == "diff":
        a = rng.choice([2, 3, 4, 5])
        b = rng.choice([-2, -1, 1, 2])
        if a == b:
            b = -b
        return f"(exp({a}*x) - exp({b}*x))/x", "0", {"a": a, "b": b}
    elif variant == "single":
        a = rng.choice([2, 3, 4, 5])
        k = rng.choice([1, 2, 3, 6])
        if k == 1:
            return f"(exp({a}*x) - 1)/x", "0", {"a": a}
        return f"(exp({a}*x) - 1)/({k}*x)", "0", {"a": a, "k": k}
    else:
        a = rng.choice([2, 3, 4])
        c = rng.choice([1, 2, 3])
        return f"(exp({a}*x) + {c}*x - 1)/x", "0", {"a": a, "c": c}

def _sample_e2_trig_combo(rng):
    """Exponential mixed with trigonometric functions."""
    variant = rng.choice([
        "sin_denom", "cos_diff", "exp_sin",
        "linear_sin_exp", "diff_two_sins", "sin_add_exp"
    ])
    if variant == "sin_denom":
        a = rng.choice([2, 3, 4, 5])
        b = rng.choice([-2, -1, 1, 2])
        if a == b:
            b = -b
        k = rng.choice([1, 2, 3])
        sin_part = f"sin({k}*x)" if k != 1 else "sin(x)"
        return f"(exp({a}*x) - exp({b}*x))/{sin_part}", "0", {"a": a, "b": b, "k": k}
    elif variant == "cos_diff":
        a = rng.choice([1, 2, 3])
        k = rng.choice([1, 2, 3])
        cos_part = f"cos({k}*x)" if k != 1 else "cos(x)"
        return f"(exp({a}*x**2) - {cos_part})/x**2", "0", {"a": a, "k": k}
    elif variant == "linear_sin_exp":
        a = rng.choice([1, 2, 3])
        b = rng.choice([1, 2])
        c = rng.choice([1, 2])
        c_part = f"{c}*x" if c != 1 else "x"
        return f"(exp({a}*x) + {b}*sin(x) - 1)/({c_part})", "0", {"a": a, "b": b, "c": c}
    elif variant == "diff_two_sins":
        a, b = rng.choice([3, 4]), rng.choice([1, 2])
        c, d = rng.choice([5, 6]), rng.choice([2, 4])
        if c == d:
            c = c + 1
        return f"(exp({a}*x) - exp({b}*x))/(sin({c}*x) - sin({d}*x))", "0", {"a": a, "b": b, "c": c, "d": d}
    elif variant == "sin_add_exp":
        a = rng.choice([1, 2, 3])
        b = rng.choice([1, 2])
        return f"({a}*sin(x) - 1 + exp({b}*x))/sin(x)", "0", {"a": a, "b": b}
    else:
        return "(exp(sin(x)) - 1)/x", "0", {}

def _sample_e3_quad_trinomial(rng):
    """Quadratic / trinomial in e^x at 0."""
    triplets = [
        (2, -3, 1),
        (1, -3, 2),
        (1, 1, -2),
        (3, -4, 1),
    ]
    a, b, c = rng.choice(triplets)
    b_term = f"+ {b}*exp(x)" if b > 0 else f"- {abs(b)}*exp(x)"
    c_term = f"+ {c}" if c > 0 else f"- {abs(c)}"
    a_term = f"{a}*exp(2*x)" if a != 1 else "exp(2*x)"
    return f"({a_term} {b_term} {c_term})/x", "0", {"a": a, "b": b, "c": c}

def _sample_eu1_rational(rng):
    """Indeterminate form 1^infinity with rational base as x -> +oo or 0."""
    variant = rng.choice(["monic_shift", "diff_ratio", "affine_ratio"])
    if variant == "monic_shift":
        a = rng.choice([-2, -1, 1, 2, 3, 4])
        a_term = f"+ {a}" if a > 0 else f"- {abs(a)}"
        return f"((x {a_term})/x)**x", "oo", {"a": a}
    elif variant == "diff_ratio":
        a = rng.choice([-2, -1, 1, 2])
        b = rng.choice([1, 2, 3, 4])
        if a == b:
            b = b + 1
        a_term = f"+ {a}" if a > 0 else f"- {abs(a)}"
        b_term = f"+ {b}" if b > 0 else f"- {abs(b)}"
        return f"((x {a_term})/(x {b_term}))**x", "oo", {"a": a, "b": b}
    else:
        return "((1 + x)/(1 - x))**(1/x)", "0", {}

def _sample_eu2_trig(rng):
    """Indeterminate form 1^infinity with trig or substitution at 0."""
    variant = rng.choice(["linear_power", "sin_power", "cos_power"])
    if variant == "linear_power":
        a = rng.choice([-3, -2, 2, 3])
        k = rng.choice([1, 2, 3])
        a_term = f"+ {a}*x" if a > 0 else f"- {abs(a)}*x"
        return f"(1 {a_term})**({k}/x)", "0", {"a": a, "k": k}
    elif variant == "sin_power":
        k = rng.choice([1, 2, 3])
        sin_part = f"sin({k}*x)" if k != 1 else "sin(x)"
        return f"(1 + {sin_part})**(1/x)", "0", {"k": k}
    else:
        k = rng.choice([1, 2])
        cos_part = f"cos({k}*x)" if k != 1 else "cos(x)"
        return f"({cos_part})**(1/x**2)", "0", {"k": k}

def _sample_e4_growth_infinity(rng):
    """Limits at infinity: ratio of exponentials or exponential growth dominance."""
    variant = rng.choice([
        "exp_ratio", "growth_poly", "diff_linear",
        "exp_poly_ratio", "poly_exp_prod", "exp_quad_ratio", "exp_poly_mix"
    ])
    if variant == "exp_ratio":
        a, b = rng.choice([2, 3]), rng.choice([1, 3])
        c, d = 1, rng.choice([1, 2])
        d_term = f"+ {d}"
        pt = rng.choice(["oo", "-oo"])
        return f"({a}*exp(x) + {b})/(exp(x) {d_term})", pt, {"a": a, "b": b, "c": c, "d": d}
    elif variant == "growth_poly":
        k = rng.choice([1, 2, 3])
        n = rng.choice([1, 2, 3])
        exp_part = f"exp({k}*x)" if k != 1 else "exp(x)"
        poly_part = f"x**{n}" if n != 1 else "x"
        return f"{exp_part}/{poly_part}", "oo", {"k": k, "n": n}
    elif variant == "poly_exp_prod":
        a = rng.choice([1, 2, 3])
        b = rng.choice([1, 2])
        pt = rng.choice(["oo", "-oo"])
        return f"(x**2 - {a}*x - {b})*exp(-x)", pt, {"a": a, "b": b}
    elif variant == "exp_poly_ratio":
        a = rng.choice([1, 2, 3])
        b = rng.choice([1, 2])
        c = rng.choice([2, 3])
        d = rng.choice([1, 2])
        pt = rng.choice(["oo", "-oo"])
        return f"({a}*exp(x) - {b}*x)/({c}*exp(x) + {d})", pt, {"a": a, "b": b, "c": c, "d": d}
    elif variant == "exp_quad_ratio":
        a = rng.choice([1, 2])
        c = rng.choice([1, 2])
        d = rng.choice([2, 3])
        pt = rng.choice(["oo", "-oo"])
        return f"({a}*exp(2*x) + exp(x) + 1)/({c}*exp(2*x) - exp(x) + {d})", pt, {"a": a, "c": c, "d": d}
    elif variant == "exp_poly_mix":
        a = rng.choice([1, 2])
        b = rng.choice([2, 3])
        pt = rng.choice(["oo", "-oo"])
        return f"(exp(x) + {a}*x**2)/(exp(x) - {b}*x**2)", pt, {"a": a, "b": b}
    else:
        return "(exp(x) - x)", "oo", {}

def _sample_l1_zero(rng):
    v = rng.choice(["scaled_arg", "linear_coeff", "quad_denom", "trig_denom", "exp_combo"])
    if v == "scaled_arg":
        a = rng.choice([2, 3, 5])
        b = rng.choice([2, 3, 4])
        c = rng.choice([1, 2, 4])
        return f"({a}*log(1 + {b}*x))/({c}*x)", "0", {"a": a, "b": b, "c": c}
    elif v == "quad_denom":
        a = rng.choice([2, 3])
        b = rng.choice([2, 3])
        return f"({a}*log(1 - {b}*x))/(x**2 - x)", "0", {"a": a, "b": b}
    elif v == "trig_denom":
        a = rng.choice([-3, 2, 3])
        k = rng.choice([1, 2])
        sin_part = f"sin({k}*x)" if k != 1 else "sin(x)"
        return f"({a}*log(x + 1))/{sin_part}", "0", {"a": a, "k": k}
    elif v == "exp_combo":
        a = rng.choice([1, 2])
        return f"(exp({a}*x) + sin(x) - 1)/log(x + 1)", "0", {"a": a}
    else:
        a = rng.choice([2, 3])
        c = rng.choice([2, 3])
        return f"({a}*log(x + 1))/({c}*x)", "0", {"a": a, "c": c}

def _sample_l2_rational(rng):
    v = rng.choice(["single_log", "diff_logs"])
    a = rng.choice([1, 2, 3])
    b = rng.choice([1, 2, 3])
    c = rng.choice([1, 2])
    d = rng.choice([1, 2, 3])
    if v == "single_log":
        return f"log(({a}*x + {b})/({c}*x + {d}))", "oo", {"a": a, "b": b, "c": c, "d": d}
    else:
        return f"log({a}*x + {b}) - log({c}*x + {d})", "oo", {"a": a, "b": b, "c": c, "d": d}

def _sample_l3_growth_zero(rng):
    v = rng.choice(["power_log", "poly_log_combo"])
    if v == "power_log":
        n = rng.choice([1, 2, 3])
        pwr = f"x**{n}" if n != 1 else "x"
        return f"{pwr}*log(x)", "0", {"n": n, "side": "+"}
    else:
        a = rng.choice([2, 3])
        return f"x**2/{a} + x - x*log(x)", "0", {"a": a, "side": "+"}

def _sample_l4_infinity(rng):
    v = rng.choice(["poly_dom", "quotient_log", "poly_mix"])
    if v == "quotient_log":
        a = rng.choice([2020, 10, 5])
        b = rng.choice([2, 3, 5])
        return f"({a} - {b}*log(x))/x", "oo", {"a": a, "b": b}
    elif v == "poly_mix":
        a = rng.choice([1, 2])
        return f"(x**2 - {a}*x*log(x) + 5)/x**2", "oo", {"a": a}
    else:
        a = rng.choice([1, 2])
        b = rng.choice([1, 2])
        return f"({a}*x**2 - {b}*x*log(x))", "oo", {"a": a, "b": b}

def _sample_log_infinity(rng):
    c = rng.choice([1, 2, 3])
    k = rng.choice([1, 2, 3])
    return f"{c}*x*(ln(x + {k}) - ln(x))", "oo", {"c": c, "k": k}

def _sample_euler_power(rng):
    a = rng.choice([1, 2, 3, 4])
    b = rng.choice([1, 2, 3])
    return f"(1 + {a}/x)**({b}*x)", "oo", {"a": a, "b": b}


LIMIT_STRUCTURES = [
    # --- Group 1: Rational Limits (30 Authentic BAC II Shapes) ---
    *RATIONAL_STRUCTURES,

    # --- Group 2: Radical / Conjugate Limits (24 Authentic BAC II Shapes) ---
    *RADICAL_STRUCTURES,

    # --- Group 3: Infinity Limits ---
    {
        "id": "limit:infinity:conjugate",
        "question_type": "limit",
        "category": "infinity",
        "subfamily": "conjugate",
        "shape": "INF1",
        "title_km": "គុណកន្សោមឆ្លាស់នៅអនន្ត (រាងអនន្តដកអនន្ត)",
        "title_en": "Conjugate at infinity (infinity minus infinity)",
        "difficulty": "hard",
        "pattern": "sqrt({k}**2*x**2 + {b}*x + {c}) - ({k}*x + {d})",
        "pattern_latex": r"\lim_{x \to +\infty} \left(\sqrt{k^{2} x^{2} + b x + c} - (k x + d)\right)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_inf_conjugate,
        "source_labels": ["2014c", "2019a"],
    },
    {
        "id": "limit:infinity:rational",
        "question_type": "limit",
        "category": "infinity",
        "subfamily": "rational",
        "shape": "INF2",
        "title_km": "លីមីតអនុគមន៍សនិទាននៅអនន្ត",
        "title_en": "Rational function at infinity",
        "difficulty": "hard",
        "pattern": "({a}*x**2 + {b}*x)/({c}*x**2 + {d})",
        "pattern_latex": r"\lim_{x \to +\infty} \dfrac{a x^{2} + b x}{c x^{2} + d}",
        "point": "oo",
        "var": "x",
        "sampler": _sample_inf_rational,
        "source_labels": ["2023a"],
    },

    # --- Group 4: Trigonometric Limits (43 Authentic BAC II Shapes) ---
    *TRIG_STRUCTURES,
    # --- Group 5: Exponential & Euler Limits (32 Authentic BAC II Shapes) ---
    *EXPONENTIAL_STRUCTURES,

    # --- Group 6: Logarithmic Limits (42 Authentic BAC II Shapes) ---
    *LOGARITHMIC_STRUCTURES,
]


def all_limit_structures():
    """Return all parameterized limit structure specifications."""
    return list(LIMIT_STRUCTURES)


def build_limit_pattern_latex(struct):
    """Return LaTeX string for structure card header."""
    return struct.get("pattern_latex") or struct["pattern"]


def _derive_limit_formula_tags(struct):
    if struct.get("formula_tags"):
        return ["setup_limit", *struct["formula_tags"]]
    sid = struct["id"]
    cat = struct.get("category", "")
    tags = ["setup_limit"]
    if cat == "rational":
        tags.append("factoring_0_0")
    elif cat == "radical":
        tags.append("rationalization_conjugate_finite")
    elif cat == "infinity":
        if "conjugate" in sid:
            tags.append("conjugate_infinity")
        else:
            tags.append("rational_function_infinity")
    elif cat == "trig":
        tags.append("sinc_standard_limit")
        if "double_angle" in sid:
            tags.append("trig_double_angle")
        elif "half_angle" in sid:
            tags.append("trig_half_angle")
        elif "sum_to_product" in sid:
            tags.append("trig_sum_to_product")
        elif "addition" in sid:
            tags.append("angle_addition_0_0")
    elif cat == "exponential":
        if "one_inf" in sid or "euler" in sid:
            tags.append("indeterminate_one_infinity")
        elif "growth" in sid or struct.get("point") == "oo":
            tags.append("exponential_infinity_growth")
        elif "trig" in sid:
            tags.extend(["exponential_sinc_combo", "sinc_standard_limit"])
        else:
            tags.append("exponential_standard_limit")
    elif cat == "logarithmic":
        if struct.get("point") == "oo":
            tags.append("log_limit_infinity")
        else:
            tags.append("log_limit_zero")
    return list(dict.fromkeys(tags))


def build_limit_sample(struct, seed):
    """Build a deterministic sample instance of the limit structure."""
    import random
    from engine.notation import pretty_expr, pretty_point
    from .solver import _solve_limit

    rng = random.Random(seed)
    expr, point_str, params = struct["sampler"](rng)
    var = struct.get("var", "x")

    solve_params = {
        "expr": expr,
        "point": point_str,
        "var": var,
        "formula_name": struct.get("shape", struct["id"]),
        "curated_technique": struct.get("title_km", struct.get("title_en", "")),
    }
    solve_params.update(params)

    solution = _solve_limit(solve_params)
    solution["formula_tags"] = _derive_limit_formula_tags(struct)
    side = solve_params.get("side")
    point_disp = pretty_point(point_str) + ("⁺" if side == "+" else "⁻" if side == "-" else "")
    prompt = f"lim({var} -> {point_disp}) of {pretty_expr(expr)}."
    pt_sym = solution.get("point")
    point_latex_str = (r"+\infty" if point_str == "oo" else r"-\infty" if point_str == "-oo" else latex(pt_sym) if pt_sym is not None else point_str)
    if side:
        point_latex_str += f"^{{{side}}}"
    expr_latex_str = latex(solution.get("given", expr), ln_notation=True)
    # Clean up awkward polynomial ordering of e^x - c + e^-x -> e^x + e^-x - c
    expr_latex_str = re.sub(
        r"([0-9]*\s*e\^\{[^\}]+\})\s*-\s*([0-9]+)\s*\+\s*([0-9]*\s*e\^\{-[^\}]+\})",
        r"\1 + \3 - \2",
        expr_latex_str,
    )
    # Clean up radical ordering so positive square root comes before negative: -\sqrt{...} + \sqrt{...} -> \sqrt{...} - \sqrt{...}
    expr_latex_str = re.sub(
        r"-\s*(\\sqrt\{[^\}]+\})\s*\+\s*(\\sqrt\{[^\}]+\})",
        r"\2 - \1",
        expr_latex_str,
    )
    prompt_latex = rf"\lim_{{{var} \to {point_latex_str}}} {expr_latex_str}"
    display = f"lim_{{{var} \\to {point_disp}}} {expr}"

    return {
        "structure": struct,
        "params": solve_params,
        "sample_params": params,
        "prompt": prompt,
        "prompt_latex": prompt_latex,
        "display": display,
        "solution": solution,
    }


def build_limit_variants(struct, count=3, seed=None):
    """Pre-generate up to `count` distinct parameter variants for a structure,
    each with SymPy solution, prompt_latex, and answer."""
    sampler = struct.get("sampler")
    if not sampler:
        return []
    variants = []
    seen_params = set()
    base_seed = (zlib.crc32(struct["id"].encode()) & 0xFFFFFFFF) if seed is None else seed
    for i in range(35):
        if len(variants) >= count:
            break
        try:
            sample = build_limit_sample(struct, seed=base_seed + i * 31337)
        except Exception:
            continue
        p = sample.get("sample_params") or {}
        sig = tuple(sorted((k, str(v)) for k, v in p.items()))
        if sig in seen_params and len(seen_params) < 15:
            continue
        seen_params.add(sig)
        sol = sample["solution"]
        variants.append({
            "variant_index": len(variants) + 1,
            "params": p,
            "prompt": sample["prompt"],
            "prompt_latex": sample["prompt_latex"],
            "answer_latex": sol.get("answer_latex") or latex(sol["answer_exact"], ln_notation=True),
            "answer_exact": str(sol["answer_exact"]),
            "steps": sol.get("steps", []),
        })
    return variants


