"""Deterministic, step-by-step marking scheme for the 2018 exam — mirrors the
*style* the teacher's own worked solution is written in (each question is a
short sequence of asserted values: an intermediate quantity, then another,
then the final answer) rather than only checking a single final number.

The paper prints one total (125 points, matching the user-supplied
per-question split below) with no per-step breakdown, so the point weights
below are a documented, mechanically-derived choice, not a transcription:

  1. A question's points are split across its own graded "items" (its
     labeled sub-parts, e.g. I's A/B/C, or VII's k/kh_der/kh_mono/...)
     proportional to how many graded steps each item's own derivation has —
     an item with a 3-line derivation gets 3x the weight of a 1-line one.
  2. Within one item that has more than one step, the LAST step (the item's
     own final answer) gets 40% of that item's points; the remaining steps
     (the intermediate working) split the other 60% evenly. An item with
     only one step gets all of its points there.

This is independent of ``solver.py``'s ``checkpoints`` (which exist for the
frontend's live step-by-step overlay and are tuned per-topic for that use);
this module hand-lists the graded steps in the teacher's own order so the
rubric matches the paper's layout exactly, then computes points from that
list mechanically via the two rules above — never hand-typed per step.

Matching a student's answer to a step is intentionally ORDER-TOLERANT
within one item (mirrors this codebase's existing "any_order" convention for
probability/functions): every step is searched for anywhere in that item's
remaining, not-yet-used lines, not only the very next line. Real BAC II
grading does not penalize a correct fact written a line early or late — it
checks whether each required fact is present and correct.
"""
from fractions import Fraction

from sympy import (
    Rational, Symbol, binomial, cancel, diff, factor, integrate, limit, log,
    oo, simplify, solve as sym_solve, sqrt, sympify,
)

from ...core.grading import grade_part
from ...core.rubric import step_matches  # shared scalar/vector matcher — see engine/core/rubric.py

_X = Symbol("x")
_Y = Symbol("y")

# A step whose value is one of these sentinels is graded by calling
# grade_part(topic="past_exam", question_type, params, item_label, line)
# instead of step_matches — reuses the SAME deterministic judges already
# wired on that part in solver.py (kh_mono's "monotonicity" judge, kot2's
# "position" judge), rather than a second, parallel keyword scanner here.
_JUDGED = "judged"


# ---------------------------------------------------------------------------
# Per-question graded steps, in the teacher's own order. Every value is
# computed with SymPy here (never hand-typed), so the rubric can't silently
# drift from the actual mathematics.
# ---------------------------------------------------------------------------

def _steps_q1(params):
    w, r, b, k = params["white"], params["red"], params["blue"], params["draw"]
    n_s = binomial(w + r + b, k)
    n_a = binomial(r, k)
    n_b = binomial(b, 2) * binomial(w + r, 1) + binomial(b, 3)
    n_c = binomial(w, 1) * binomial(r, 1) * binomial(b, 1)
    return [
        {"label": "setup", "steps": [{"label": "n(S)", "value": n_s}]},
        {"label": "A", "steps": [
            {"label": "n(A)", "value": n_a}, {"label": "P(A)", "value": Rational(n_a, n_s)}]},
        {"label": "B", "steps": [
            {"label": "n(B)", "value": n_b}, {"label": "P(B)", "value": Rational(n_b, n_s)}]},
        {"label": "C", "steps": [
            {"label": "n(C)", "value": n_c}, {"label": "P(C)", "value": Rational(n_c, n_s)}]},
    ]


def _steps_q2(params):
    expr_a = sympify("(x**2*(x-2)+x**2+x-1)/(1-x)")
    num, den = expr_a.as_numer_denom()
    cancelled = simplify(cancel(factor(num) / factor(den)))
    final_a = limit(expr_a, _X, 1)

    expr_b = sympify("-2*x/sin(3*x)")
    final_b = limit(expr_b, _X, 0)

    expr_c = sympify("(sin(x)-sqrt(3)*cos(x))/(2*(pi-3*x))")
    final_c = limit(expr_c, _X, sympify("pi/3"))

    return [
        {"label": "a", "steps": [
            {"label": "cancelled form", "value": cancelled},
            {"label": "final value", "value": final_a}]},
        {"label": "b", "steps": [
            {"label": "standard sinc-limit fact (kx/sin kx -> 1)", "value": 1},
            {"label": "final value", "value": final_b}]},
        {"label": "c", "steps": [
            {"label": "standard sinc-limit fact (sin t/t -> 1)", "value": 1},
            {"label": "final value", "value": final_c}]},
    ]


def _steps_q3(params):
    locals_ = {"sqrt": sqrt}
    from sympy import I
    z1 = sympify(params["z1_re"], locals=locals_) + sympify(params["z1_im"], locals=locals_) * I
    z2 = sympify(params["z2_re"], locals=locals_) + sympify(params["z2_im"], locals=locals_) * I
    prod = simplify((z1 * z2).expand(complex=True))
    quot = simplify((z1 / z2).expand(complex=True))
    quot_sq = simplify((quot ** 2).expand(complex=True))
    quot_cube = simplify((quot ** 3).expand(complex=True))
    return [
        {"label": "a1", "steps": [{"label": "z1*z2", "value": prod}]},
        {"label": "a2", "steps": [{"label": "z1/z2", "value": quot}]},
        {"label": "b1", "steps": [{"label": "z1*z2 (trig form)", "value": prod}]},
        {"label": "b2", "steps": [{"label": "(z1/z2)^2 (trig form)", "value": quot_sq}]},
        {"label": "c1", "steps": [{"label": "(z1/z2)^3", "value": quot_cube}]},
    ]


