"""Radical limit structures registry matching BAC II textbook exercises.

Contains 24 authentic radical limit structures (rad_01 through rad_24) with:
- semantic IDs
- authentic textbook labels ['rad_01'] to ['rad_24']
- deterministic SymPy closed-form samplers
- authentic Khmer titles (no fake code abbreviations)
"""
import random

def _sample_rad_sqrt_linear_num(rng):
    c = rng.choice([5, 7, 10])
    b = rng.choice([3, 4])
    a = b**2 - c
    return f"(sqrt(x + {c}) - {b})/(x - {a})", str(a), {"a": a, "b": b, "c": c}

def _sample_rad_quad_under_sqrt(rng):
    p, a, b = rng.choice([(2, 1, 2), (3, 2, 3), (4, 3, 4)])
    return f"(x - sqrt({a}*x + {b}))/(x - {p})", str(p), {"a": a, "b": b, "p": p}

def _sample_rad_sqrt_diff_linear_den(rng):
    p, a, b = rng.choice([(3, 1, 2), (7, 2, 3), (11, 5, 4)])
    return f"(sqrt(x + {a}) - {b})/({p} - x)", str(p), {"p": p, "a": a, "b": b}

def _sample_rad_sqrt_den_conjugate(rng):
    p = rng.choice([2, 3, 4])
    diff = p**2 - p
    return f"(x - {p})/(sqrt(x**2 - {diff}) - sqrt({p}))", str(p), {"p": p}

def _sample_rad_linear_over_sqrt_diff(rng):
    return "(2 - x)/(sqrt(x + 7) - 3)", "2", {"p": 2, "c": 7, "d": 3}

def _sample_rad_cubes_over_sqrt(rng):
    p, c, d = rng.choice([(2, 2, 2), (3, 6, 3), (1, 3, 2)])
    return f"(x**3 - {p**3})/(sqrt(x + {c}) - {d})", str(p), {"p": p, "c": c, "d": d}

def _sample_rad_sqrt_linear_shift(rng):
    return "(sqrt(2 + x) - 3)/(x - 7)", "7", {"p": 7, "c": 2, "b": 3}

def _sample_rad_diff_two_sqrts_zero(rng):
    k = rng.choice([2, 3, 4])
    return f"(sqrt(1 + x) - sqrt(1 - x))/({k}*x)", "0", {"k": k}

def _sample_rad_diff_two_sqrts_param(rng):
    a = rng.choice([2, 3, 4])
    return f"(sqrt({a}) - sqrt({a} - x))/({a}*x)", "0", {"a": a}

def _sample_rad_cubic_under_sqrt(rng):
    p, c, b = rng.choice([(2, 1, 3), (1, 8, 3), (2, 17, 5)])
    return f"(sqrt(x**3 + {c}) - {b})/(x - {p})", str(p), {"p": p, "c": c, "b": b}

def _sample_rad_double_conjugate_basic(rng):
    p, a, b, c, d = rng.choice([(2, 2, 2, 7, 3), (3, 1, 2, 6, 3), (5, 4, 3, 11, 4)])
    return f"(sqrt(x + {a}) - {b})/(sqrt(x + {c}) - {d})", str(p), {"p": p, "a": a, "b": b, "c": c, "d": d}

def _sample_rad_double_conjugate_quad(rng):
    p, a, b, c, d = rng.choice([(2, 3, 1, 2, 2), (3, 5, 2, 1, 2), (4, 7, 3, 5, 3)])
    return f"(sqrt(x**2 - {a}) - {b})/(sqrt(x + {c}) - {d})", str(p), {"p": p, "a": a, "b": b, "c": c, "d": d}

def _sample_rad_double_conjugate_two_sqrts(rng):
    a, k, c = rng.choice([(4, 3, 1), (1, 2, 4), (9, 4, 1)])
    d = int(c**0.5)
    return f"(sqrt(x + {a}) - sqrt({k}*x + {a}))/(sqrt(x + {c}) - {d})", "0", {"a": a, "k": k, "c": c, "d": d}

def _sample_rad_cbrt_quad_at_zero(rng):
    a, k = rng.choice([(1, 1), (2, 1), (1, 2)])
    a3 = a**3
    denom = f"({k}*x**2)" if k != 1 else "x**2"
    return f"(cbrt(x**2 + {a3}) - {a})/{denom}", "0", {"a": a, "k": k}

def _sample_rad_cbrt_linear_at_1(rng):
    a = rng.choice([1, 2, 3])
    return f"(cbrt(x) - {a})/(x - {a**3})", str(a**3), {"a": a}

