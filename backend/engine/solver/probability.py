"""Probability solvers: the 7 structures (laplace, hypergeometric, two_box,
two_bag_numbers, binomial, union, conditional) plus multi-part assembly."""
from sympy import N, Rational, binomial, latex, sympify

from .shared import _formula_tags, inline_latex


# ---------------------------------------------------------------------------
# Probability (topic = "probability", question_type = "probability")
#
# Khmer word problems: the story text comes from the scenario catalog
# (backend/data/scenarios/*.json); the math here is the only authority. Each
# `structure` maps to one solver branch and every branch validates its params
# (impossible problems raise ValueError — the generator's constraint sampler
# prevents them, the solver refuses them).
# ---------------------------------------------------------------------------

_PROB_STRUCTURES = (
    "laplace",
    "hypergeometric",
    "two_box",
    "two_bag_numbers",
    "binomial",
    "union",
    "conditional",
)

def _rational(value):
    """int or '1/2'-style string -> SymPy Rational."""
    return Rational(sympify(value))

def _p_solution(steps, checkpoints, p):
    return {
        "answer_exact": p,
        "answer_decimal": float(N(p, 8)),
        "answer_latex": latex(p),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
        "work_mode": "any_order",
    }

def _solve_probability(params):
    structure = params.get("structure")
    if structure not in _PROB_STRUCTURES:
        raise ValueError(f"unknown probability structure: {structure}")
    parts = params.get("parts")
    if isinstance(parts, list) and parts and all(
        isinstance(p, dict) and p.get("want") for p in parts
    ):
        return _solve_prob_multipart(params, structure, parts)
    return _solve_prob_single(params)

def _solve_prob_multipart(params, structure, parts):
    """Solve every sub-part of a multi-part exercise.

    Each part reuses the single-part branches (params env = shared slots +
    that part's overrides). The question's `answer_exact`/`steps`/... become the
    TARGET part's (the last one by default — the culminating sub-question), so
    create_question/grade keep working unchanged. The full solution is exposed
    via `parts` and the merged `checkpoints` (deduplicated shared totals), so
    explanations and line-checking cover the whole exercise."""
    part_solutions = []
    for part in parts:
        label = part.get("label") or "?"
        want = part.get("want")
        env = {k: v for k, v in part.items() if k not in ("label", "want", "km", "en")}
        single = _solve_prob_single({"structure": structure, "want": want, **env})
        single["checkpoints"] = [
            {**cp, "label": f"{label}: {cp['label']}"} for cp in single["checkpoints"]
        ]
        single["steps"] = [
            {**s, "title": f"Part {label}: {s['title']}"} for s in single["steps"]
        ]
        part_solutions.append({
            "label": label,
            "want": want,
            "answer_exact": single["answer_exact"],
            "answer_decimal": single["answer_decimal"],
            "answer_latex": single["answer_latex"],
            "steps": single["steps"],
            "checkpoints": single["checkpoints"],
            "formula_tags": single["formula_tags"],
        })

    merged_cps = []
    for i, sol in enumerate(part_solutions):
        cps = sol["checkpoints"]
        # The shared sample-space total (first checkpoint) repeats across parts:
        # keep it once, at the top.
        if i > 0 and cps and merged_cps and cps[0]["value"] == merged_cps[0]["value"]:
            cps = cps[1:]
        merged_cps.extend(cps)

    merged_steps = [s for sol in part_solutions for s in sol["steps"]]
    tags = list(dict.fromkeys(t for sol in part_solutions for t in sol["formula_tags"]))
    target = part_solutions[-1]
    return {
        "answer_exact": target["answer_exact"],
        "answer_decimal": target["answer_decimal"],
        "answer_latex": target["answer_latex"],
        "steps": merged_steps,
        "formula_tags": tags,
        "checkpoints": merged_cps,
        "parts": part_solutions,
        "target_label": target["label"],
        "work_mode": "any_order",
    }

def _solve_prob_single(params):
    structure = params.get("structure")
    if structure == "laplace":
        return _solve_prob_laplace(params)
    if structure == "hypergeometric":
        return _solve_prob_hypergeometric(params)
    if structure == "two_box":
        return _solve_prob_two_box(params)
    if structure == "two_bag_numbers":
        return _solve_prob_two_bag_numbers(params)
    if structure == "binomial":
        return _solve_prob_binomial(params)
    if structure == "union":
        return _solve_prob_union(params)
    return _solve_prob_conditional(params)