def _steps_q4(params):
    x = _X
    exprs = [
        ("I", sympify("2-x+x**2"), sympify("1"), sympify("2")),
        ("J", sympify("cos(2*x)-cos(4*x)/2"), sympify("0"), sympify("pi/4")),
        ("K", sympify("3*x-2+1/(x-1)"), sympify("2"), sympify("3")),
    ]
    items = []
    for label, expr, lo, hi in exprs:
        antideriv = integrate(expr, x)
        result = integrate(expr, (x, lo, hi))
        items.append({"label": label, "steps": [
            {"label": "antiderivative", "value": antideriv},
            {"label": "final value", "value": simplify(result)},
        ]})
    return items


def _steps_q5(params):
    from sympy import Matrix
    a, b, c, d = (Matrix(params[k]) for k in ("A", "B", "C", "D"))
    n = Matrix(params["n"])
    ab, ac, ad, bc = b - a, c - a, d - a, c - b
    cross = ab.cross(ac)
    items = [
        {"label": "AB", "steps": [{"label": "AB", "value": list(ab)}]},
        {"label": "AC", "steps": [{"label": "AC", "value": list(ac)}]},
        {"label": "AD", "steps": [{"label": "AD", "value": list(ad)}]},
        {"label": "BC", "steps": [{"label": "BC", "value": list(bc)}]},
        {"label": "noncollinear", "steps": [{"label": "AB x AC", "value": list(cross)}]},
        {"label": "normal1", "steps": [{"label": "n.AB", "value": (n.T * ab)[0]}]},
        {"label": "normal2", "steps": [{"label": "n.AC", "value": (n.T * ac)[0]}]},
    ]

    expr = sympify(params.get("conic_expr", "(2*x+3*y)**2 - 12*(x*y+3)"), locals={"x": _X, "y": _Y})
    expr = expr.expand()
    a_coeff = expr.coeff(_X, 2)
    b_coeff = expr.coeff(_Y, 2)
    rhs = simplify(-(expr - a_coeff * _X ** 2 - b_coeff * _Y ** 2))
    a2, b2 = simplify(rhs / a_coeff), simplify(rhs / b_coeff)
    a_len, b_len = sqrt(max(a2, b2)), sqrt(min(a2, b2))
    items += [
        {"label": "a", "steps": [{"label": "a", "value": a_len}]},
        {"label": "b", "steps": [{"label": "b", "value": b_len}]},
        {"label": "v1", "steps": [{"label": "V1", "value": [-a_len, 0]}]},
        {"label": "v2", "steps": [{"label": "V2", "value": [a_len, 0]}]},
    ]
    return items


def _steps_q6(params):
    x = _X
    r = Symbol("r")
    b, c = params.get("b", 4), params.get("c", -5)
    roots = sorted(sym_solve(r ** 2 + b * r + c, r))
    from sympy import Function, exp
    y = Function("y")
    # General solution C1*e^(r0 x) + C2*e^(r1 x); IC pins C1, C2.
    C1, C2 = Symbol("C1"), Symbol("C2")
    general = C1 * exp(roots[0] * x) + C2 * exp(roots[1] * x)
    ics = params.get("ics", {"x0": 0, "y0": 3, "yp0": -3})
    eqs = [general.subs(x, ics["x0"]) - ics["y0"], general.diff(x).subs(x, ics["x0"]) - ics["yp0"]]
    sol = sym_solve(eqs, [C1, C2], dict=True)[0]
    particular = simplify(general.subs(sol))
    return [
        {"label": "ode", "steps": [
            # Two distinct roots, unordered — a student may label them r1/r2
            # in either order (matching is by value, never by this label).
            {"label": "characteristic root", "value": roots[0]},
            {"label": "characteristic root", "value": roots[1]},
            # Same for the two IC-solved arbitrary constants.
            {"label": "arbitrary constant", "value": sol[C1]},
            {"label": "arbitrary constant", "value": sol[C2]},
            {"label": "particular solution y(x)", "value": particular},
        ]},
    ]


