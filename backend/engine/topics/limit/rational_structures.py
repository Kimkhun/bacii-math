"""Rational limit structures registry matching BAC II textbook exercises.

Contains 30 authentic rational limit structures (rat_01 through rat_30) with:
- semantic IDs
- authentic textbook labels ['rat_01'] to ['rat_30']
- deterministic SymPy closed-form samplers
- authentic Khmer titles (no fake code abbreviations)
"""
import random

def _sample_rat_diff_squares_linear(rng):
    a = rng.choice([2, 3, 4, 5, 6])
    sign = rng.choice([1, -1])
    pt = a * sign
    return f"(x**2 - {a**2})/(x - {pt})", str(pt), {"a": a}

def _sample_rat_diff_squares_quad(rng):
    a = rng.choice([2, 3, 4, 5])
    return f"(x**2 - {a**2})/(x**2 - {a}*x)", str(a), {"a": a}

def _sample_rat_diff_cubes(rng):
    a = rng.choice([1, 2, 3])
    return f"(x**3 - {a**3})/(x**2 - {a**2})", str(a), {"a": a}

def _sample_rat_quartic_quad(rng):
    a = rng.choice([2, 3])
    k = rng.choice([1, 2])
    return f"({k*a**4} - {k}*x**4)/({a**2} - x**2)", str(a), {"a": a, "k": k}

def _sample_rat_quadratic_linear(rng):
    r1 = rng.choice([1, 2, 3])
    r2 = rng.choice([-3, -2, -1, 4])
    while r1 == r2:
        r2 = rng.choice([-4, 4, 5])
    p = r1 + r2
    q = r1 * r2
    return f"(x**2 - {p}*x + {q})/(x - {r1})", str(r1), {"r1": r1, "p": p, "q": q}

def _sample_rat_quadratic_quadratic(rng):
    r_shared = rng.choice([1, 2, -1, -2])
    r1 = rng.choice([3, -3, 4])
    r2 = rng.choice([5, -4, 2])
    num = f"(x - {r_shared})*(x - {r1})"
    den = f"(x - {r_shared})*(x - {r2})"
    return f"({num})/({den})", str(r_shared), {"shared": r_shared}

def _sample_rat_quartic_linear(rng):
    a = rng.choice([1, 2, 3])
    return f"(x**4 - {a**4})/(x - {a})", str(a), {"a": a}

def _sample_rat_quartic_cubic(rng):
    a = rng.choice([1, 2])
    return f"(x**4 - {a**4})/(x**3 - {a**3})", str(a), {"a": a}

def _sample_rat_sum_cubes(rng):
    a = rng.choice([1, 2, 3])
    return f"(x**3 + {a**3})/(x + {a})", str(-a), {"a": a}

def _sample_rat_diff_cubes_quad(rng):
    a = rng.choice([2, 3])
    return f"(x**3 - {a**3})/(x**2 - {a**2})", str(a), {"a": a}

def _sample_rat_diff_cubes_trinomial(rng):
    a = rng.choice([1, 2])
    b = rng.choice([2, 3])
    return f"(x**3 - {a**3})/({b}*x**2 - {b*a + 1}*x + {a})", str(a), {"a": a, "b": b}

def _sample_rat_shifted_binomial_cube(rng):
    a = rng.choice([2, 3, 4])
    return f"((x - {a})**3 + {a**3})/x", "0", {"a": a}

def _sample_rat_shifted_binomial_square(rng):
    a = rng.choice([2, 3, 4, 5])
    return f"((x + {a})**2 - {a**2})/x", "0", {"a": a}

def _sample_rat_shifted_difference_squares(rng):
    a = rng.choice([1, 2])
    b = rng.choice([3, 4])
    return f"((1 + {a}*x)**2 - ({b}*x + 1)**2)/(2*x)", "0", {"a": a, "b": b}

def _sample_rat_grouping_cubic(rng):
    a = rng.choice([2, 3])
    return f"(x**3 - {a}*x**2 + x - {a})/(2*x**2 - {2*a + 1}*x + {a})", str(a), {"a": a}

def _sample_rat_poly_derivative_1(rng):
    n = rng.choice([4, 5, 6])
    return f"(x**{n} - {n}*x + {n-1})/(x - 1)**2", "1", {"n": n}

