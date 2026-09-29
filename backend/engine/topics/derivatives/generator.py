"""Derivative generation: every question is sampled from the structure
registry (``structures.py``) — no verbatim curated exercises. SymPy
recomputes the derivative at solve time. Every question records its
structure (``params["template_id"]``) and slot values
(``params["template_params"]``)."""
import random
import zlib

from sympy import Symbol, latex, sympify

from .structures import DERIVATIVE_STRUCTURES, DERIVATIVE_TECHNIQUES, STRUCTURES_BY_ID


def _derivative_shape(item):
    """Legacy expression-text classifier, kept only to bucket questions
    stored before template tagging (they carry just ``expr``/``order``)."""
    if item.get("order", 1) == 2:
        return "second_order"
    expr = item.get("expr", "")
    if "log" in expr:
        return "logarithm"
    if "exp" in expr:
        return "exponential"
    if any(fn in expr for fn in ("sin", "cos", "tan")):
        return "trigonometric"
    if "sqrt" in expr:
        return "radical"
    if "/" in expr:
        return "quotient"
    if ")**" in expr:
        return "chain"
    if ")*" in expr or "*(" in expr:
        return "product"
    return "polynomial"


def _build_problem(params, order, expr_text):
    label = "second derivative" if order == 2 else "derivative"
    prime = "y''" if order == 2 else "y'"
    var = params["var"]
    expr_l = latex(sympify(expr_text, locals={var: Symbol(var)}))
    display = f"{label} of y = {expr_text}"
    return {
        "topic": "derivatives",
        "question_type": "compute_derivative",
        "difficulty": params.get("difficulty", "medium"),
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": f"Compute the {label} of y = {expr_text}.",
        "prompt_latex": rf"\text{{Compute }} {prime} \text{{ for }} y = {expr_l}.",
        "source": "generated",
    }


def _structure_problem(struct, expr, values, difficulty=None):
    params = {
        "difficulty": difficulty or struct["difficulty"],
        "var": struct["var"],
        "expr": str(expr),
        "order": struct["order"],
        "curated_technique": struct["narration"],
        "technique": struct["category"],
        "template_id": struct["id"],
        "template_params": dict(values),
    }
    return _build_problem(params, struct["order"], params["expr"])


def generate_derivative_for_structure(rng, struct, difficulty=None):
    """One procedurally-sampled exercise from a registry structure."""
    expr, values = struct["sampler"](rng)
    return _structure_problem(struct, expr, values, difficulty)


def generate_derivative_for_technique(rng, technique, difficulty="medium"):
    """One procedurally-sampled exercise for a differentiation technique:
    a structure of that category at `difficulty` (any difficulty if the
    category has none there)."""
    pool = [s for s in DERIVATIVE_STRUCTURES if s["category"] == technique]
    at_diff = [s for s in pool if s["difficulty"] == difficulty]
    return generate_derivative_for_structure(rng, rng.choice(at_diff or pool), difficulty)


def _generate_derivatives(rng, difficulty, question_type=None, variant=None):
    """`variant` is a differentiation technique (see `DERIVATIVE_TECHNIQUES`),
    a structure id from the registry (e.g. "deriv:product:three_factors"), or
    the legacy "order_1"/"order_2". Unknown variants are ignored."""
    if question_type not in (None, "compute_derivative"):
        raise ValueError(f"question_type {question_type} does not match topic derivatives")
    if variant in STRUCTURES_BY_ID:
        return generate_derivative_for_structure(rng, STRUCTURES_BY_ID[variant])
    if variant in ("order_1", "order_2"):
        order = int(variant[-1])
        pool = [s for s in DERIVATIVE_STRUCTURES if s["order"] == order]
        at_diff = [s for s in pool if s["difficulty"] == difficulty]
        return generate_derivative_for_structure(rng, rng.choice(at_diff or pool), difficulty)
    technique = variant if variant in DERIVATIVE_TECHNIQUES else rng.choice(DERIVATIVE_TECHNIQUES)
    return generate_derivative_for_technique(rng, technique, difficulty)


def build_derivative_variant(struct, seed=0, template_params=None):
    """One worked example of a structure for the admin template card: the
    sampled (or, with `template_params`, the given) exercise plus SymPy's
    answer and steps."""
    from ...core.dispatch import solve
    from .structures import instantiate

    if template_params is None:
        problem = generate_derivative_for_structure(random.Random(seed), struct)
    else:
        problem = _structure_problem(struct, instantiate(struct, template_params), template_params)
    sol = solve("derivatives", "compute_derivative", problem["params"])
    return {
        "params": problem["params"]["template_params"],
        "prompt": problem["prompt"],
        "prompt_latex": problem["prompt_latex"],
        "answer_exact": str(sol["answer_exact"]),
        "answer_latex": sol["answer_latex"],
        "steps": sol.get("steps", []),
        "formula_tags": sol.get("formula_tags", []),
    }


def build_derivative_variants(struct, count=3, seed=None):
    """Up to `count` distinct worked variants (distinct slot values)."""
    base = (zlib.crc32(struct["id"].encode()) & 0xFFFFFFFF) if seed is None else seed
    variants, seen = [], set()
    for i in range(20):
        if len(variants) >= count:
            break
        v = build_derivative_variant(struct, base + i * 31337)
        sig = tuple(sorted(v["params"].items()))
        if sig in seen:
            continue
        seen.add(sig)
        variants.append({"variant_index": len(variants) + 1, **v})
    return variants