def _solve_prob_laplace(params):
    total = int(params["total"])
    favorable = int(params["favorable"])
    if not (0 < favorable < total):
        raise ValueError(f"impossible laplace params: favorable={favorable} total={total}")
    p = Rational(favorable, total)
    steps = [
        {
            "title": "Count the total outcomes",
            "detail": f"The sample space has \\(n(\\Omega) = {total}\\) equally likely outcomes.",
            "formula": "laplace_rule",
        },
        {
            "title": "Count the favorable outcomes",
            "detail": f"The event has \\(n(A) = {favorable}\\) favorable outcomes.",
            "formula": "laplace_rule",
        },
        {
            "title": "Apply Laplace's rule",
            "detail": f"\\(P(A) = \\dfrac{{n(A)}}{{n(\\Omega)}} = \\dfrac{{{favorable}}}{{{total}}}\\) = {inline_latex(p)}.",
            "formula": "laplace_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "n(Ω)", "value": total, "formula": "laplace_rule"},
            {"label": "n(A)", "value": favorable, "formula": "laplace_rule"},
            {"label": "P(A)", "value": p, "formula": "laplace_rule"},
        ],
        p,
    )

def _solve_prob_hypergeometric(params):
    w = int(params["w"])
    b = int(params["b"])
    k = int(params["k"])
    want = params.get("want")
    if w < 1 or b < 1 or not (1 <= k <= w + b):
        raise ValueError(f"impossible hypergeometric params: w={w} b={b} k={k}")
    n = w + b
    total = binomial(n, k)

    # Which category a part asks about. "wanted" defaults to w (the white/first
    # category); parts that ask about the second category pass "wanted": "b".
    wanted = params.get("wanted", "w")
    if wanted not in ("w", "b"):
        raise ValueError(f"unknown wanted slot: {wanted}")
    if wanted == "b":
        first, second = b, w
    else:
        first, second = w, b
    first_name = params.get("want_label") or "white"
    second_name = params.get("other_label") or "black"

    if want == "all_white":
        if k > first:
            raise ValueError("all_white: k > wanted count")
        favorable = binomial(first, k)
        title = "Count the favorable draws"
        detail = (
            f"Choosing {k} {first_name} balls from {first}: "
            f"\\(n(A) = C({first}, {k})\\) = {inline_latex(favorable)}."
        )
    elif want == "all_black":
        if k > second:
            raise ValueError("all_black: k > other count")
        favorable = binomial(second, k)
        title = "Count the favorable draws"
        detail = (
            f"Choosing {k} {second_name} balls from {second}: "
            f"\\(n(A) = C({second}, {k})\\) = {inline_latex(favorable)}."
        )
    elif want == "exactly_split":
        a = int(params["a"])
        if not (1 <= a <= k - 1 and a <= first and k - a <= second):
            raise ValueError(f"impossible exactly_split params: w={w} b={b} k={k} a={a}")
        favorable = binomial(first, a) * binomial(second, k - a)
        title = "Count the favorable draws"
        detail = (
            f"Choosing {a} {first_name} balls from {first} and {k - a} {second_name} "
            f"balls from {second}: \\(n(A) = C({first}, {a})\\,C({second}, {k - a})\\) "
            f"= {inline_latex(favorable)}."
        )
    elif want == "at_least_white":
        if not (1 <= k <= second):
            raise ValueError("at_least_white: complement would be trivial")
        no = binomial(second, k)
        p_no = Rational(no, total)
        p = 1 - p_no
        steps = [
            {
                "title": "Count the total draws",
                "detail": f"Drawing {k} balls from {n}: \\(n(\\Omega) = C({n}, {k})\\) = {inline_latex(total)}.",
                "formula": "hypergeometric_rule",
            },
            {
                "title": "Count the unfavorable draws",
                "detail": (
                    f"\"No {first_name} ball\" means all {k} are {second_name}: "
                    f"\\(C({second}, {k})\\) = {inline_latex(no)}. The probability of "
                    f"no {first_name} ball is \\(P(\\text{{no {first_name}}}) = "
                    f"\\dfrac{{{no}}}{{{total}}}\\) = {inline_latex(p_no)}."
                ),
                "formula": "combination_rule",
            },
            {
                "title": "Apply the complement rule",
                "detail": (
                    f"\\(P(\\text{{at least one {first_name}}}) = "
                    f"1 - P(\\text{{no {first_name}}})\\) = {inline_latex(1 - p_no)}."
                ),
                "formula": "complement_rule",
            },
        ]
        return _p_solution(
            steps,
            [
                {"label": "C(n,k) total", "value": total, "formula": "hypergeometric_rule"},
                {"label": f"C({second},{k}) no {first_name}", "value": no, "formula": "combination_rule"},
                {"label": f"P(no {first_name})", "value": p_no, "formula": "combination_rule"},
                {"label": f"P(at least one {first_name})", "value": p, "formula": "complement_rule"},
            ],
            p,
        )
    else:
        raise ValueError(f"unknown hypergeometric want: {want}")

    p = Rational(favorable, total)
    steps = [
        {
            "title": "Count the total draws",
            "detail": f"Drawing {k} balls from {n}: \\(n(\\Omega) = C({n}, {k})\\) = {inline_latex(total)}.",
            "formula": "hypergeometric_rule",
        },
        {
            "title": title,
            "detail": detail,
            "formula": "combination_rule" if want == "exactly_split" else "hypergeometric_rule",
        },
        {
            "title": "Apply the hypergeometric ratio",
            "detail": f"\\(P(A) = \\dfrac{{n(A)}}{{n(\\Omega)}} = \\dfrac{{{favorable}}}{{{total}}}\\) = {inline_latex(p)}.",
            "formula": "hypergeometric_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "C(n,k) total", "value": total, "formula": "hypergeometric_rule"},
            {"label": "n(A) favorable", "value": favorable, "formula": "combination_rule" if want == "exactly_split" else "hypergeometric_rule"},
            {"label": "P(A)", "value": p, "formula": "hypergeometric_rule"},
        ],
        p,
    )