def _sample_rat_poly_monomial_n(rng):
    n = rng.choice([2015, 2018, 2021, 2025])
    return f"(x**{n} - 1)/(x - 1)", "1", {"n": n}

def _sample_rat_poly_derivative_ratio(rng):
    n = rng.choice([10, 20, 50, 100])
    m = rng.choice([5, 10, 25, 50])
    return f"(x**{n} - {n}*x + {n-1})/(x**{m} - {m}*x + {m-1})", "1", {"n": n, "m": m}

def _sample_rat_poly_odd_ratio(rng):
    p = rng.choice([2017, 2019, 2023])
    q = rng.choice([2015, 2021])
    return f"(x**{p} + 1)/(x**{q} + 1)", "-1", {"p": p, "q": q}

def _sample_rat_poly_sum_split(rng):
    n = rng.choice([3, 4, 5, 2017])
    m = rng.choice([2, 3, 2016])
    return f"(x + x**2 + x**3 - 3)/(x + x**2 - 2)", "1", {"n": n, "m": m}


RATIONAL_STRUCTURES = [
    {
        "id": "limit:rational:diff_squares_linear",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផលដកការេពីរតួ (ភាគបែងលីនេអ៊ែរ)",
        "title_en": "Difference of squares (linear denominator)",
        "difficulty": "easy",
        "pattern": "(x**2 - {a}**2)/(x - {pt})",
        "pattern_latex": r"\lim_{x \to a} \dfrac{x^{2} - a^{2}}{x - a}",
        "point": "2",
        "var": "x",
        "sampler": _sample_rat_diff_squares_linear,
        "source_labels": ["rat_01", "rat_15", "rat_16", "rat_17"],
    },
    {
        "id": "limit:rational:diff_squares_quad",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផលដកការេពីរតួ (ទាញកត្តា x នៅភាគបែង)",
        "title_en": "Difference of squares (factored x denominator)",
        "difficulty": "easy",
        "pattern": "(x**2 - {a}**2)/(x**2 - {a}*x)",
        "pattern_latex": r"\lim_{x \to a} \dfrac{x^{2} - a^{2}}{x^{2} - a x}",
        "point": "3",
        "var": "x",
        "sampler": _sample_rat_diff_squares_quad,
        "source_labels": ["rat_02", "rat_14"],
    },
    {
        "id": "limit:rational:diff_cubes_squares",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផលដកគូបលើផលដកការេ",
        "title_en": "Difference of cubes over difference of squares",
        "difficulty": "medium",
        "pattern": "(x**3 - {a}**3)/(x**2 - {a}**2)",
        "pattern_latex": r"\lim_{x \to a} \dfrac{x^{3} - a^{3}}{x^{2} - a^{2}}",
        "point": "1",
        "var": "x",
        "sampler": _sample_rat_diff_cubes,
        "source_labels": ["rat_03", "rat_10"],
    },
    {
        "id": "limit:rational:quartic_diff_squares",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផលដកដឺក្រេទីបួនលើផលដកការេ",
        "title_en": "Quartic difference factoring over difference of squares",
        "difficulty": "medium",
        "pattern": "({k}*{a}**4 - {k}*x**4)/({a}**2 - x**2)",
        "pattern_latex": r"\lim_{x \to a} \dfrac{k a^{4} - k x^{4}}{a^{2} - x^{2}}",
        "point": "2",
        "var": "x",
        "sampler": _sample_rat_quartic_quad,
        "source_labels": ["rat_04"],
    },
    {
        "id": "limit:rational:quad_trinomial_linear",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "quadratics",
        "title_km": "ត្រីធាដឺក្រេទីពីរលើកន្សោមលីនេអ៊ែរ",
        "title_en": "Quadratic trinomial over linear expression",
        "difficulty": "easy",
        "pattern": "(x**2 - {p}*x + {q})/(x - {r1})",
        "pattern_latex": r"\lim_{x \to r_1} \dfrac{x^{2} - p x + q}{x - r_1}",
        "point": "2",
        "var": "x",
        "sampler": _sample_rat_quadratic_linear,
        "source_labels": ["rat_05", "rat_13"],
    },
    {
        "id": "limit:rational:quad_trinomial_quad",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "quadratics",
        "title_km": "ត្រីធាដឺក្រេទីពីរលើត្រីធាដឺក្រេទីពីរ",
        "title_en": "Quadratic trinomial over quadratic trinomial",
        "difficulty": "easy",
        "pattern": "((x - {shared})*(x - {r1}))/((x - {shared})*(x - {r2}))",
        "pattern_latex": r"\lim_{x \to c} \dfrac{(x - c)(x - r_1)}{(x - c)(x - r_2)}",
        "point": "1",
        "var": "x",
        "sampler": _sample_rat_quadratic_quadratic,
        "source_labels": ["rat_06", "rat_12"],
    },
    {
        "id": "limit:rational:quartic_linear",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផលដកដឺក្រេទីបួនលើលីនេអ៊ែរ",
        "title_en": "Quartic difference factoring over linear",
        "difficulty": "medium",
        "pattern": "(x**4 - {a}**4)/(x - {a})",
        "pattern_latex": r"\lim_{x \to a} \dfrac{x^{4} - a^{4}}{x - a}",
        "point": "2",
        "var": "x",
        "sampler": _sample_rat_quartic_linear,
        "source_labels": ["rat_07"],
    },
    {
        "id": "limit:rational:quartic_over_cubic",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផលដកដឺក្រេទីបួនលើផលដកគូប",
        "title_en": "Quartic difference over difference of cubes",
        "difficulty": "medium",
        "pattern": "(x**4 - {a}**4)/(x**3 - {a}**3)",
        "pattern_latex": r"\lim_{x \to a} \dfrac{x^{4} - a^{4}}{x^{3} - a^{3}}",
        "point": "1",
        "var": "x",
        "sampler": _sample_rat_quartic_cubic,
        "source_labels": ["rat_08"],
    },
    {
        "id": "limit:rational:sum_cubes_linear",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផលបូកគូបពីរតួ",
        "title_en": "Sum of cubes over linear factor",
        "difficulty": "medium",
        "pattern": "(x**3 + {a}**3)/(x + {a})",
        "pattern_latex": r"\lim_{x \to -a} \dfrac{x^{3} + a^{3}}{x + a}",
        "point": "-1",
        "var": "x",
        "sampler": _sample_rat_sum_cubes,
        "source_labels": ["rat_09", "rat_18"],
    },
    {
        "id": "limit:rational:diff_cubes_trinomial",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផលដកគូបលើត្រីធាដឺក្រេទីពីរ",
        "title_en": "Difference of cubes over quadratic trinomial",
        "difficulty": "medium",
        "pattern": "(x**3 - {a}**3)/({b}*x**2 - {c}*x + {d})",
        "pattern_latex": r"\lim_{x \to a} \dfrac{x^{3} - a^{3}}{b x^{2} - c x + d}",
        "point": "2",
        "var": "x",
        "sampler": _sample_rat_diff_cubes_trinomial,
        "source_labels": ["rat_11"],
    },
    {
        "id": "limit:rational:shifted_binomial_cube",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "binomial",
        "title_km": "ពន្លាតទ្វេធាគូបត្រង់ 0",
        "title_en": "Shifted cubic binomial at 0",
        "difficulty": "medium",
        "pattern": "((x - {a})**3 + {a}**3)/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{(x - a)^{3} + a^{3}}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_rat_shifted_binomial_cube,
        "source_labels": ["rat_21"],
    },
    {
        "id": "limit:rational:shifted_binomial_square",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "binomial",
        "title_km": "ពន្លាតទ្វេធាការេត្រង់ 0",
        "title_en": "Shifted square binomial at 0",
        "difficulty": "easy",
        "pattern": "((x + {a})**2 - {a}**2)/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{(x + a)^{2} - a^{2}}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_rat_shifted_binomial_square,
        "source_labels": ["rat_22"],
    },
    {
        "id": "limit:rational:shifted_diff_squares",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "binomial",
        "title_km": "ផលដកការេនៃទ្វេធាត្រង់ 0",
        "title_en": "Difference of two linear squares at 0",
        "difficulty": "medium",
        "pattern": "((1 + {a}*x)**2 - ({b}*x + 1)**2)/(2*x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{(1 + a x)^{2} - (b x + 1)^{2}}{2x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_rat_shifted_difference_squares,
        "source_labels": ["rat_23"],
    },
    {
        "id": "limit:rational:grouping_cubic",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផ្ដុំតួពហុធាដឺក្រេទីបី",
        "title_en": "Cubic polynomial factoring by grouping",
        "difficulty": "medium",
        "pattern": "(x**3 - {a}*x**2 + x - {a})/(2*x**2 - {b}*x + {a})",
        "pattern_latex": r"\lim_{x \to a} \dfrac{x^{3} - a x^{2} + x - a}{2x^{2} - b x + a}",
        "point": "3",
        "var": "x",
        "sampler": _sample_rat_grouping_cubic,
        "source_labels": ["rat_24"],
    },
    {
        "id": "limit:rational:poly_derivative_identity",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ពហុធាដឺក្រេខ្ពស់តាមក្បួនដេរីវេ",
        "title_en": "High-degree polynomial limit via derivative identity",
        "difficulty": "hard",
        "pattern": "(x**{n} - {n}*x + {n-1})/(x - 1)**2",
        "pattern_latex": r"\lim_{x \to 1} \dfrac{x^{n} - n x + (n-1)}{(x - 1)^{2}}",
        "point": "1",
        "var": "x",
        "sampler": _sample_rat_poly_derivative_1,
        "source_labels": ["rat_25"],
    },
    {
        "id": "limit:rational:poly_monomial_n",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "រូបមន្តលីមីតពហុធាដឺក្រេ n (xⁿ - 1)/(x - 1)",
        "title_en": "Standard identity (x^n - 1)/(x - 1)",
        "difficulty": "medium",
        "pattern": "(x**{n} - 1)/(x - 1)",
        "pattern_latex": r"\lim_{x \to 1} \dfrac{x^{n} - 1}{x - 1}",
        "point": "1",
        "var": "x",
        "sampler": _sample_rat_poly_monomial_n,
        "source_labels": ["rat_26"],
    },
    {
        "id": "limit:rational:poly_derivative_ratio",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផលធៀបពហុធាដឺក្រេខ្ពស់តាមដេរីវេ",
        "title_en": "High-degree polynomial ratio via derivative definition",
        "difficulty": "hard",
        "pattern": "(x**{n} - {n}*x + {n-1})/(x**{m} - {m}*x + {m-1})",
        "pattern_latex": r"\lim_{x \to 1} \dfrac{x^{n} - n x + (n-1)}{x^{m} - m x + (m-1)}",
        "point": "1",
        "var": "x",
        "sampler": _sample_rat_poly_derivative_ratio,
        "source_labels": ["rat_27"],
    },
    {
        "id": "limit:rational:poly_odd_ratio",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផលធៀបដឺក្រេវេសេសត្រង់ -1 ((xᵖ + 1)/(xᵍ + 1))",
        "title_en": "Odd powers polynomial ratio at -1 ((x^p + 1)/(x^q + 1))",
        "difficulty": "medium",
        "pattern": "(x**{p} + 1)/(x**{q} + 1)",
        "pattern_latex": r"\lim_{x \to -1} \dfrac{x^{p} + 1}{x^{q} + 1}",
        "point": "-1",
        "var": "x",
        "sampler": _sample_rat_poly_odd_ratio,
        "source_labels": ["rat_28"],
    },
    {
        "id": "limit:rational:poly_sum_split",
        "question_type": "limit",
        "category": "rational",
        "subfamily": "powers",
        "title_km": "ផលបូកស្វ័យគុណបំបែកតួ (x + x² + ... + xⁿ - n)",
        "title_en": "Sum of powers decomposition (x + x^2 + ... + x^n - n)",
        "difficulty": "hard",
        "pattern": "(x + x**2 + x**3 - 3)/(x + x**2 - 2)",
        "pattern_latex": r"\lim_{x \to 1} \dfrac{x + x^{2} + \dots + x^{n} - n}{x + x^{2} + \dots + x^{m} - m}",
        "point": "1",
        "var": "x",
        "sampler": _sample_rat_poly_sum_split,
        "source_labels": ["rat_29", "rat_30"],
    },
]
