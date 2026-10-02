"""Differential-equation generation: every question is sampled from the
structure registry (``structures.py``) — no verbatim curated exercises (each
of those is an instance of a structure). SymPy's dsolve recomputes the
solution at solve time. Every question records its structure
(``params["template_id"]``) and slot values (``params["template_params"]``)."""
import random
import zlib

from sympy import Symbol, latex, sympify

from .structures import ODE_KINDS, ODE_STRUCTURES, STRUCTURES_BY_ID, instantiate

_KIND_LABEL = {
    "first_order_linear_homogeneous": "y' + a y = 0",
    "first_order_linear_nonhomogeneous": "y' + a y = g(x)",
    "second_order_homogeneous_constant_coeff": "y'' + b y' + c y = 0",
    "second_order_nonhomogeneous": "y'' + b y' + c y = g(x)",
}


def _term(coeff_str, symbol, first):
    """Render one 'coeff * symbol' term with a leading sign, e.g. '- 4y'' or
    '+ y'. Returns '' if the coefficient is zero."""
    c = sympify(coeff_str)
    if c == 0:
        return ""
    sign = "-" if c < 0 else ("" if first else "+")
    mag = abs(c)
    mag_str = "" if mag == 1 else latex(mag)
    spacer = " " if not first else ""
    return f"{spacer}{sign} {mag_str}{symbol}".replace("  ", " ")


def _equation_latex(item):
    kind = item["kind"]
    locals_ = {"x": Symbol("x")}
    if kind in ("first_order_linear_homogeneous", "first_order_linear_nonhomogeneous"):
        a_term = _term(item["a"], "y", first=False)
        lhs = f"y'{a_term}" if a_term else "y'"
        rhs = "0" if kind == "first_order_linear_homogeneous" else latex(sympify(item.get("rhs", 0), locals=locals_))
        return rf"{lhs} = {rhs}"

    b_term = _term(item["b"], "y'", first=False)
    c_term = _term(item["c"], "y", first=False)
    lhs = f"y''{b_term}{c_term}"
    rhs = latex(sympify(item.get("rhs", 0), locals=locals_)) if kind == "second_order_nonhomogeneous" else "0"
    return rf"{lhs} = {rhs}"


def _ics_latex(ics):
    if not ics:
        return None
    x0_l = latex(sympify(ics["x0"]))
    y0_l = latex(sympify(ics["y0"]))
    parts = [rf"y({x0_l}) = {y0_l}"]
    if ics.get("yp0") is not None:
        yp0_l = latex(sympify(ics["yp0"]))
        parts.append(rf"y'({x0_l}) = {yp0_l}")
    return r",\ ".join(parts)


def _build_problem(item):
    params = dict(item)
    display = _KIND_LABEL.get(item["kind"], item["kind"])
    eq_l = _equation_latex(item)
    ics_l = _ics_latex(item.get("ics"))
    prompt_latex = rf"\text{{Solve: }} {eq_l}" + (rf"\\[4pt] \text{{with }} {ics_l}." if ics_l else r"\text{ (general solution).}")
    return {
        "topic": "differential_equations",
        "question_type": "solve_ode",
        "difficulty": item.get("difficulty", "medium"),
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": f"Solve the differential equation: {display}"
        + (" with the given initial conditions." if item.get("ics") else " (find the general solution)."),
        "prompt_latex": prompt_latex,
        "source": "generated",
    }


_KINDS = ODE_KINDS


def _structure_problem(struct, values, difficulty=None):
    params = {
        **instantiate(struct, values),
        "difficulty": difficulty or struct["difficulty"],
        "var": struct["var"],
        "curated_technique": struct["narration"],
        "template_id": struct["id"],
        # Nested, so the grader never mistakes a slot name for a given.
        "template_params": dict(values),
    }
    return _build_problem(params)


def generate_ode_for_structure(rng, struct, difficulty=None):
    """One exercise sampled from a registry structure."""
    _, values = struct["sampler"](rng)
    return _structure_problem(struct, values, difficulty)


def generate_ode_for_kind(rng, kind, difficulty="medium"):
    """One exercise of an ODE kind: a structure of that kind at `difficulty`
    (any difficulty if the kind has none there)."""
    pool = [s for s in ODE_STRUCTURES if s["category"] == kind]
    at_diff = [s for s in pool if s["difficulty"] == difficulty]
    return generate_ode_for_structure(rng, rng.choice(at_diff or pool), difficulty)


def _generate_differential_equations(rng, difficulty, question_type=None, variant=None):
    """`variant` is an ODE `kind` (first/second order, homogeneous or not) or a
    structure id from the registry (e.g. "ode:second_hom:double_root");
    unknown variants are ignored rather than fatal, so a stale practice link
    still yields a question."""
    if question_type not in (None, "solve_ode"):
        raise ValueError(f"question_type {question_type} does not match topic differential_equations")
    if variant in STRUCTURES_BY_ID:
        return generate_ode_for_structure(rng, STRUCTURES_BY_ID[variant])
    kind = variant if variant in _KINDS else rng.choice(_KINDS)
    return generate_ode_for_kind(rng, kind, difficulty)


def build_ode_variant(struct, seed=0, template_params=None):
    """One worked example of a structure for the admin template card: the
    sampled (or, with `template_params`, the given) exercise plus SymPy's
    answer and steps."""
    from ...core.dispatch import solve

    if template_params is None:
        problem = generate_ode_for_structure(random.Random(seed), struct)
    else:
        problem = _structure_problem(struct, template_params)
    sol = solve("differential_equations", "solve_ode", problem["params"])
    return {
        "params": problem["params"]["template_params"],
        "prompt": problem["prompt"],
        "prompt_latex": problem["prompt_latex"],
        "answer_exact": str(sol["answer_exact"]),
        "answer_latex": sol["answer_latex"],
        "steps": sol.get("steps", []),
        "formula_tags": sol.get("formula_tags", []),
    }


def build_ode_variants(struct, count=3, seed=None):
    """Up to `count` distinct worked variants (distinct slot values)."""
    base = (zlib.crc32(struct["id"].encode()) & 0xFFFFFFFF) if seed is None else seed
    variants, seen = [], set()
    for i in range(20):
        if len(variants) >= count:
            break
        v = build_ode_variant(struct, base + i * 31337)
        sig = tuple(sorted(v["params"].items()))
        if sig in seen:
            continue
        seen.add(sig)
        variants.append({"variant_index": len(variants) + 1, **v})
    return variants