def _solve_prob_two_box(params):
    w1 = int(params["w1"])
    b1 = int(params["b1"])
    w2 = int(params["w2"])
    b2 = int(params["b2"])
    want = params.get("want")
    if min(w1, b1, w2, b2) < 1:
        raise ValueError(f"impossible two_box params: {params}")
    n1, n2 = w1 + b1, w2 + b2
    p_w1, p_b1 = Rational(w1, n1), Rational(b1, n1)
    p_w2, p_b2 = Rational(w2, n2), Rational(b2, n2)

    if want == "both_white":
        p = p_w1 * p_w2
        steps = [
            {"title": "Probability from box 1", "detail": f"\\(P(\\text{{white from box 1}}) = \\dfrac{{{w1}}}{{{n1}}}\\) = {inline_latex(p_w1)}.", "formula": "laplace_rule"},
            {"title": "Probability from box 2", "detail": f"\\(P(\\text{{white from box 2}}) = \\dfrac{{{w2}}}{{{n2}}}\\) = {inline_latex(p_w2)}.", "formula": "laplace_rule"},
            {"title": "Multiply the independent draws", "detail": f"\\(P(\\text{{2 white}}) = \\dfrac{{{w1}}}{{{n1}}} \\times \\dfrac{{{w2}}}{{{n2}}}\\) = {inline_latex(p)}.", "formula": "product_rule"},
        ]
        checkpoints = [
            {"label": "P(white box 1)", "value": p_w1, "formula": "laplace_rule"},
            {"label": "P(white box 2)", "value": p_w2, "formula": "laplace_rule"},
            {"label": "P(A)", "value": p, "formula": "product_rule"},
        ]
    elif want == "both_black":
        p = p_b1 * p_b2
        steps = [
            {"title": "Probability from box 1", "detail": f"\\(P(\\text{{black from box 1}}) = \\dfrac{{{b1}}}{{{n1}}}\\) = {inline_latex(p_b1)}.", "formula": "laplace_rule"},
            {"title": "Probability from box 2", "detail": f"\\(P(\\text{{black from box 2}}) = \\dfrac{{{b2}}}{{{n2}}}\\) = {inline_latex(p_b2)}.", "formula": "laplace_rule"},
            {"title": "Multiply the independent draws", "detail": f"\\(P(\\text{{2 black}}) = \\dfrac{{{b1}}}{{{n1}}} \\times \\dfrac{{{b2}}}{{{n2}}}\\) = {inline_latex(p)}.", "formula": "product_rule"},
        ]
        checkpoints = [
            {"label": "P(black box 1)", "value": p_b1, "formula": "laplace_rule"},
            {"label": "P(black box 2)", "value": p_b2, "formula": "laplace_rule"},
            {"label": "P(A)", "value": p, "formula": "product_rule"},
        ]
    elif want == "cross":
        p = p_w1 * p_b2
        steps = [
            {"title": "Probability from box 1", "detail": f"\\(P(\\text{{white from box 1}}) = \\dfrac{{{w1}}}{{{n1}}}\\) = {inline_latex(p_w1)}.", "formula": "laplace_rule"},
            {"title": "Probability from box 2", "detail": f"\\(P(\\text{{black from box 2}}) = \\dfrac{{{b2}}}{{{n2}}}\\) = {inline_latex(p_b2)}.", "formula": "laplace_rule"},
            {"title": "Multiply the independent draws", "detail": f"\\(P(\\text{{white, black}}) = \\dfrac{{{w1}}}{{{n1}}} \\times \\dfrac{{{b2}}}{{{n2}}}\\) = {inline_latex(p)}.", "formula": "product_rule"},
        ]
        checkpoints = [
            {"label": "P(white box 1)", "value": p_w1, "formula": "laplace_rule"},
            {"label": "P(black box 2)", "value": p_b2, "formula": "laplace_rule"},
            {"label": "P(A)", "value": p, "formula": "product_rule"},
        ]
    elif want == "exactly_one_white":
        term1 = p_w1 * p_b2
        term2 = p_b1 * p_w2
        p = term1 + term2
        steps = [
            {"title": "White from box 1, black from box 2", "detail": f"\\(P(W_1) = \\dfrac{{{w1}}}{{{n1}}}\\), \\(P(B_2) = \\dfrac{{{b2}}}{{{n2}}}\\), so \\(P(W_1 \\cap B_2) = {inline_latex(term1)}\\).", "formula": "product_rule"},
            {"title": "Black from box 1, white from box 2", "detail": f"\\(P(B_1) = \\dfrac{{{b1}}}{{{n1}}}\\), \\(P(W_2) = \\dfrac{{{w2}}}{{{n2}}}\\), so \\(P(B_1 \\cap W_2) = {inline_latex(term2)}\\).", "formula": "product_rule"},
            {"title": "Add the two disjoint cases", "detail": f"\\(P(\\text{{exactly one white}}) = {inline_latex(term1)} + {inline_latex(term2)}\\) = {inline_latex(p)}.", "formula": "union_rule"},
        ]
        checkpoints = [
            {"label": "P(white box 1)", "value": p_w1, "formula": "laplace_rule"},
            {"label": "P(black box 2)", "value": p_b2, "formula": "laplace_rule"},
            {"label": "P(W1 ∩ B2)", "value": term1, "formula": "product_rule"},
            {"label": "P(B1 ∩ W2)", "value": term2, "formula": "product_rule"},
            {"label": "P(A)", "value": p, "formula": "union_rule"},
        ]
    else:
        raise ValueError(f"unknown two_box want: {want}")

    return _p_solution(steps, checkpoints, p)