def _sample_rad_cbrt_diff_two_roots(rng):
    a = rng.choice([1, 2])
    k = rng.choice([1, 2])
    denom = f"({k}*x)" if k != 1 else "x"
    return f"(cbrt(x + {a}) - cbrt({a} - x))/{denom}", "0", {"a": a, "k": k}

def _sample_rad_split_cbrt_sqrt(rng):
    a = rng.choice([1, 2])
    k = rng.choice([1, 2])
    a3 = a**3
    a2 = a**2
    denom = f"({k}*x)" if k != 1 else "x"
    return f"(cbrt(x + {a3}) - sqrt(x + {a2}))/{denom}", "0", {"a": a, "k": k}

def _sample_rad_split_sqrt_cbrt_1(rng):
    a, k, m = rng.choice([(1, 2, 1), (1, 3, 2), (1, 2, 2)])
    denom = f"({m}*x)" if m != 1 else "x"
    return f"(sqrt({a} + x) - cbrt({a**3} + {k}*x))/{denom}", "0", {"a": a, "k": k, "m": m}

def _sample_rad_split_two_sqrts_const(rng):
    p, a, b, c = rng.choice([(5, 4, 4, 2), (7, 9, 6, 3), (8, 8, 4, 2)])
    return f"(sqrt(x + {a}) - sqrt(x - {b}) - {c})/(x - {p})", str(p), {"p": p, "a": a, "b": b, "c": c}

def _sample_rad_split_fourth_sqrt(rng):
    p, a, b = rng.choice([(6, 10, 2), (7, 9, 3), (5, 11, 1)])
    return f"((x + {a})**(1/4) - sqrt(x - {b}))/(x - {p})", str(p), {"p": p, "a": a, "b": b}

def _sample_rad_nth_root_ratio(rng):
    n = rng.choice([3, 4, 5, 2017])
    m = rng.choice([2, 3, 2016])
    return f"(x**(1/{n}) - 1)/(x**(1/{m}) - 1)", "1", {"n": n, "m": m}


