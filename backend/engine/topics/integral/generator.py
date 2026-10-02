"""Integral generation: every question is sampled from the structure registry
(``structures.py``) — definite (polynomial, trig, linear_argument,
u_substitution, mixed_sum, by_parts) and indefinite (power, indefinite_sum,
expand, split, linear_argument, usub, trig_sec) — and records its structure
(``params["template_id"]``) and slot values + bounds
(``params["template_params"]``), so the structure's blueprint supplies the
graded steps. SymPy computes the answer at solve time."""
import re

from engine.core.expr_shared import _build_expr_problem, _expr_latex
from engine.notation import pretty_expr, pretty_point

from .structures import _bound_latex, all_integral_structures, structure_by_id

_INTEGRAL_VARIANT_BY_DIFFICULTY = {
    "easy": ["polynomial"],
    "medium": ["polynomial", "linear_argument", "mixed_sum"],
    "hard": ["trig", "u_substitution", "by_parts"],
}

_INDEFINITE_VARIANT_BY_DIFFICULTY = {
    "easy": ["power", "expand"],
    "medium": ["power", "expand", "split", "linear_argument"],
    "hard": ["usub", "split", "trig_sec", "linear_argument", "expand"],
}

_DEF = "definite_integral"
_IND = "indefinite_integral"

#: A sec^2 / csc^2 term (1/cos^2, 1/sin^2): what the "trig_sec" skill practises.
_SEC_CSC = re.compile(r"/(cos|sin)\(\{v\}\)\*\*2")


def _serves(struct, question_type, variant):
    """Whether `struct` answers a request for `variant` of `question_type`:
    its own variant, plus — as the old samplers did — the textbook sums for
    "power", and every sec^2/csc^2 shape for "trig_sec"."""
    if struct["question_type"] != question_type:
        return False
    if struct["variant"] == variant:
        return True
    if variant == "power":
        return struct["variant"] == "indefinite_sum"
    if variant == "trig_sec":
        return bool(_SEC_CSC.search(struct["pattern"]))
    return False


def _pick(rng, question_type, variant, difficulty):
    pool = [s for s in all_integral_structures() if _serves(s, question_type, variant)]
    if not pool:
        raise ValueError(f"no integral structure for {question_type} / {variant}")
    at_diff = [s for s in pool if s["difficulty"] == difficulty]
    return rng.choice(at_diff or pool)


def _build_indefinite(func, var, difficulty, variant, curated=False):
    params = {"expr": func, "var": var, "variant": variant, "curated": curated}
    prompt = f"Compute ∫ ({pretty_expr(func)}) d{var} (indefinite — include +C)."
    expr_latex = _expr_latex(func, var)
    prompt_latex = rf"\text{{Compute }} \int ({expr_latex})\,d{var} \text{{ (indefinite, +C)}}"
    display = f"\\int ({func})\\,d{var}"
    return _build_expr_problem("integral", _IND, params, difficulty, prompt, prompt_latex, display)


def _build_definite(params, difficulty):
    lower, upper, func, var = params["lower"], params["upper"], params["expr"], params["var"]
    return _build_expr_problem(
        "integral", _DEF, params, difficulty,
        f"Compute ∫ from {var} = {pretty_point(lower)} to {var} = {pretty_point(upper)} "
        f"of {pretty_expr(func)} d{var}.",
        rf"\text{{Compute }} \int_{{{_bound_latex(lower, var)}}}^{{{_bound_latex(upper, var)}}} "
        rf"{_expr_latex(func, var)}\,d{var}",
        f"\\int_{{{lower}}}^{{{upper}}} ({func})\\,d{var}",
    )


def generate_integral_for_structure(rng, struct, difficulty=None, variant=None):
    """One exercise sampled from a registry structure. `variant` is the skill
    it is recorded under (default: the structure's own)."""
    params, template_params = struct["sampler"](rng)
    difficulty = difficulty or struct["difficulty"]
    variant = "indefinite_sum" if struct["variant"] == "indefinite_sum" else (variant or struct["variant"])
    if struct["question_type"] == _IND:
        problem = _build_indefinite(params["expr"], params["var"], difficulty, variant,
                                    curated=struct["variant"] == "indefinite_sum")
    else:
        problem = _build_definite({**params, "variant": variant}, difficulty)
    problem["params"]["template_id"] = struct["id"]
    # Nested, so the grader never mistakes a slot name for a given.
    problem["params"]["template_params"] = template_params
    return problem


def _generate(rng, question_type, difficulty, variant, table):
    struct = structure_by_id(variant) if variant else None
    if struct is not None:
        return generate_integral_for_structure(rng, struct)
    if variant not in {v for vs in table.values() for v in vs} | {"indefinite_sum"}:
        variant = rng.choice(table[difficulty])
    return generate_integral_for_structure(rng, _pick(rng, question_type, variant, difficulty), difficulty, variant)


def _generate_integral(rng, difficulty, variant=None):
    """A definite integral: `variant` is a technique (see
    `_INTEGRAL_VARIANT_BY_DIFFICULTY`) or a structure id; unknown variants
    are ignored, so a stale practice link still yields a question."""
    return _generate(rng, _DEF, difficulty, variant, _INTEGRAL_VARIANT_BY_DIFFICULTY)


def _generate_indefinite(rng, difficulty, variant=None):
    """An indefinite integral: `variant` is a technique (see
    `_INDEFINITE_VARIANT_BY_DIFFICULTY`, plus "indefinite_sum" — the
    textbook's sums of basic terms) or a structure id."""
    return _generate(rng, _IND, difficulty, variant, _INDEFINITE_VARIANT_BY_DIFFICULTY)