def _solve_prob_two_bag_numbers(params):
    n = int(params["n"])
    k1 = int(params["k1"])
    k2 = int(params["k2"])
    want = params.get("want")
    if n < 3 or n % 2 == 0 or not (1 <= k1 <= n) or not (1 <= k2 <= n):
        raise ValueError(f"impossible two_bag_numbers params: {params}")
    o, e = (n + 1) // 2, (n - 1) // 2  # odd and even counts among 1..n
    total = binomial(n, k1) * binomial(n, k2)

    def favorable(count):
        return binomial(count, k1) * binomial(count, k2)

    if want == "at_least_one_odd":
        fav_even = favorable(e)
        p_all_even = Rational(fav_even, total)
        p = 1 - p_all_even
        steps = [
            {
                "title": "Count the total draws",
                "detail": f"Drawing {k1} balls from bag 1 and {k2} from bag 2: \\(n(S) = C({n}, {k1})\\,C({n}, {k2})\\) = {inline_latex(total)}.",
                "formula": "combination_rule",
            },
            {
                "title": "Count the all-even draws",
                "detail": f"Choosing only even numbers: \\(n(\\text{{all even}}) = C({e}, {k1})\\,C({e}, {k2})\\) = {inline_latex(fav_even)}.",
                "formula": "combination_rule",
            },
            {
                "title": "Probability that all drawn balls are even",
                "detail": f"\\(P(\\text{{all even}}) = \\dfrac{{{fav_even}}}{{{total}}}\\) = {inline_latex(p_all_even)}.",
                "formula": "product_rule",
            },
            {
                "title": "Apply the complement rule",
                "detail": f"\\(P(\\text{{at least one odd}}) = 1 - P(\\text{{all even}})\\) = {inline_latex(p)}.",
                "formula": "complement_rule",
            },
        ]
        return _p_solution(
            steps,
            [
                {"label": "n(S) total", "value": total, "formula": "combination_rule"},
                {"label": "n(all even)", "value": fav_even, "formula": "combination_rule"},
                {"label": "P(all even)", "value": p_all_even, "formula": "product_rule"},
                {"label": "P(at least one odd)", "value": p, "formula": "complement_rule"},
            ],
            p,
        )

    if want not in ("all_odd", "all_even"):
        raise ValueError(f"unknown two_bag_numbers want: {want}")
    count = o if want == "all_odd" else e
    name = "odd" if want == "all_odd" else "even"
    fav = favorable(count)
    p = Rational(fav, total)
    steps = [
        {
            "title": "Count the total draws",
            "detail": f"Drawing {k1} balls from bag 1 and {k2} from bag 2: \\(n(S) = C({n}, {k1})\\,C({n}, {k2})\\) = {inline_latex(total)}.",
            "formula": "combination_rule",
        },
        {
            "title": "Count the favorable draws",
            "detail": f"Choosing only {name} numbers: \\(n(A) = C({count}, {k1})\\,C({count}, {k2})\\) = {inline_latex(fav)}.",
            "formula": "combination_rule",
        },
        {
            "title": "Apply the ratio",
            "detail": f"\\(P(A) = \\dfrac{{n(A)}}{{n(S)}} = \\dfrac{{{fav}}}{{{total}}}\\) = {inline_latex(p)}.",
            "formula": "product_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "n(S) total", "value": total, "formula": "combination_rule"},
            {"label": "n(A) favorable", "value": fav, "formula": "combination_rule"},
            {"label": "P(A)", "value": p, "formula": "product_rule"},
        ],
        p,
    )

