"""Limit generation: 50% curated real BAC II exercises / 50% procedural technique samplers."""
from sympy import expand, latex, oo, sympify

from engine.core.expr_shared import _build_expr_problem, _expr_latex, _fmt_poly
from engine.notation import pretty_expr, pretty_point

from .structures import LIMIT_STRUCTURES, LIMIT_TECHNIQUES, _LIMIT_CURATED_TEMPLATES


def _sample_direct_substitution(rng):
    c = rng.randint(-4, 4)
    kind = rng.choice(["polynomial", "rational", "exponential"])
    if kind == "rational":
        a = rng.randint(-5, 5)
        b = rng.choice([v for v in range(-5, 6) if v != -c])
        expr = f"(x + {a})/(x + {b})"
    elif kind == "exponential":
        k = rng.choice([v for v in range(-3, 4) if v != 0])
        expr = f"(exp({k}*x) + 1)/(2*exp({k}*x))"
    else:
        p, q, r = rng.randint(1, 3), rng.randint(-5, 5), rng.randint(-5, 5)
        expr = _fmt_poly(p, q, r)
    return expr, str(c), {}


def _sample_factoring_0_0(rng):
    for _ in range(20):
        c = rng.randint(-5, 5)
        g1, g0 = rng.randint(-4, 4), rng.randint(-4, 4)
        h1, h0 = rng.randint(1, 4), rng.randint(-4, 4)
        if g1 == 0 and g0 == 0:
            continue
        if h1 * c + h0 == 0:
            continue
        num = expand(sympify(f"(x - ({c}))*({g1}*x + {g0})"))
        den = expand(sympify(f"(x - ({c}))*({h1}*x + {h0})"))
        return f"({num})/({den})", str(c), {}
    raise RuntimeError("could not sample factoring_0_0")


def _sample_rational_function_infinity(rng):
    p = rng.randint(1, 5)
    q = rng.randint(-9, 9)
    r = rng.randint(1, 5)
    s = rng.randint(-9, 9)
    num = _fmt_poly(p, q, 0)
    den = _fmt_poly(r, 0, s)
    return f"({num})/({den})", "oo", {}


def _sample_sinc_standard_limit(rng):
    k = rng.randint(1, 9)
    c = rng.randint(1, 9)
    expr = f"{c}*sin({k}*x)/x" if c != 1 else f"sin({k}*x)/x"
    return expr, "0", {"k": k, "c": c}


def _sample_exponential_standard_limit(rng):
    a = rng.choice([v for v in range(-6, 7) if v != 0])
    b = rng.choice([v for v in range(-6, 7) if v != 0 and v != a])
    expr = f"(exp({a}*x) - 1)/(exp({b}*x) - 1)"
    return expr, "0", {"a": a, "b": b}


def _sample_conjugate_infinity(rng):
    k = rng.randint(1, 4)
    b = rng.randint(-9, 9)
    c = rng.randint(0, 9)
    d = rng.randint(-9, 9)
    while b * b == 4 * k * k * c:
        b = rng.randint(-9, 9)
    expr = f"sqrt({k * k}*x**2 + {b}*x + {c}) - ({k}*x + ({d}))"
    return expr, "oo", {"k": k, "b": b, "c": c, "d": d}


def _sample_rationalization_conjugate_finite(rng):
    p = rng.randint(-4, 4)
    d = rng.randint(1, 6)
    n = rng.choice([2, 3])
    c = d * d - p
    num = expand(sympify(f"x**{n} - ({p})**{n}"))
    expr = f"({num})/(sqrt(x + ({c})) - ({d}))"
    return expr, str(p), {"p": p, "d": d, "c": c, "n": n}


def _sample_rationalization_sinc_combo(rng):
    a = rng.randint(1, 9)
    k = rng.randint(1, 5)
    expr = f"(sqrt({a} + x) - sqrt({a} - x))/sin({k}*x)"
    return expr, "0", {"a": a, "k": k}


def _sample_exponential_sinc_combo(rng):
    a = rng.randint(1, 5)
    k = rng.randint(1, 5)
    expr = f"(exp({a}*x) + exp(-{a}*x))*sin({k}*x)**2/(2*x**2)"
    return expr, "0", {"a": a, "k": k}


def _sample_half_angle_sinc_combo(rng):
    k = rng.randint(1, 5)
    m = rng.randint(1, 5)
    expr = f"sin({k}*x)*(1 - cos({m}*x))/x**3"
    return expr, "0", {"k": k, "m": m}


def _sample_log_limit_infinity(rng):
    c = rng.randint(1, 9)
    k = rng.choice([v for v in range(-9, 10) if v != 0])
    expr = f"{c}*x*(ln(x + ({k})) - ln(x))" if c != 1 else f"x*(ln(x + ({k})) - ln(x))"
    return expr, "oo", {"c": c, "k": k}


