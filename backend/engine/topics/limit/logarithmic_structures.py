"""Logarithmic limit structures registry matching textbook exercises.

Contains authentic logarithmic limit structures with:
- semantic IDs
- authentic textbook labels ['log_01'], ['log_11'], etc.
- deterministic SymPy closed-form samplers
- authentic Khmer titles (no fake code abbreviations)
"""
import random

def _sample_log_sum_oo(rng):
    a = rng.choice([1, 2, 3])
    return f"{a}*x**2 + x + ln(x)" if a != 1 else "x**2 + x + ln(x)", "oo", {"a": a}

def _sample_log_diff_factor_oo(rng):
    a = rng.choice([2, 3])
    return f"x**2 + {a}*x - x*ln(x)", "oo", {"a": a}

def _sample_log_poly_dom_neg_oo(rng):
    a = rng.choice([3, 4, 5])
    return f"{a}*ln(x) - 4*x**2 + x", "oo", {"a": a}

def _sample_log_sq_diff_oo(rng):
    k = rng.choice([1, 2, 3])
    return f"ln(x)**2 - {k}*x*ln(x)", "oo", {"k": k}

def _sample_log_linear_fraction_oo(rng):
    a = rng.choice([2020, 2024, 2026])
    b = rng.choice([2019, 2023, 2025])
    return f"({a} - {b}*ln(x))/x", "oo", {"a": a, "b": b}

def _sample_log_cubic_dom_oo(rng):
    a = rng.choice([2, 3, 4])
    return f"{a}*x**2*ln(x) - 3*x**3 + 5*x", "oo", {"a": a}

def _sample_log_quad_rational_1_oo(rng):
    k = rng.choice([1, 2, 3])
    return f"(x**2 - {k}*x*ln(x) + 5)/x**2", "oo", {"k": k}

def _sample_log_quad_rational_neg_oo(rng):
    a = rng.choice([2, 3, 4])
    return f"({a}*ln(x) + x**2 - 2)/(-x**2)", "oo", {"a": a}

def _sample_log_quad_rational_half_oo(rng):
    k = rng.choice([1, 2, 3])
    return f"(x**2 + {k}*x - ln(x))/(2*x**2 - 3*x)", "oo", {"k": k}

def _sample_log_quad_rational_two_oo(rng):
    a = rng.choice([2, 3])
    return f"({a}*x**2 - x*ln(x))/(x**2 - x + ln(x))", "oo", {"a": a}

def _sample_log_rational_inside_zero(rng):
    k = rng.choice([1, 2, 3])
    return f"ln((x + {k})/(x - {k}))", "oo", {"k": k}

def _sample_log_rational_inside_val(rng):
    a = rng.choice([2, 3])
    b = rng.choice([3, 4])
    return f"ln(({a}*x - 4)/(x + {b}))", "oo", {"a": a, "b": b}

def _sample_log_growth_zero_plus(rng):
    a = rng.choice([1, 2, 3])
    return f"x**2/2 + {a}*x - x*ln(x)", "0", {"a": a, "side": "+"}

def _sample_log_split_growth_oo(rng):
    a = rng.choice([3, 4, 5])
    return f"x + {a} - (x + ln(x))/(x + 1)", "oo", {"a": a}

def _sample_log_diff_cube_split_oo(rng):
    k = rng.choice([1, 2, 3])
    return f"(x**3 - {k})/x**2 - ln(x)", "oo", {"k": k}

def _sample_log_sinc_zero_standard(rng):
    a = rng.choice([2, 3, 4, 5])
    return f"ln(1 + {a}*x)/x", "0", {"a": a}

def _sample_log_sinc_zero_ratio(rng):
    a = rng.choice([2, 3, 4])
    b = rng.choice([3, 5])
    return f"ln(1 + {a}*x)/({b}*x)", "0", {"a": a, "b": b}

def _sample_log_ratio_two_logs(rng):
    a = rng.choice([2, 3, 4])
    b = rng.choice([5, 6, 7])
    return f"ln(1 + {a}*x)/ln(1 + {b}*x)", "0", {"a": a, "b": b}