def _solve_prob_binomial(params):
    n = int(params["n"])
    k = int(params["k"])
    if not (1 <= k <= n):
        raise ValueError(f"impossible binomial params: n={n} k={k}")
    total = 2**n
    favorable = binomial(n, k)
    p = Rational(favorable, total)
    steps = [
        {
            "title": "Count the total outcomes",
            "detail": f"Each of the {n} flips has 2 outcomes: \\(n(\\Omega) = 2^{{{n}}}\\) = {total}.",
            "formula": "binomial_rule",
        },
        {
            "title": "Count the favorable outcomes",
            "detail": f"Choosing which {k} of the {n} flips are heads: \\(n(A) = C({n}, {k})\\) = {inline_latex(favorable)}.",
            "formula": "binomial_rule",
        },
        {
            "title": "Apply the binomial formula",
            "detail": f"\\(P(\\text{{exactly }} {k} \\text{{ heads}}) = \\dfrac{{C({n}, {k})}}{{2^{{{n}}}}}\\) = {inline_latex(p)}.",
            "formula": "binomial_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "n(Ω)", "value": total, "formula": "binomial_rule"},
            {"label": "n(A)", "value": favorable, "formula": "binomial_rule"},
            {"label": "P(A)", "value": p, "formula": "binomial_rule"},
        ],
        p,
    )

def _solve_prob_union(params):
    pa = _rational(params["pa"])
    pb = _rational(params["pb"])
    pab = _rational(params["pab"])
    if not (0 < pab <= pa and pab <= pb and pa + pb - pab <= 1):
        raise ValueError(f"impossible union params: {params}")
    p = pa + pb - pab
    steps = [
        {
            "title": "Sum the individual probabilities",
            "detail": f"\\(P(A) + P(B) = {inline_latex(pa)} + {inline_latex(pb)}\\) = {inline_latex(pa + pb)}.",
            "formula": "union_rule",
        },
        {
            "title": "Subtract the intersection",
            "detail": f"\\(P(A \\cup B) = P(A) + P(B) - P(A \\cap B)\\) = {inline_latex(pa + pb)} - {inline_latex(pab)} = {inline_latex(p)}.",
            "formula": "union_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "P(A)+P(B)", "value": pa + pb, "formula": "union_rule"},
            {"label": "P(A∪B)", "value": p, "formula": "union_rule"},
        ],
        p,
    )

def _solve_prob_conditional(params):
    pab = _rational(params["pab"])
    pb = _rational(params["pb"])
    if not (0 < pab <= pb):
        raise ValueError(f"impossible conditional params: {params}")
    p = pab / pb
    steps = [
        {
            "title": "Identify the given probabilities",
            "detail": f"\\(P(A \\cap B) = {inline_latex(pab)}\\) and \\(P(B) = {inline_latex(pb)}\\).",
            "formula": "conditional_rule",
        },
        {
            "title": "Apply the conditional formula",
            "detail": f"\\(P(A \\mid B) = \\dfrac{{P(A \\cap B)}}{{P(B)}} = \\dfrac{{{pab}}}{{{pb}}}\\) = {inline_latex(p)}.",
            "formula": "conditional_rule",
        },
    ]
    return _p_solution(
        steps,
        [
            {"label": "P(A∩B)", "value": pab, "formula": "conditional_rule"},
            {"label": "P(A|B)", "value": p, "formula": "conditional_rule"},
        ],
        p,
    )