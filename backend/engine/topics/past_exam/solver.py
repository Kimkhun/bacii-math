"""Solvers for the past-exam question shapes no existing topic covers (see
``__init__.py`` for why these four and not the whole exam). SymPy computes
every answer; the curated JSON only supplies this exercise's fixed numbers."""
from sympy import (
    I, Matrix, N, Rational, Symbol, binomial, diff, expand, latex, limit,
    simplify, solve as sym_solve, sqrt, sympify,
)

from ...core.shared import _formula_tags

_X, _Y = Symbol("x"), Symbol("y")


def _step(title, detail, formula):
    return {"title": title, "detail": detail, "formula": formula}


def _safe_float(value):
    try:
        return float(N(value, 8))
    except (TypeError, ValueError):
        return None


def _assemble(parts, work_mode="any_order"):
    merged_cps = [cp for p in parts for cp in p["checkpoints"]]
    merged_steps = [s for p in parts for s in p["steps"]]
    tags = list(dict.fromkeys(t for p in parts for t in p["formula_tags"]))
    target = parts[-1]
    return {
        "answer_exact": target["answer_exact"],
        "answer_decimal": target["answer_decimal"],
        "answer_latex": target["answer_latex"],
        "answer_display": target.get("answer_display"),
        "steps": merged_steps,
        "formula_tags": tags,
        "checkpoints": merged_cps,
        "parts": parts,
        "target_label": target["label"],
        "work_mode": work_mode,
        "given": None,
    }


# ---------------------------------------------------------------------------
# Q1 — three-color hypergeometric counting/probability
# ---------------------------------------------------------------------------

def _scalar_part(label, title, value, formula, extra_steps=()):
    p_latex = latex(value)
    return {
        "label": label,
        "answer_kind": None,
        "answer_exact": value,
        "answer_decimal": _safe_float(value),
        "answer_latex": p_latex,
        "answer_display": str(value),
        "steps": [*extra_steps, _step(f"Part {label}", f"{title} = {p_latex}.", formula)],
        "checkpoints": [{"label": label, "value": value, "formula": formula}],
        "formula_tags": _formula_tags([*extra_steps, {"formula": formula}]),
    }


def _solve_q1(params):
    w, r, b, k = params["white"], params["red"], params["blue"], params["draw"]
    n = w + r + b
    n_s = binomial(n, k)
    setup = _step("Total ways to draw", f"n(S) = C({n},{k}) = {n_s}.", "hypergeometric_rule")

    n_a = binomial(r, k)
    p_a = Rational(n_a, n_s)
    part_a = _scalar_part(
        "A", "P(A)", p_a, "hypergeometric_rule",
        [setup, _step("Part A: favorable outcomes",
                       f"All {k} balls are red: n(A) = C({r},{k}) = {n_a}.", "hypergeometric_rule")],
    )

    n_other = w + r
    n_b = binomial(b, 2) * binomial(n_other, 1) + binomial(b, 3)
    p_b = Rational(n_b, n_s)
    part_b = _scalar_part(
        "B", "P(B)", p_b, "hypergeometric_rule",
        [_step("Part B: favorable outcomes",
               f"At least 2 blue: n(B) = C({b},2)\\times C({n_other},1) + C({b},3) "
               f"= {binomial(b, 2) * binomial(n_other, 1)} + {binomial(b, 3)} = {n_b}.",
               "hypergeometric_rule")],
    )

    n_c = binomial(w, 1) * binomial(r, 1) * binomial(b, 1)
    p_c = Rational(n_c, n_s)
    part_c = _scalar_part(
        "C", "P(C)", p_c, "hypergeometric_rule",
        [_step("Part C: favorable outcomes",
               f"One ball of each color: n(C) = C({w},1)\\times C({r},1)\\times C({b},1) = {n_c}.",
               "hypergeometric_rule")],
    )

    return _assemble([part_a, part_b, part_c])


# ---------------------------------------------------------------------------
# Q3 — complex arithmetic/trig-form with irrational coefficients
# ---------------------------------------------------------------------------

def _complex_part(label, title, value, formula="complex_multiplication"):
    return {
        "label": label,
        "answer_kind": None,
        "answer_exact": value,
        "answer_decimal": str(value),
        "answer_latex": latex(value),
        "answer_display": str(value),
        "steps": [_step(f"Part {label}", f"{title} = {latex(value)}.", formula)],
        "checkpoints": [{"label": label, "value": value, "formula": formula}],
        "formula_tags": [formula],
    }


def _solve_q3(params):
    locals_ = {"sqrt": sqrt, "I": I}
    z1 = sympify(params["z1_re"], locals=locals_) + sympify(params["z1_im"], locals=locals_) * I
    z2 = sympify(params["z2_re"], locals=locals_) + sympify(params["z2_im"], locals=locals_) * I

    prod = simplify(expand(z1 * z2, complex=True))
    quot = simplify(expand(z1 / z2, complex=True))
    quot_sq = simplify(expand(quot ** 2, complex=True))
    quot_cube = simplify(expand(quot ** 3, complex=True))

    parts = [
        _complex_part("a1", r"z_1 \times z_2", prod, "complex_multiplication"),
        _complex_part("a2", r"z_1/z_2", quot, "complex_division"),
        _complex_part("b1", r"z_1 \times z_2\ (\text{trig form})", prod, "complex_multiplication"),
        _complex_part("b2", r"(z_1/z_2)^2\ (\text{trig form})", quot_sq, "de_moivre"),
        _complex_part("c1", r"(z_1/z_2)^3", quot_cube, "de_moivre"),
    ]
    return _assemble(parts)