_LIMIT_SAMPLERS = {
    "direct_substitution": _sample_direct_substitution,
    "factoring_0_0": _sample_factoring_0_0,
    "rational_function_infinity": _sample_rational_function_infinity,
    "sinc_standard_limit": _sample_sinc_standard_limit,
    "exponential_standard_limit": _sample_exponential_standard_limit,
    "conjugate_infinity": _sample_conjugate_infinity,
    "rationalization_conjugate_finite": _sample_rationalization_conjugate_finite,
    "rationalization_sinc_combo": _sample_rationalization_sinc_combo,
    "exponential_sinc_combo": _sample_exponential_sinc_combo,
    "half_angle_sinc_combo": _sample_half_angle_sinc_combo,
    "log_limit_infinity": _sample_log_limit_infinity,
}

_LIMIT_TECHNIQUES_BY_DIFFICULTY = {}
for _tid, _meta in LIMIT_TECHNIQUES.items():
    if _meta["parameterizable"]:
        _LIMIT_TECHNIQUES_BY_DIFFICULTY.setdefault(_meta["difficulty"], []).append(_tid)


def _point_latex(point):
    """Render the limit point as LaTeX (pi -> \\pi, pi/6 -> \\frac{\\pi}{6})."""
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
    limit technique. Used both by `_generate_limit`'s random pick and by the
    admin template-structures endpoint, which needs a deterministic sample per
    technique."""
    sampler = _LIMIT_SAMPLERS.get(technique)
    if sampler is None:
        raise ValueError(f"{technique} has no procedural sampler")
    expr, point, slots = sampler(rng)
    difficulty = difficulty or LIMIT_TECHNIQUES[technique]["difficulty"]
    problem = _build_sampled_limit(technique, expr, point, difficulty, slots.get("side"))
    problem["params"]["technique"] = technique
    problem["params"].update(slots)
    return problem


def _build_curated_limit(item, difficulty):
    """A real BAC II limit exercise from data/curated/{formula_name}.json,
    replayed through SymPy for the graded answer (technique text narrates the
    steps; see solver._solve_limit's `formula_name` branch)."""
    var = item["var"]
    expr, point = item["expr"], item["point"]
    point_str = "oo" if point is oo else "-oo" if point is -oo else str(point)
    params = {
        "expr": str(expr),
        "var": var,
        "point": point_str,
        "formula_name": item["formula_name"],
        "curated_technique": item["technique"],
        "curated_formula_latex": item["formula_latex"],
        "source_id": item["id"],
    }
    point_display = pretty_point(point_str)
    point_latex_str = r"+\infty" if point is oo else r"-\infty" if point is -oo else latex(point)
    prompt = f"lim({var} → {point_display}) of {pretty_expr(str(expr))}"
    expr_l = item.get("expr_latex") or latex(expr, ln_notation=True)
    prompt_latex = rf"\lim_{{{var} \to {point_latex_str}}} {expr_l}"
    display = f"lim_{{{var} \\to {point_display}}} {expr}"

    problem = _build_expr_problem("limit", "limit", params, difficulty, prompt, prompt_latex, display)
    problem["source"] = "curated"
    return problem


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

        if variant in _LIMIT_SAMPLERS:
            return generate_limit_for_technique(rng, variant, difficulty)
        if variant in LIMIT_TECHNIQUES:
            pool = [t for t in _LIMIT_CURATED_TEMPLATES if t["formula_name"] == variant]
            at_level = [t for t in pool if t["difficulty"] == difficulty]
            if pool:
                item = rng.choice(at_level or pool)
                return _build_curated_limit(item, difficulty if at_level else item["difficulty"])

    # If no variant or "any": sample from all LIMIT_STRUCTURES matching difficulty
    matching_structs = [s for s in LIMIT_STRUCTURES if s.get("difficulty") == difficulty]
    pool = matching_structs or LIMIT_STRUCTURES
    if pool and rng.random() < 0.7:
        chosen = rng.choice(pool)
        expr, point, slots = chosen["sampler"](rng)
        prob = _build_sampled_limit(chosen["id"], expr, point, chosen.get("difficulty", difficulty), slots.get("side"))
        prob["params"]["technique"] = chosen["id"]
        prob["params"]["title_km"] = chosen.get("title_km")
        prob["params"]["formula_name"] = chosen.get("shape", chosen["id"])
        prob["params"].update(slots)
        return prob

    curated_pool = [t for t in _LIMIT_CURATED_TEMPLATES if t["difficulty"] == difficulty]
    if curated_pool:
        return _build_curated_limit(rng.choice(curated_pool), difficulty)

    chosen = rng.choice(LIMIT_STRUCTURES)
    expr, point, slots = chosen["sampler"](rng)
    prob = _build_sampled_limit(chosen["id"], expr, point, chosen.get("difficulty", difficulty), slots.get("side"))
    prob["params"]["technique"] = chosen["id"]
    prob["params"]["title_km"] = chosen.get("title_km")
    prob["params"]["formula_name"] = chosen.get("shape", chosen["id"])
    prob["params"].update(slots)
    return prob