RADICAL_STRUCTURES = [
    {
        "id": "limit:radical:sqrt_single_num",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "sqrt",
        "title_km": "កន្សោមឆ្លាស់ឬសការេនៅភាគយក",
        "title_en": "Square root conjugate in numerator",
        "difficulty": "medium",
        "pattern": "(sqrt(x + {c}) - {b})/(x - {a})",
        "pattern_latex": r"\lim_{x \to a} \dfrac{\sqrt{x + c} - b}{x - a}",
        "point": "4",
        "var": "x",
        "sampler": _sample_rad_sqrt_linear_num,
        "source_labels": ["rad_01", "rad_07"],
    },
    {
        "id": "limit:radical:quad_under_sqrt",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "sqrt",
        "title_km": "កន្សោមឆ្លាស់ x - √(ax + b)",
        "title_en": "Conjugate rationalization (x - sqrt(ax + b))",
        "difficulty": "medium",
        "pattern": "(x - sqrt({a}*x + {b}))/(x - {p})",
        "pattern_latex": r"\lim_{x \to p} \dfrac{x - \sqrt{a x + b}}{x - p}",
        "point": "3",
        "var": "x",
        "sampler": _sample_rad_quad_under_sqrt,
        "source_labels": ["rad_02"],
    },
    {
        "id": "limit:radical:sqrt_diff_linear_den",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "sqrt",
        "title_km": "កន្សោមឆ្លាស់ឬសការេ (ភាគបែងប្តូរសញ្ញា)",
        "title_en": "Square root conjugate with reversed linear denominator",
        "difficulty": "medium",
        "pattern": "(sqrt(x + {a}) - {b})/({p} - x)",
        "pattern_latex": r"\lim_{x \to p} \dfrac{\sqrt{x + a} - b}{p - x}",
        "point": "3",
        "var": "x",
        "sampler": _sample_rad_sqrt_diff_linear_den,
        "source_labels": ["rad_03"],
    },
    {
        "id": "limit:radical:sqrt_single_den",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "sqrt",
        "title_km": "កន្សោមឆ្លាស់ឬសការេនៅភាគបែង",
        "title_en": "Square root conjugate in denominator",
        "difficulty": "medium",
        "pattern": "(x - {p})/(sqrt(x**2 - {p}) - sqrt({p}))",
        "pattern_latex": r"\lim_{x \to p} \dfrac{x - p}{\sqrt{x^{2} - p} - \sqrt{p}}",
        "point": "2",
        "var": "x",
        "sampler": _sample_rad_sqrt_den_conjugate,
        "source_labels": ["rad_04", "rad_05"],
    },
    {
        "id": "limit:radical:cubes_over_sqrt",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "sqrt",
        "title_km": "ផលដកគូបលើកន្សោមឬសការេ",
        "title_en": "Difference of cubes numerator over square root denominator",
        "difficulty": "hard",
        "pattern": "(x**3 - {p}**3)/(sqrt(x + {c}) - {d})",
        "pattern_latex": r"\lim_{x \to p} \dfrac{x^{3} - p^{3}}{\sqrt{x + c} - d}",
        "point": "2",
        "var": "x",
        "sampler": _sample_rad_cubes_over_sqrt,
        "source_labels": ["rad_06"],
    },
    {
        "id": "limit:radical:diff_two_sqrts_zero",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "sqrt",
        "title_km": "ផលដកឬសការេពីរត្រង់ 0",
        "title_en": "Difference of two square roots at 0",
        "difficulty": "medium",
        "pattern": "(sqrt(1 + x) - sqrt(1 - x))/({k}*x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\sqrt{1 + x} - \sqrt{1 - x}}{k x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_rad_diff_two_sqrts_zero,
        "source_labels": ["rad_08"],
    },
    {
        "id": "limit:radical:diff_two_sqrts_param",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "sqrt",
        "title_km": "ផលដកឬសការេពីរមានប៉ារ៉ាម៉ែត្រ",
        "title_en": "Parameterized difference of square roots at 0",
        "difficulty": "medium",
        "pattern": "(sqrt({a}) - sqrt({a} - x))/({a}*x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\sqrt{a} - \sqrt{a - x}}{a x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_rad_diff_two_sqrts_param,
        "source_labels": ["rad_09"],
    },
    {
        "id": "limit:radical:cubic_under_sqrt",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "sqrt",
        "title_km": "ពហុធាដឺក្រេទីបីក្នុងឬសការេ",
        "title_en": "Cubic polynomial under square root conjugate",
        "difficulty": "medium",
        "pattern": "(sqrt(x**3 + {c}) - {b})/(x - {p})",
        "pattern_latex": r"\lim_{x \to p} \dfrac{\sqrt{x^{3} + c} - b}{x - p}",
        "point": "2",
        "var": "x",
        "sampler": _sample_rad_cubic_under_sqrt,
        "source_labels": ["rad_11"],
    },
    {
        "id": "limit:radical:double_conjugate_basic",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "double_and_split",
        "title_km": "កន្សោមឆ្លាស់ពីរជាន់ (ភាគយកនិងភាគបែង)",
        "title_en": "Double square root conjugate",
        "difficulty": "hard",
        "pattern": "(sqrt(x + {a}) - {b})/(sqrt(x + {c}) - {d})",
        "pattern_latex": r"\lim_{x \to p} \dfrac{\sqrt{x + a} - b}{\sqrt{x + c} - d}",
        "point": "2",
        "var": "x",
        "sampler": _sample_rad_double_conjugate_basic,
        "source_labels": ["rad_12"],
    },
    {
        "id": "limit:radical:double_conjugate_quad",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "double_and_split",
        "title_km": "កន្សោមឆ្លាស់ពីរជាន់ (ភាគយកមានការេ)",
        "title_en": "Double conjugate with quadratic under radical",
        "difficulty": "hard",
        "pattern": "(sqrt(x**2 - {a}) - {b})/(sqrt(x + {c}) - {d})",
        "pattern_latex": r"\lim_{x \to p} \dfrac{\sqrt{x^{2} - a} - b}{\sqrt{x + c} - d}",
        "point": "2",
        "var": "x",
        "sampler": _sample_rad_double_conjugate_quad,
        "source_labels": ["rad_13"],
    },
    {
        "id": "limit:radical:double_conjugate_two_sqrts",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "double_and_split",
        "title_km": "កន្សោមឆ្លាស់ពីរជាន់ (ផលដកឬសពីរលើឬសមួយ)",
        "title_en": "Double conjugate (difference of two sqrts over sqrt)",
        "difficulty": "hard",
        "pattern": "(sqrt(x + {a}) - sqrt({k}*x + {a}))/(sqrt(x + {c}) - {d})",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\sqrt{x + a} - \sqrt{k x + a}}{\sqrt{x + c} - d}",
        "point": "0",
        "var": "x",
        "sampler": _sample_rad_double_conjugate_two_sqrts,
        "source_labels": ["rad_14"],
    },
    {
        "id": "limit:radical:cbrt_quad_at_zero",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "cbrt",
        "title_km": "កន្សោមឆ្លាស់ឬសគូប (∛(x² + a) - b)/x²",
        "title_en": "Cube root conjugate with quadratic at 0",
        "difficulty": "medium",
        "pattern": "(cbrt(x**2 + {a}**3) - {a})/({k}*x**2)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\sqrt[3]{x^{2} + a^{3}} - a}{k x^{2}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_rad_cbrt_quad_at_zero,
        "source_labels": ["rad_15"],
    },
    {
        "id": "limit:radical:cbrt_linear_at_1",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "cbrt",
        "title_km": "កន្សោមឆ្លាស់ឬសគូប (∛x - a)/(x - a³)",
        "title_en": "Standard cube root conjugate at a^3",
        "difficulty": "medium",
        "pattern": "(cbrt(x) - {a})/(x - {a}**3)",
        "pattern_latex": r"\lim_{x \to a^{3}} \dfrac{\sqrt[3]{x} - a}{x - a^{3}}",
        "point": "1",
        "var": "x",
        "sampler": _sample_rad_cbrt_linear_at_1,
        "source_labels": ["rad_16"],
    },
    {
        "id": "limit:radical:cbrt_diff_two_roots",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "cbrt",
        "title_km": "ផលដកឬសគូបពីរត្រង់ 0",
        "title_en": "Difference of two cube roots at 0",
        "difficulty": "medium",
        "pattern": "(cbrt(x + {a}) - cbrt({a} - x))/({k}*x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\sqrt[3]{x + a} - \sqrt[3]{a - x}}{k x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_rad_cbrt_diff_two_roots,
        "source_labels": ["rad_18"],
    },
    {
        "id": "limit:radical:split_cbrt_sqrt",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "double_and_split",
        "title_km": "វិធីថែមថយបំបែកលីមីត (ឬសគូប និងឬសការេ)",
        "title_en": "Mixed radical split trick (cbrt and sqrt at 0)",
        "difficulty": "hard",
        "pattern": "(cbrt(x + {a}**3) - sqrt(x + {a}**2))/({k}*x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\sqrt[3]{x + a^{3}} - \sqrt{x + a^{2}}}{k x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_rad_split_cbrt_sqrt,
        "source_labels": ["rad_19"],
    },
    {
        "id": "limit:radical:split_sqrt_cbrt_1",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "double_and_split",
        "title_km": "វិធីថែមថយបំបែកលីមីត (√(a+x) - ∛(a³+kx))",
        "title_en": "Mixed radical split trick (sqrt and cbrt)",
        "difficulty": "hard",
        "pattern": "(sqrt({a} + x) - cbrt({a}**3 + {k}*x))/({m}*x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\sqrt{a + x} - \sqrt[3]{a^{3} + k x}}{m x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_rad_split_sqrt_cbrt_1,
        "source_labels": ["rad_20"],
    },
    {
        "id": "limit:radical:split_two_sqrts_const",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "double_and_split",
        "title_km": "វិធីថែមថយបំបែកលីមីត (ឬសការេពីរមានចំនួនថេរ)",
        "title_en": "Grouping split trick with two square roots and constant",
        "difficulty": "hard",
        "pattern": "(sqrt(x + {a}) - sqrt(x - {b}) - {c})/(x - {p})",
        "pattern_latex": r"\lim_{x \to p} \dfrac{\sqrt{x + a} - \sqrt{x - b} - c}{x - p}",
        "point": "5",
        "var": "x",
        "sampler": _sample_rad_split_two_sqrts_const,
        "source_labels": ["rad_21"],
    },
    {
        "id": "limit:radical:split_fourth_sqrt",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "double_and_split",
        "title_km": "វិធីថែមថយបំបែកលីមីត (ឬសទីបួន និងឬសការេ)",
        "title_en": "Mixed radical split trick (4th root and square root)",
        "difficulty": "hard",
        "pattern": "((x + {a})**(1/4) - sqrt(x - {b}))/(x - {p})",
        "pattern_latex": r"\lim_{x \to p} \dfrac{\sqrt[4]{x + a} - \sqrt{x - b}}{x - p}",
        "point": "6",
        "var": "x",
        "sampler": _sample_rad_split_fourth_sqrt,
        "source_labels": ["rad_22"],
    },
    {
        "id": "limit:radical:nth_root_ratio",
        "question_type": "limit",
        "category": "radical",
        "subfamily": "cbrt",
        "title_km": "ផលធៀបឬសទី n តាមដេរីវេ (ⁿ√x - 1)/(ᵐ√x - 1)",
        "title_en": "Ratio of n-th and m-th roots at 1",
        "difficulty": "hard",
        "pattern": "(x**(1/{n}) - 1)/(x**(1/{m}) - 1)",
        "pattern_latex": r"\lim_{x \to 1} \dfrac{\sqrt[n]{x} - 1}{\sqrt[m]{x} - 1}",
        "point": "1",
        "var": "x",
        "sampler": _sample_rad_nth_root_ratio,
        "source_labels": ["rad_23", "rad_24"],
    },
]