# ---------------------------------------------------------------------------
# Q5a — 3D vectors: components + non-collinearity + normal-vector check
# ---------------------------------------------------------------------------

def _vec_part(label, title, vec, formula="vector_ops"):
    vals = list(vec)
    display = "(" + ", ".join(str(v) for v in vals) + ")"
    return {
        "label": label,
        "answer_kind": "vector",
        "answer_exact": vals,
        "answer_decimal": None,
        "answer_latex": display,
        "answer_display": display,
        "steps": [_step(f"Part {label}", f"{title} = {display}.", formula)],
        # Vector-valued checkpoints aren't SymPy scalars, so analyze_work's
        # line-by-line matcher skips them rather than flagging them wrong —
        # this is informational only; grade_part is the authoritative check.
        "checkpoints": [{"label": label, "value": display, "formula": formula}],
        "formula_tags": [formula],
    }


def _solve_q5_vectors(params):
    a, b, c, d = (Matrix(params[k]) for k in ("A", "B", "C", "D"))
    n = Matrix(params["n"])

    ab, ac, ad, bc = b - a, c - a, d - a, c - b
    cross = ab.cross(ac)
    dot_ab = (n.T * ab)[0]
    dot_ac = (n.T * ac)[0]

    parts = [
        _vec_part("AB", r"\overrightarrow{AB}", ab),
        _vec_part("AC", r"\overrightarrow{AC}", ac),
        _vec_part("AD", r"\overrightarrow{AD}", ad),
        _vec_part("BC", r"\overrightarrow{BC}", bc),
        _vec_part("cross", r"\overrightarrow{AB}\times\overrightarrow{AC}", cross, "cross_product"),
        _scalar_part("n_dot_AB", r"\vec n \cdot \overrightarrow{AB}", dot_ab, "dot_product"),
        _scalar_part("n_dot_AC", r"\vec n \cdot \overrightarrow{AC}", dot_ac, "dot_product"),
    ]
    return _assemble(parts)


# ---------------------------------------------------------------------------
# Q5b — conic reduced to standard form (centered ellipse, no cross/linear
# terms once expanded — this exercise's own shape, not a general classifier;
# the ``conics`` topic already owns the general parabola/ellipse/hyperbola
# classifier for its own curated exercises)
# ---------------------------------------------------------------------------

def _solve_q5_conic(params):
    expr = expand(sympify(params["expr"], locals={"x": _X, "y": _Y}))
    a_coeff = expr.coeff(_X, 2)
    b_coeff = expr.coeff(_Y, 2)
    const = simplify(expr - a_coeff * _X ** 2 - b_coeff * _Y ** 2)
    rhs = simplify(-const)
    a2 = simplify(rhs / a_coeff)
    b2 = simplify(rhs / b_coeff)

    major_is_x = a2 >= b2
    a_len = sqrt(a2) if major_is_x else sqrt(b2)
    b_len = sqrt(b2) if major_is_x else sqrt(a2)
    v1 = (-a_len, 0) if major_is_x else (0, -a_len)
    v2 = (a_len, 0) if major_is_x else (0, a_len)

    setup = _step(
        "Reduce to standard form",
        f"\\({latex(expr)} = 0\\) expands to \\({latex(a_coeff)}x^2 + {latex(b_coeff)}y^2 = {latex(rhs)}\\), "
        f"i.e. \\(\\frac{{x^2}}{{{latex(a2)}}} + \\frac{{y^2}}{{{latex(b2)}}} = 1\\) — an ellipse centered at the origin.",
        "conic_classification",
    )

    parts = [
        _scalar_part("a", "a", a_len, "conic_classification", [setup]),
        _scalar_part("b", "b", b_len, "conic_classification"),
        _vec_part("v1", "V_1", v1, "conic_classification"),
        _vec_part("v2", "V_2", v2, "conic_classification"),
    ]
    return _assemble(parts)


# ---------------------------------------------------------------------------
# Q7 — full function study on a restricted domain the exam states as given
# (f(x) = -x+4+ln((x+1)/(x-1)), restricted to x>1) rather than derived from
# the expression alone (its natural domain is (-oo,-1) U (1,oo); the exam
# only studies the (1,oo) branch). The existing ``functions`` topic's
# domain/monotonicity machinery assumes the whole function_expr is either a
# bare log or a bare rational (it takes `expr.as_numer_denom()` on the
# WHOLE expression otherwise), so a polynomial-plus-log expr like this one
# comes out with the wrong (un-split, unrestricted) domain — hence a
# bespoke solve here rather than reusing that topic for this question.
# ---------------------------------------------------------------------------

