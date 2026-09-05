"""Limit generation: 50% curated real BAC II exercises / 50% procedural technique samplers."""
from sympy import expand, latex, oo, sympify

from engine.core.expr_shared import _build_expr_problem, _expr_latex, _fmt_poly
from engine.notation import pretty_expr, pretty_point

from .structures import LIMIT_TECHNIQUES, _LIMIT_CURATED_TEMPLATES


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


def _build_sampled_limit(technique, expr, point, difficulty):
    point_latex = r"+\infty" if point == "oo" else str(point)
    point_display = "+∞" if point == "oo" else str(point)
    params = {"expr": expr, "var": "x", "point": point}
    prompt = f"Find lim(x → {point_display}) of {pretty_expr(expr)}."
    expr_latex = _expr_latex(expr)
    prompt_latex = rf"\text{{Find }} \lim_{{x \to {point_latex}}} {expr_latex}"
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
    problem = _build_sampled_limit(technique, expr, point, difficulty)
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
    prompt = f"Find lim({var} → {point_display}) of {pretty_expr(str(expr))}."
    prompt_latex = rf"\text{{Find }} \lim_{{{var} \to {point_latex_str}}} {latex(expr)}"
    display = f"lim_{{{var} \\to {point_display}}} {expr}"

    problem = _build_expr_problem("limit", "limit", params, difficulty, prompt, prompt_latex, display)
    problem["source"] = "curated"
    return problem


def _generate_limit(rng, difficulty, variant=None):
    if variant and variant in _LIMIT_SAMPLERS:
        return generate_limit_for_technique(rng, variant, difficulty)

    curated_pool = [t for t in _LIMIT_CURATED_TEMPLATES if t["difficulty"] == difficulty]
    if curated_pool and rng.random() < 0.5:
        return _build_curated_limit(rng.choice(curated_pool), difficulty)

    techniques = _LIMIT_TECHNIQUES_BY_DIFFICULTY.get(difficulty, [])
    if not techniques:
        if not curated_pool:
            raise ValueError(f"no curated exercises or parameterizable techniques for difficulty {difficulty}")
        return _build_curated_limit(rng.choice(curated_pool), difficulty)

    technique = rng.choice(techniques)
    return generate_limit_for_technique(rng, technique, difficulty)