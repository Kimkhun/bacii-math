"""Formula catalog for tagged step-by-step checking.

`solver.py` emits a `formula` id on every step and on every checkpoint (the tag).
This module holds the *display metadata* and the *weight* used to derive difficulty
from the tags. It is content, not math: the ids originate in `solver.py` and must
never drift from it. Adding a new formula = register an id here and tag the solver's
steps/checkpoints with it; difficulty, line-checking and weakness stats then pick it
up with no other changes.
"""

_FORMULA_REGISTRY_BUILTIN = {
    # --- complex numbers ---
    "extract_real_imag": {
        "name_en": "Identify real & imaginary parts",
        "latex": r"z = a + bi,\quad a = \operatorname{Re}(z),\ b = \operatorname{Im}(z)",
        "weight": 0,
        "group": "complex",
    },
    "pythagorean": {
        "name_en": "Pythagorean theorem",
        "latex": r"|z| = \sqrt{a^2 + b^2}",
        "weight": 1,
        "group": "complex",
    },
    "sqrt_simplify": {
        "name_en": "Simplify a square root",
        "latex": r"\sqrt{a^2} = a",
        "weight": 1,
        "group": "complex",
    },
    "atan2_ratio": {
        "name_en": "Argument ratio (atan2)",
        "latex": r"\arg(z) = \operatorname{atan2}(b, a)",
        "weight": 1,
        "group": "complex",
    },
    "quadrant_adjustment": {
        "name_en": "Quadrant adjustment",
        "latex": r"\arg(z) \in (-\pi,\ \pi]",
        "weight": 1,
        "group": "complex",
    },
    "sign_flip": {
        "name_en": "Conjugate sign flip",
        "latex": r"\bar{z} = a - bi",
        "weight": 1,
        "group": "complex",
    },
    "extract_real": {
        "name_en": "Extract the real part",
        "latex": r"\operatorname{Re}(z) = a",
        "weight": 1,
        "group": "complex",
    },
    "extract_imag": {
        "name_en": "Extract the imaginary part",
        "latex": r"\operatorname{Im}(z) = b",
        "weight": 1,
        "group": "complex",
    },
    # --- limits ---
    "setup_limit": {
        "name_en": "Set up the limit",
        "latex": r"\lim_{x \to a} f(x)",
        "weight": 0,
        "group": "limit",
    },
    "direct_substitution": {
        "name_en": "Direct substitution",
        "latex": r"\lim_{x \to a} f(x) = f(a)",
        "weight": 1,
        "group": "limit",
    },
    "factor_difference_of_squares": {
        "name_en": "Factor a difference of squares",
        "latex": r"x^2 - a^2 = (x - a)(x + a)",
        "weight": 1,
        "group": "limit",
    },
    "cancel_common_factor": {
        "name_en": "Cancel a common factor",
        "latex": r"\frac{(x-a)P(x)}{(x-a)} = P(x)",
        "weight": 1,
        "group": "limit",
    },
    "divide_highest_power": {
        "name_en": "Divide by the highest power",
        "latex": r"\lim_{x\to\infty} \frac{P(x)}{Q(x)} = \lim_{x\to\infty}\frac{P/x^n}{Q/x^n}",
        "weight": 1,
        "group": "limit",
    },
    "leading_coefficient_ratio": {
        "name_en": "Leading coefficient ratio",
        "latex": r"\lim_{x\to\infty} \frac{ax^n}{bx^n} = \frac{a}{b}",
        "weight": 1,
        "group": "limit",
    },
    # --- integrals ---
    "setup_integral": {
        "name_en": "Set up the definite integral",
        "latex": r"\int_a^b f(x)\,dx",
        "weight": 0,
        "group": "integral",
    },
    "antiderivative_power_rule": {
        "name_en": "Power rule antiderivative",
        "latex": r"\int x^n\,dx = \frac{x^{n+1}}{n+1} + C",
        "weight": 1,
        "group": "integral",
    },
    "antiderivative_trig": {
        "name_en": "Trig antiderivative",
        "latex": r"\int \sin x\,dx = -\cos x + C,\quad \int \cos x\,dx = \sin x + C",
        "weight": 2,
        "group": "integral",
    },
    "fundamental_theorem": {
        "name_en": "Fundamental theorem of calculus",
        "latex": r"\int_a^b f(x)\,dx = F(b) - F(a)",
        "weight": 1,
        "group": "integral",
    },
    "expand_before_integrating": {
        "name_en": "Expand a product before integrating",
        "latex": r"f(x)\cdot g(x) = \text{sum of terms}",
        "weight": 1,
        "group": "integral",
    },
    "split_fraction": {
        "name_en": "Split a fraction term by term",
        "latex": r"\frac{a+b}{c} = \frac{a}{c} + \frac{b}{c}",
        "weight": 1,
        "group": "integral",
    },
    "integration_by_parts": {
        "name_en": "Integration by parts",
        "latex": r"\int u\,dv = uv - \int v\,du",
        "weight": 3,
        "group": "integral",
    },
}

# --- catalog overlays (editable content, loaded from JSON) ---

import glob
import json
import os

_TOPICS_DIR = os.path.join(os.path.dirname(__file__), "topics")


def _load_catalog_overlays():
    """Load each topic's engine/topics/<topic>/data/formulas.json (where
    present) and merge every entry over the built-in registry. This is where
    formula content (names, translations, LaTeX, the per-technique formula
    lists) lives so it can be edited without touching Python. Malformed
    files/entries are skipped; built-ins remain the fallback."""
    merged = {}
    fpaths = sorted(glob.glob(os.path.join(_TOPICS_DIR, "*", "data", "formulas.json")))
    for fpath in fpaths:
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        for tag, entry in data.items():
            if not isinstance(tag, str) or not tag or not isinstance(entry, dict):
                continue
            try:
                weight = float(entry.get("weight", 1.0))
            except (TypeError, ValueError):
                weight = 1.0
            merged[tag] = {
                "name_en": str(entry.get("name_en") or tag),
                "name_km": str(entry.get("name_km") or ""),
                "latex": entry.get("latex") or None,
                "weight": weight,
                "group": entry.get("group") or None,
                "formulas": entry.get("formulas") or [],
            }
    return merged


FORMULA_REGISTRY = {**_FORMULA_REGISTRY_BUILTIN, **_load_catalog_overlays()}

_FALLBACK = {
    "name_en": None,
    "latex": None,
    "weight": 1,
    "group": None,
    "formulas": [],
}


def resolve_formula(tag):
    """Return the registry entry for a tag, or a safe fallback for unknown ids so a
    future solver can never break existing questions (raw id is rendered, weight 1)."""
    entry = FORMULA_REGISTRY.get(tag)
    if entry is not None:
        return entry
    return {**_FALLBACK, "name_en": tag}


def formula_difficulty(tags):
    """Difficulty derived from formula weights.

    score = sum of the distinct tags' weights; score <= 1 -> easy, == 2 -> medium,
    >= 3 -> hard. Unknown tags fall back to weight 1 so they still affect the score.
    """
    score = sum(resolve_formula(t)["weight"] for t in dict.fromkeys(tags))
    if score <= 1:
        return "easy"
    if score == 2:
        return "medium"
    return "hard"