def _sample_log_euler_diff_oo(rng):
    c = rng.choice([1, 2, 3])
    k = rng.choice([1, 2, 3])
    return f"{c}*x*(ln(x + {k}) - ln(x))", "oo", {"c": c, "k": k}


def _sample_log_diff_linear_terms(rng):
    a = rng.choice([1, 2, 3])
    b = rng.choice([1, 2])
    c = rng.choice([2, 3])
    return f"(ln(1 + {a}*x) - {c}*ln(1 - {b}*x))/x", "0", {"a": a, "b": b, "c": c}


def _sample_log_sum_linear_terms(rng):
    a = rng.choice([2, 3])
    b = rng.choice([3, 4, 5])
    c1 = rng.choice([2, 3])
    c2 = rng.choice([2, 3])
    return f"({c1}*ln(1 - {a}*x) + {c2}*ln(1 + {b}*x))/x", "0", {"a": a, "b": b, "c1": c1, "c2": c2}


def _sample_log_mixed_linear_quad(rng):
    a = rng.choice([2, 3, 4])
    b = rng.choice([3, 4, 5])
    return f"(x*ln(1 + {a}*x) + {b}*ln(1 + x**2))/x**2", "0", {"a": a, "b": b}


def _sample_log_quad_diff_ratio(rng):
    a = rng.choice([2, 4, 6])
    b = rng.choice([2, 4])
    k = rng.choice([2, 3])
    return f"(ln(1 + {a}*x**2) - x*ln(1 - {b}*x))/({k}*x**2)", "0", {"a": a, "b": b, "k": k}


def _sample_log_trig_sin_combo(rng):
    a = rng.choice([2, 3])
    b = rng.choice([2, 3])
    c = rng.choice([2, 3])
    return f"(ln(1 + {a}*sin(x)) - {c}*ln(1 - sin({b}*x)))/x", "0", {"a": a, "b": b, "c": c}


def _sample_log_quad_cos_half_angle(rng):
    a = rng.choice([1, 2, 3])
    b = rng.choice([2, 4])
    return f"ln(2 + {a}*x**2 - cos({b}*x))/x**2", "0", {"a": a, "b": b}


def _sample_log_sinc_cos_half_angle(rng):
    a = rng.choice([2, 3, 4])
    b = rng.choice([2, 4])
    return f"ln(2 + x*sin({a}*x) - cos({b}*x))/x**2", "0", {"a": a, "b": b}


def _sample_log_exp_cos_combo(rng):
    a = rng.choice([2, 4])
    return f"ln(2*e**(x**2) - cos({a}*x))/x**2", "0", {"a": a}


def _sample_log_exp_neg_cos_combo(rng):
    a = rng.choice([2, 4])
    return f"ln(2 - e**(-x**2)*cos({a}*x))/x**2", "0", {"a": a}


def _sample_log_cos_product_combo(rng):
    a = rng.choice([2, 4])
    b = rng.choice([2, 4])
    return f"ln(2 - cos({a}*x)*cos({b}*x))/x**2", "0", {"a": a, "b": b}


def _sample_log_diff_rational_oo(rng):
    a = rng.choice([2, 3, 4])
    b = rng.choice([1, 2])
    return f"ln(x + {a}) - ln(x) - {b}/(x + {a}) + 1/4", "oo", {"a": a, "b": b}


def _sample_log_linear_minus_log_oo(rng):
    a = rng.choice([2, 3])
    b = rng.choice([5, 7, 9])
    c = rng.choice([7, 11, 13])
    return f"{a}*x - {b} - {c}*ln(x)", "oo", {"a": a, "b": b, "c": c}