def _steps_q7(params):
    x = _X
    f = sympify(params.get("expr", "-x+4+log((x+1)/(x-1))"), locals={"x": x})
    lo = sympify(params.get("domain_lo", "1"))
    lim_lo = limit(f, x, lo, dir="+")
    lim_inf = limit(f, x, oo)
    fp = simplify(diff(f, x))
    m = limit(f / x, x, oo)
    line1 = simplify(m * x + simplify(limit(f - m * x, x, oo)))
    slope = sympify(params.get("tangent_slope", "-5/3"))
    x0 = [r for r in sym_solve(fp - slope, x) if r.is_real and r > lo][0]
    y0 = simplify(f.subs(x, x0))
    line2 = simplify(slope * (x - x0) + y0)
    return [
        {"label": "k1", "steps": [{"label": "lim x->1+", "value": lim_lo}]},
        {"label": "k2", "steps": [{"label": "lim x->+oo", "value": lim_inf}]},
        {"label": "kh_der", "steps": [{"label": "f'(x)", "value": fp}]},
        {"label": "kh_mono", "steps": [{"label": "monotonicity verdict", "value": _JUDGED}]},
        {"label": "kot1", "steps": [{"label": "d1: y", "value": line1}]},
        {"label": "kot2", "steps": [{"label": "position verdict", "value": _JUDGED}]},
        {"label": "kh_tan", "steps": [
            {"label": "x0", "value": x0},
            {"label": "d2: y", "value": line2}]},
    ]


GRADED_STEPS = {
    "2018_1": _steps_q1, "2018_2": _steps_q2, "2018_3": _steps_q3,
    "2018_4": _steps_q4, "2018_5": _steps_q5, "2018_6": _steps_q6, "2018_7": _steps_q7,
}

QUESTION_POINTS = {
    "2018_1": 10, "2018_2": 15, "2018_3": 15, "2018_4": 15,
    "2018_5": 25, "2018_6": 10, "2018_7": 35,
}


# ---------------------------------------------------------------------------
# Rubric construction (mechanical — see module docstring) and marking.
# ---------------------------------------------------------------------------

def _split_final_intermediate(points, n):
    if n == 1:
        return [points]
    final = points * Fraction(2, 5)
    each = (points - final) / (n - 1)
    return [each] * (n - 1) + [final]


def build_rubric(exam_id, question_no, params):
    """[{"item", "label", "value", "points"}, ...] for one exam question,
    points computed mechanically from each item's own step count (never
    hand-typed) — see module docstring for the two-rule weighting."""
    key = f"{exam_id}_{question_no}"
    items = GRADED_STEPS[key](params)
    question_points = Fraction(QUESTION_POINTS[key])
    weights = [len(it["steps"]) for it in items]
    total_w = sum(weights)
    out = []
    for it, w in zip(items, weights):
        per_item = question_points * w / total_w
        pts = _split_final_intermediate(per_item, len(it["steps"]))
        for step, p in zip(it["steps"], pts):
            out.append({"item": it["label"], "label": step["label"], "value": step["value"], "points": p})
    return out


def mark_question(exam_id, question_no, params, lines):
    """Grade a student's full written work for one exam question against its
    rubric. `lines`: the student's raw work, one asserted fact per line (any
    order — see module docstring). Every rubric step is searched for among
    the lines not already claimed by an earlier step; unclaimed steps score
    zero without blocking credit for any step found later. Fully
    deterministic: every match is either a SymPy equality/tolerance check
    (`step_matches`) or that part's own existing `grade_part` judge
    (monotonicity/position verdicts) — never an LLM judgment call."""
    rubric = build_rubric(exam_id, question_no, params)
    work = [ln for ln in lines if ln.strip()]
    used = [False] * len(work)
    breakdown = []
    earned = Fraction(0)
    possible = Fraction(0)
    question_type = f"{exam_id}_q{question_no}"
    for step in rubric:
        possible += step["points"]
        matched_line = None
        for i, raw in enumerate(work):
            if used[i]:
                continue
            if step["value"] == _JUDGED:
                try:
                    ok = grade_part("past_exam", question_type, params, step["item"], raw).get("correct")
                except Exception:
                    ok = False
            else:
                ok = step_matches(raw, step["value"])
            if ok:
                matched_line = i
                break
        if matched_line is not None:
            used[matched_line] = True
            earned += step["points"]
        breakdown.append({
            "item": step["item"], "label": step["label"],
            "points_earned": step["points"] if matched_line is not None else Fraction(0),
            "points_possible": step["points"],
            "matched_line": work[matched_line].strip() if matched_line is not None else None,
        })
    return {"earned": earned, "possible": possible, "breakdown": breakdown}


def mark_full_exam(exam_id, params_by_question, lines_by_question):
    """Mark every question of one exam and total the score (out of the
    exam's printed total, e.g. 125 for 2018). `params_by_question`/
    `lines_by_question`: {question_no: params-dict / lines-list}, one entry
    per question the student attempted (a question with no entry scores 0
    of its own points, not an error)."""
    per_question = {}
    earned = Fraction(0)
    possible = Fraction(0)
    key_prefix = f"{exam_id}_"
    for key, q_points in QUESTION_POINTS.items():
        if not key.startswith(key_prefix):
            continue
        question_no = int(key[len(key_prefix):])
        params = params_by_question.get(question_no, {})
        lines = lines_by_question.get(question_no, [])
        result = mark_question(exam_id, question_no, params, lines) if lines else {
            "earned": Fraction(0), "possible": Fraction(q_points), "breakdown": [],
        }
        per_question[question_no] = result
        earned += result["earned"]
        possible += result["possible"]
    return {"earned": earned, "possible": possible, "per_question": per_question}
