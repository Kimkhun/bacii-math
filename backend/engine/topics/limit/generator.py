"""Limit generation: procedural technique samplers, parameterized per structure/technique."""
from sympy import expand, latex, oo, sympify

from engine.core.expr_shared import _build_expr_problem, _expr_latex, _fmt_poly
from engine.notation import pretty_expr, pretty_point

from .structures import LIMIT_STRUCTURES, LIMIT_TECHNIQUES


_LIMIT_TECHNIQUES_BY_DIFFICULTY = {}
for _tid, _meta in LIMIT_TECHNIQUES.items():
    if _meta["parameterizable"]:
        _LIMIT_TECHNIQUES_BY_DIFFICULTY.setdefault(_meta["difficulty"], []).append(_tid)


def _point_latex(point):
    r"""Render the limit point as LaTeX (pi -> \pi, pi/6 -> \frac{\pi}{6})."""
    try:
        return latex(sympify(str(point)))
    except Exception:
        return str(point)


def _point_display(point):
    return str(point).replace("pi", "π")


def _build_sampled_limit(technique, expr, point, difficulty, side=None):
    point_latex = r"+\infty" if point == "oo" else _point_latex(point)
    point_display = "+∞" if point == "oo" else _point_display(point)
    if side:
        # One-sided limit (the two-sided limit doesn't exist): the side must be
        # shown to the student, and the solver reads params["side"] for dir=.
        point_latex += f"^{{{side}}}"
        point_display += side
    params = {"expr": expr, "var": "x", "point": point}
    if side:
        params["side"] = side
    prompt = f"lim(x → {point_display}) of {pretty_expr(expr)}"
    expr_latex = _expr_latex(expr)
    prompt_latex = rf"\lim_{{x \to {point_latex}}} {expr_latex}"
    display = f"lim_{{x \\to {point_display}}} {expr}"
    return _build_expr_problem("limit", "limit", params, difficulty, prompt, prompt_latex, display)


def generate_limit_for_technique(rng, technique, difficulty=None):
    """Sample one procedurally-generated instance of a specific parameterizable
    limit technique using authentic textbook structures."""
    candidates = [
        s for s in LIMIT_STRUCTURES
        if s.get("id") == technique or s.get("subfamily") == technique
        or s.get("category") == technique or s.get("shape") == technique
    ]
    pool = candidates or [s for s in LIMIT_STRUCTURES if s.get("difficulty") == difficulty] or LIMIT_STRUCTURES
    chosen = rng.choice(pool)
    expr, point, slots = chosen["sampler"](rng)
    diff = chosen.get("difficulty", difficulty or "medium")
    prob = _build_sampled_limit(chosen["id"], expr, point, diff, slots.get("side"))
    prob["params"]["technique"] = chosen["id"]
    prob["params"]["title_km"] = chosen.get("title_km")
    prob["params"]["formula_name"] = chosen.get("shape", chosen["id"])
    prob["params"].update(slots)
    return prob



# Dropdown items that cover several structure subfamilies (mirrors the grouping
# in web/src/app/admin/page.tsx, so /practice and /admin agree).
_SUBFAMILY_GROUPS = {
    ("trig", "half_angle"): {"half_angle", "double_angle", "quadratic"},
}


def _generate_limit(rng, difficulty, variant=None):
    if variant:
        norm_variant = variant[6:] if variant.startswith("limit:") else variant
        # Category/family match (e.g. "rational", "radical", "trig", "exponential", "logarithmic", "infinity")
        cat_pool = [
            s for s in LIMIT_STRUCTURES
            if s.get("category") == norm_variant
            or (norm_variant in ("exponential", "exp_log") and s.get("category") == "exponential")
            or (norm_variant in ("logarithmic", "log") and s.get("category") == "logarithmic")
        ]
        if cat_pool:
            at_diff = [s for s in cat_pool if s.get("difficulty") == difficulty]
            chosen = rng.choice(at_diff or cat_pool)
            expr, point, slots = chosen["sampler"](rng)
            prob = _build_sampled_limit(chosen["id"], expr, point, chosen.get("difficulty", difficulty), slots.get("side"))
            prob["params"]["technique"] = chosen["id"]
            prob["params"]["title_km"] = chosen.get("title_km")
            prob["params"]["formula_name"] = chosen.get("shape", chosen["id"])
            prob["params"].update(slots)
            return prob

        # Subfamily match (e.g. "rational:powers", "exponential:zero", "exponential:one_inf", "logarithmic:zero", etc.)
        subfam_pool = []
        if ":" in variant:
            parts = variant.split(":")
            cat_part = parts[-2] if len(parts) >= 2 and parts[-2] != "limit" else None
            sub_part = parts[-1]
            sub_set = _SUBFAMILY_GROUPS.get((cat_part, sub_part), {sub_part})
            subfam_pool = [
                s for s in LIMIT_STRUCTURES
                if s.get("subfamily") in sub_set and (
                    not cat_part or s.get("category") == cat_part
                    or (cat_part in ("exponential", "exp_log") and s.get("category") == "exponential")
                    or (cat_part in ("logarithmic", "log") and s.get("category") == "logarithmic")
                )
            ]
        if subfam_pool:
            at_diff = [s for s in subfam_pool if s.get("difficulty") == difficulty]
            chosen = rng.choice(at_diff or subfam_pool)
            expr, point, slots = chosen["sampler"](rng)
            prob = _build_sampled_limit(chosen["id"], expr, point, chosen.get("difficulty", difficulty), slots.get("side"))
            prob["params"]["technique"] = chosen["id"]
            prob["params"]["title_km"] = chosen.get("title_km")
            prob["params"]["formula_name"] = chosen.get("shape", chosen["id"])
            prob["params"].update(slots)
            return prob

        # Specific structure id match (e.g. "limit:rational:diff_cubes" or "diff_cubes")
        matching = [s for s in LIMIT_STRUCTURES if s["id"] == variant or s["id"].endswith(f":{variant}")]
        if matching:
            chosen = matching[0]
            expr, point, slots = chosen["sampler"](rng)
            prob = _build_sampled_limit(chosen["id"], expr, point, chosen.get("difficulty", difficulty), slots.get("side"))
            prob["params"]["technique"] = chosen["id"]
            prob["params"]["title_km"] = chosen.get("title_km")
            prob["params"]["formula_name"] = chosen.get("shape", chosen["id"])
            prob["params"].update(slots)
            return prob

        return generate_limit_for_technique(rng, variant, difficulty)

    # Sample from LIMIT_STRUCTURES matching difficulty, or all structures
    matching_structs = [s for s in LIMIT_STRUCTURES if s.get("difficulty") == difficulty]
    pool = matching_structs or LIMIT_STRUCTURES
    chosen = rng.choice(pool)
    expr, point, slots = chosen["sampler"](rng)
    prob = _build_sampled_limit(chosen["id"], expr, point, chosen.get("difficulty", difficulty), slots.get("side"))
    prob["params"]["technique"] = chosen["id"]
    prob["params"]["title_km"] = chosen.get("title_km")
    prob["params"]["formula_name"] = chosen.get("shape", chosen["id"])
    prob["params"].update(slots)
    return prob