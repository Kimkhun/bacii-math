"""Limit generation: 50% curated real BAC II exercises / 50% procedural."""
from sympy import latex, oo

from engine.notation import pretty_expr, pretty_point
from engine.structures import _LIMIT_CURATED_TEMPLATES

from .shared import _build_expr_problem, _expr_latex, _fmt_poly


_LIMIT_VARIANT_BY_DIFFICULTY = {
    "easy": "polynomial",
    "medium": "removable",
    "hard": "infinity_rational",
}

def _build_curated_limit(item, difficulty):
    """A real BAC II limit exercise from backend/data/limits/{formula_name}.json,
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

def _generate_limit(rng, difficulty):
    curated_pool = [t for t in _LIMIT_CURATED_TEMPLATES if t["difficulty"] == difficulty]
    if curated_pool and rng.random() < 0.5:
        return _build_curated_limit(rng.choice(curated_pool), difficulty)

    variant = _LIMIT_VARIANT_BY_DIFFICULTY[difficulty]

    if variant == "polynomial":
        p = rng.randint(1, 3)
        q = rng.randint(-5, 5)
        r = rng.randint(-5, 5)
        c = rng.randint(-3, 3)
        expr = _fmt_poly(p, q, r)
        point_latex = str(c)
    elif variant == "removable":
        c = rng.choice([v for v in range(-5, 6) if v != 0])
        expr = f"(x**2 - {c * c})/(x - {c})"
        point_latex = str(c)
    else:  # infinity_rational
        p = rng.randint(1, 5)
        q = rng.randint(-9, 9)
        r = rng.randint(1, 5)
        s = rng.randint(-9, 9)
        num = _fmt_poly(p, q, 0)
        den = _fmt_poly(r, 0, s)
        expr = f"({num})/({den})"
        point_latex = r"+\infty"

    point = "oo" if variant == "infinity_rational" else str(c)
    params = {"expr": expr, "var": "x", "point": point}
    point_display = "+∞" if variant == "infinity_rational" else str(c)
    prompt = f"Find lim(x → {point_display}) of {pretty_expr(expr)}."
    expr_latex = _expr_latex(expr)
    prompt_latex = rf"\text{{Find }} \lim_{{x \to {point_latex}}} {expr_latex}"
    display = f"lim_{{x \\to {point_display}}} {expr}"

    return _build_expr_problem("limit", "limit", params, difficulty, prompt, prompt_latex, display)