LOGARITHMIC_STRUCTURES = [

    {
        "id": "limit:logarithmic:sum_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "infinity",
        "title_km": "ផលបូកពហុធានិងលោការីតនៅ +∞ (ax² + x + ln x)",
        "title_en": "Sum of polynomial and log at +infinity",
        "difficulty": "easy",
        "pattern": "{a}*x**2 + x + ln(x)",
        "pattern_latex": r"\lim_{x \to +\infty} (a x^{2} + x + \ln x)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_sum_oo,
        "source_labels": ["log_01"],
    },
    {
        "id": "limit:logarithmic:diff_factor_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "infinity",
        "title_km": "ទាញកត្តាដឺក្រេខ្ពស់នៅ +∞ (ax² + 2x - x ln x)",
        "title_en": "Factor dominant power at +infinity",
        "difficulty": "medium",
        "pattern": "{a}*x**2 + 2*x - x*ln(x)",
        "pattern_latex": r"\lim_{x \to +\infty} (a x^{2} + 2x - x\ln x)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_diff_factor_oo,
        "source_labels": ["log_02"],
    },
    {
        "id": "limit:logarithmic:poly_dom_neg_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "infinity",
        "title_km": "ពហុធាដឺក្រេពីរមានមេគុណអវិជ្ជមាន (3 ln x - ax² + x)",
        "title_en": "Negative dominant polynomial at +infinity",
        "difficulty": "medium",
        "pattern": "3*ln(x) - {a}*x**2 + x",
        "pattern_latex": r"\lim_{x \to +\infty} (3\ln x - a x^{2} + x)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_poly_dom_neg_oo,
        "source_labels": ["log_03"],
    },
    {
        "id": "limit:logarithmic:sq_diff_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "infinity",
        "title_km": "ផលដកលោការីតការេ (ln² x - kx ln x)",
        "title_en": "Log squared difference at +infinity",
        "difficulty": "medium",
        "pattern": "ln(x)**2 - {k}*x*ln(x)",
        "pattern_latex": r"\lim_{x \to +\infty} (\ln^{2} x - k x\ln x)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_sq_diff_oo,
        "source_labels": ["log_04"],
    },
    {
        "id": "limit:logarithmic:linear_fraction_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "infinity",
        "title_km": "លំដាប់កំណើនលោការីតលើ x ((a - b ln x)/x)",
        "title_en": "Log growth dominance ratio (a - b ln x)/x",
        "difficulty": "medium",
        "pattern": "({a} - {b}*ln(x))/x",
        "pattern_latex": r"\lim_{x \to +\infty} \dfrac{a - b\ln x}{x}",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_linear_fraction_oo,
        "source_labels": ["log_05"],
    },
    {
        "id": "limit:logarithmic:cubic_dom_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "infinity",
        "title_km": "ពហុធាដឺក្រេបីលុបលើលោការីត (ax² ln x - 3x³ + 5x)",
        "title_en": "Cubic dominance over log at +infinity",
        "difficulty": "medium",
        "pattern": "{a}*x**2*ln(x) - 3*x**3 + 5*x",
        "pattern_latex": r"\lim_{x \to +\infty} (a x^{2}\ln x - 3x^{3} + 5x)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_cubic_dom_oo,
        "source_labels": ["log_06"],
    },
    {
        "id": "limit:logarithmic:quad_rational_1_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "infinity",
        "title_km": "ប្រភាគសនិទានមានលោការីត ((x² - x ln x + k)/x²)",
        "title_en": "Rational-log combination with limit 1",
        "difficulty": "medium",
        "pattern": "(x**2 - x*ln(x) + {k})/x**2",
        "pattern_latex": r"\lim_{x \to +\infty} \dfrac{x^{2} - x\ln x + k}{x^{2}}",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_quad_rational_1_oo,
        "source_labels": ["log_07"],
    },
    {
        "id": "limit:logarithmic:quad_rational_neg_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "infinity",
        "title_km": "ប្រភាគសនិទានមានលោការីត ((a ln x + x² - 2)/(-x²))",
        "title_en": "Rational-log combination with limit -1",
        "difficulty": "medium",
        "pattern": "({a}*ln(x) + x**2 - 2)/(-x**2)",
        "pattern_latex": r"\lim_{x \to +\infty} \dfrac{a\ln x + x^{2} - 2}{-x^{2}}",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_quad_rational_neg_oo,
        "source_labels": ["log_08"],
    },
    {
        "id": "limit:logarithmic:quad_rational_half_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "infinity",
        "title_km": "ប្រភាគសនិទានមានលោការីត ((x² + kx - ln x)/(2x² - 3x))",
        "title_en": "Rational-log combination with limit 1/2",
        "difficulty": "medium",
        "pattern": "(x**2 + {k}*x - ln(x))/(2*x**2 - 3*x)",
        "pattern_latex": r"\lim_{x \to +\infty} \dfrac{x^{2} + k x - \ln x}{2x^{2} - 3x}",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_quad_rational_half_oo,
        "source_labels": ["log_09"],
    },
    {
        "id": "limit:logarithmic:quad_rational_two_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "infinity",
        "title_km": "ប្រភាគសនិទានមានលោការីត ((ax² - x ln x)/(x² - x + ln x))",
        "title_en": "Rational-log combination with limit 2",
        "difficulty": "medium",
        "pattern": "({a}*x**2 - x*ln(x))/(x**2 - x + ln(x))",
        "pattern_latex": r"\lim_{x \to +\infty} \dfrac{a x^{2} - x\ln x}{x^{2} - x + \ln x}",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_quad_rational_two_oo,
        "source_labels": ["log_10"],
    },
    {
        "id": "limit:logarithmic:rational_inside_zero",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "rational",
        "title_km": "លោការីតនៃកន្សោមសនិទាន ln((x+k)/(x-k)) → 0",
        "title_en": "Logarithm of rational function approaching 0",
        "difficulty": "medium",
        "pattern": "ln((x + {k})/(x - {k}))",
        "pattern_latex": r"\lim_{x \to +\infty} \ln\left(\dfrac{x + k}{x - k}\right)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_rational_inside_zero,
        "source_labels": ["log_11"],
    },
    {
        "id": "limit:logarithmic:rational_inside_val",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "rational",
        "title_km": "លោការីតនៃកន្សោមសនិទាន ln((ax-4)/(x+b))",
        "title_en": "Logarithm of rational function approaching ln(a)",
        "difficulty": "medium",
        "pattern": "ln(({a}*x - 4)/(x + {b}))",
        "pattern_latex": r"\lim_{x \to +\infty} \ln\left(\dfrac{a x - 4}{x + b}\right)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_rational_inside_val,
        "source_labels": ["log_12"],
    },
    {
        "id": "limit:logarithmic:growth_zero_plus",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "growth_zero",
        "title_km": "លំដាប់កំណើនលោការីតត្រង់ 0⁺ (x ln x → 0)",
        "title_en": "Logarithmic growth dominance at 0+ (x ln x -> 0)",
        "difficulty": "medium",
        "pattern": "x**2/2 + x - x*ln(x)",
        "pattern_latex": r"\lim_{x \to 0^+} \left(\dfrac{x^{2}}{2} + x - x\ln x\right)",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_growth_zero_plus,
        "source_labels": ["log_16"],
    },
    {
        "id": "limit:logarithmic:sinc_zero_standard",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "លីមីតគ្រឹះលោការីត ln(1 + ax)/x",
        "title_en": "Standard logarithmic limit ln(1 + ax)/x",
        "difficulty": "easy",
        "pattern": "ln(1 + {a}*x)/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\ln(1 + a x)}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_sinc_zero_standard,
        "source_labels": ["log_22"],
    },
    {
        "id": "limit:logarithmic:sinc_zero_ratio",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "ផលធៀបលោការីតត្រង់ 0 (ln(1 + ax)/(bx))",
        "title_en": "Ratio of logarithmic limit at 0 (ln(1 + ax)/(bx))",
        "difficulty": "easy",
        "pattern": "ln(1 + {a}*x)/({b}*x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\ln(1 + a x)}{b x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_sinc_zero_ratio,
        "source_labels": ["log_23"],
    },
    {
        "id": "limit:logarithmic:ratio_two_logs",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "ផលធៀបលោការីតពីរត្រង់ 0 (ln(1 + ax)/ln(1 + bx))",
        "title_en": "Ratio of two logarithms at 0",
        "difficulty": "medium",
        "pattern": "ln(1 + {a}*x)/ln(1 + {b}*x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\ln(1 + a x)}{\ln(1 + b x)}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_ratio_two_logs,
        "source_labels": ["log_24"],
    },
    {
        "id": "limit:logarithmic:euler_diff_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "rational",
        "title_km": "លីមីតអនុគមន៍លោការីតនៅអនន្ត (បំលែងជា Euler)",
        "title_en": "Logarithmic limit at infinity (Euler transformation)",
        "difficulty": "hard",
        "pattern": "{c}*x*(ln(x + {k}) - ln(x))",
        "pattern_latex": r"\lim_{x \to +\infty} c\,x\left(\ln(x + k) - \ln x\right)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_euler_diff_oo,
        "source_labels": ["log_42"],
    },
    {
        "id": "limit:logarithmic:diff_linear_terms",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "ផលដកលោការីតលីនេអ៊ែរ ((ln(1+ax) - c ln(1-bx))/x)",
        "title_en": "Difference of linear logarithmic terms (ln(1+ax) - c ln(1-bx))/x",
        "difficulty": "hard",
        "pattern": "(ln(1 + {a}*x) - {c}*ln(1 - {b}*x))/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\ln(1 + a x) - c\ln(1 - b x)}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_diff_linear_terms,
        "source_labels": ["p98_1a", "log_25"],
    },
    {
        "id": "limit:logarithmic:sum_linear_terms",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "ផលបូកលោការីតលីនេអ៊ែរ ((c₁ln(1-ax) + c₂ln(1+bx))/x)",
        "title_en": "Sum of linear logarithmic terms (c1 ln(1-ax) + c2 ln(1+bx))/x",
        "difficulty": "hard",
        "pattern": "({c1}*ln(1 - {a}*x) + {c2}*ln(1 + {b}*x))/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{c_1\ln(1 - a x) + c_2\ln(1 + b x)}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_sum_linear_terms,
        "source_labels": ["p98_1b", "log_26"],
    },
    {
        "id": "limit:logarithmic:mixed_linear_quad",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "លោការីតចម្រុះការ៉េ ((x ln(1+ax) + b ln(1+x²))/x²)",
        "title_en": "Mixed linear and quadratic log limit (x ln(1+ax) + b ln(1+x^2))/x^2",
        "difficulty": "hard",
        "pattern": "(x*ln(1 + {a}*x) + {b}*ln(1 + x**2))/x**2",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{x\ln(1 + a x) + b\ln(1 + x^{2})}{x^{2}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_mixed_linear_quad,
        "source_labels": ["p98_1c", "log_27"],
    },
    {
        "id": "limit:logarithmic:quad_diff_ratio",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "ផលដកលោការីតការ៉េលើ x² ((ln(1+ax²) - x ln(1-bx))/(kx²))",
        "title_en": "Difference of quadratic logs over x^2 (ln(1+ax^2) - x ln(1-bx))/(kx^2)",
        "difficulty": "hard",
        "pattern": "(ln(1 + {a}*x**2) - x*ln(1 - {b}*x))/({k}*x**2)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\ln(1 + a x^{2}) - x\ln(1 - b x)}{k x^{2}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_quad_diff_ratio,
        "source_labels": ["p98_1d", "log_28"],
    },
    {
        "id": "limit:logarithmic:trig_sin_combo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "លោការីតចម្រុះអនុគមន៍ស៊ីនុស ((ln(1+a sin x) - c ln(1-sin bx))/x)",
        "title_en": "Logarithmic with sine combination (ln(1+a sin x) - c ln(1-sin bx))/x",
        "difficulty": "hard",
        "pattern": "(ln(1 + {a}*sin(x)) - {c}*ln(1 - sin({b}*x)))/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\ln(1 + a\sin x) - c\ln(1 - \sin(b x))}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_trig_sin_combo,
        "source_labels": ["p98_1e", "log_29"],
    },
    {
        "id": "limit:logarithmic:quad_cos_half_angle",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "លោការីតនិងកូស៊ីនុសកន្លះមុំ ln(2 + ax² - cos bx)/x²",
        "title_en": "Logarithmic with cosine half-angle ln(2 + ax^2 - cos bx)/x^2",
        "difficulty": "hard",
        "pattern": "ln(2 + {a}*x**2 - cos({b}*x))/x**2",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\ln(2 + a x^{2} - \cos(b x))}{x^{2}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_quad_cos_half_angle,
        "source_labels": ["p98_1f", "log_30"],
    },
    {
        "id": "limit:logarithmic:sinc_cos_half_angle",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "លោការីតចម្រុះស៊ីនុសនិងកូស៊ីនុស ln(2 + x sin ax - cos bx)/x²",
        "title_en": "Logarithmic with sinc and cosine ln(2 + x sin ax - cos bx)/x^2",
        "difficulty": "hard",
        "pattern": "ln(2 + x*sin({a}*x) - cos({b}*x))/x**2",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\ln(2 + x\sin(a x) - \cos(b x))}{x^{2}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_sinc_cos_half_angle,
        "source_labels": ["p98_1g", "log_31"],
    },
    {
        "id": "limit:logarithmic:exp_cos_combo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "លោការីតចម្រុះអិចស្ប៉ូណង់ស្យែលនិងកូស៊ីនុស ln(2e^(x²) - cos ax)/x²",
        "title_en": "Logarithmic with exponential and cosine ln(2e^(x^2) - cos ax)/x^2",
        "difficulty": "hard",
        "pattern": "ln(2*e**(x**2) - cos({a}*x))/x**2",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\ln(2e^{x^{2}} - \cos(a x))}{x^{2}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_exp_cos_combo,
        "source_labels": ["p98_1h", "log_32"],
    },
    {
        "id": "limit:logarithmic:exp_neg_cos_combo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "លោការីតចម្រុះអិចស្ប៉ូណង់ស្យែលអវិជ្ជមាន ln(2 - e^(-x²)cos ax)/x²",
        "title_en": "Logarithmic with decaying exponential ln(2 - e^(-x^2)cos ax)/x^2",
        "difficulty": "hard",
        "pattern": "ln(2 - e**(-x**2)*cos({a}*x))/x**2",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\ln(2 - e^{-x^{2}}\cos(a x))}{x^{2}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_exp_neg_cos_combo,
        "source_labels": ["p98_1i", "log_33"],
    },
    {
        "id": "limit:logarithmic:cos_product_combo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "zero",
        "title_km": "លោការីតចម្រុះផលគុណកូស៊ីនុស ln(2 - cos ax cos bx)/x²",
        "title_en": "Logarithmic with cosine product ln(2 - cos ax cos bx)/x^2",
        "difficulty": "hard",
        "pattern": "ln(2 - cos({a}*x)*cos({b}*x))/x**2",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\ln(2 - \cos(a x)\cos(b x))}{x^{2}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_log_cos_product_combo,
        "source_labels": ["p98_1j", "log_34"],
    },
    {
        "id": "limit:logarithmic:diff_rational_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "rational",
        "title_km": "ផលដកលោការីតនិងសនិទាននៅ +∞ (ln(x+a) - ln x - b/(x+a) + c)",
        "title_en": "Logarithmic difference with rational tail at +infinity",
        "difficulty": "hard",
        "pattern": "ln(x + {a}) - ln(x) - {b}/(x + {a}) + 1/4",
        "pattern_latex": r"\lim_{x \to +\infty} \left(\ln(x + a) - \ln x - \dfrac{b}{x + a} + \dfrac{1}{4}\right)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_diff_rational_oo,
        "source_labels": ["2014e", "log_35"],
    },
    {
        "id": "limit:logarithmic:linear_minus_log_oo",
        "question_type": "limit",
        "category": "logarithmic",
        "subfamily": "infinity",
        "title_km": "ផលដកលីនេអ៊ែរនិងលោការីតនៅ +∞ (ax - b - c ln x)",
        "title_en": "Linear growth minus logarithm at +infinity (ax - b - c ln x)",
        "difficulty": "medium",
        "pattern": "{a}*x - {b} - {c}*ln(x)",
        "pattern_latex": r"\lim_{x \to +\infty} \left(a x - b - c\ln x\right)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_log_linear_minus_log_oo,
        "source_labels": ["2021c", "log_36"],
    },
]