def _infinity_part(label, title, value, formula="vertical_asymptote"):
    return {
        "label": label,
        "answer_kind": "infinity",
        "answer_exact": value,
        "answer_decimal": None,
        "answer_latex": latex(value),
        "answer_display": ("+\\infty" if value > 0 else "-\\infty"),
        "steps": [_step(f"Part {label}", f"{title} = {latex(value)}.", formula)],
        "checkpoints": [{"label": label, "value": value, "formula": formula}],
        "formula_tags": [formula],
    }


def _expr_part(label, title, value, formula, extra_steps=()):
    return {
        "label": label,
        "answer_kind": None,
        "answer_exact": value,
        "answer_decimal": _safe_float(value),
        "answer_latex": latex(value),
        "answer_display": str(value),
        "steps": [*extra_steps, _step(f"Part {label}", f"{title} = {latex(value)}.", formula)],
        "checkpoints": [{"label": label, "value": value, "formula": formula}],
        "formula_tags": _formula_tags([*extra_steps, {"formula": formula}]),
    }


def _solve_q7(params):
    x = Symbol("x")
    f = sympify(params["expr"], locals={"x": x})
    lo = sympify(params.get("domain_lo", "1"), locals={"x": x})

    lim_lo = limit(f, x, lo, dir="+")
    lim_inf = limit(f, x, sympify("oo"))
    part_k1 = _infinity_part("k1", f"\\lim_{{x\\to {latex(lo)}^+}} f(x)", lim_lo)
    part_k2 = _infinity_part("k2", "\\lim_{x\\to +\\infty} f(x)", lim_inf)

    fp = simplify(diff(f, x))
    part_der = _expr_part("kh_der", "f'(x)", fp, "quotient_rule")

    part_mono = {
        "label": "kh_mono",
        "answer_kind": "monotonicity",
        "answer_exact": [{"interval": f"({latex(lo)}, oo)", "direction": "dec"}],
        "answer_decimal": None,
        "answer_latex": None,
        "answer_display": f"decreasing on ({latex(lo)}, +\\infty)",
        "steps": [_step("Part kh_mono", f"f'(x) < 0 on ({latex(lo)}, +\\infty), so f is strictly decreasing there.",
                          "monotonicity_sign")],
        "checkpoints": [],
        "formula_tags": ["monotonicity_sign"],
    }

    m = limit(f / x, x, sympify("oo"))
    b = simplify(limit(f - m * x, x, sympify("oo")))
    line1 = simplify(m * x + b)
    part_asym = _expr_part("kot1", "d_1: y", line1, "oblique_asymptote")

    diff_line = simplify(f - line1)
    part_pos = {
        "label": "kot2",
        "answer_kind": "position",
        "answer_exact": "above",
        "answer_decimal": None,
        "answer_latex": None,
        "answer_display": "C is above d1 on the whole domain",
        "steps": [_step("Part kot2", f"f(x) - d_1(x) = {latex(diff_line)} > 0 for x > {latex(lo)}, so C lies above d1.",
                          "position_asymptote")],
        "checkpoints": [],
        "formula_tags": ["position_asymptote"],
    }

    slope = sympify(params.get("tangent_slope", "-5/3"))
    x0_candidates = [r for r in sym_solve(fp - slope, x) if r.is_real and r > lo]
    x0 = x0_candidates[0] if x0_candidates else None
    y0 = simplify(f.subs(x, x0))
    line2 = simplify(slope * (x - x0) + y0)
    part_tan = _expr_part(
        "kh_tan", "d_2: y", line2, "tangent_equation",
        [_step("Part kh_tan: solve for the point",
               f"f'(x_0) = {latex(slope)} \\Rightarrow x_0 = {latex(x0)},\\ y_0 = {latex(y0)}.",
               "tangent_equation")],
    )
    part_tan["checkpoints"].insert(0, {"label": "kh_tan: x0", "value": x0, "formula": "tangent_equation"})

    part_draw = {
        "label": "ng", "answer_kind": None, "answer_exact": "graph", "answer_decimal": None,
        "answer_latex": "\\text{graph}", "answer_display": "sketch C with d1 and d2",
        "steps": [_step("Part ng", "Sketch C together with the asymptote d1 and the tangent d2.", "graph_drawing")],
        "checkpoints": [{"label": "ng", "value": "graph", "formula": "graph_drawing"}],
        "formula_tags": ["graph_drawing"],
    }

    return _assemble([part_k1, part_k2, part_der, part_mono, part_asym, part_pos, part_tan, part_draw])


def _solve_past_exam(question_type, params):
    if question_type == "2018_q1":
        return _solve_q1(params)
    if question_type == "2018_q3":
        return _solve_q3(params)
    if question_type == "2018_q5_vectors":
        return _solve_q5_vectors(params)
    if question_type == "2018_q5_conic":
        return _solve_q5_conic(params)
    if question_type == "2018_q7":
        return _solve_q7(params)
    raise ValueError(f"unknown question_type: {question_type}")
