"""Trigonometric limit structures registry matching BAC II textbook exercises.

Each structure maps directly to an authentic BAC II / textbook exercise with:
- a semantic ID (no invented abbreviations)
- real source labels (e.g. ['I-01'], ['II-05'])
- clean, non-singular samplers with deterministic SymPy closed forms
- authentic Khmer titles and formula tags
"""
import random
from sympy import pi, sqrt, Rational

# ---------------------------------------------------------------------------
# Samplers for Trigonometric Limits
# ---------------------------------------------------------------------------

def _sample_sinc_standard(rng):
    c = rng.choice([1, 2, 3, 4, 5])
    k = rng.choice([2, 3, 4, 5, 6])
    return f"{c}*sin({k}*x)/x", "0", {"c": c, "k": k}

def _sample_half_angle(rng):
    m = rng.choice([1, 2, 3, 4])
    b = rng.choice([1, 2, 3])
    return f"(1 - cos({m}*x))/({b}*x**2)", "0", {"m": m, "b": b}

def _sample_sin_ratio_zero(rng):
    a = rng.choice([2, 3, 4, 5])
    b = rng.choice([2, 3, 4, 5])
    while a == b:
        b = rng.choice([2, 3, 4, 5])
    return f"sin({a}*x)/sin({b}*x)", "0", {"a": a, "b": b}

def _sample_sin_ratio_pi(rng):
    # a and b odd so sin(a*(pi - t)) = sin(a*pi - a*t) = (-1)^(a-1)*sin(at) = sin(at)
    a = rng.choice([3, 5, 7])
    b = rng.choice([3, 5, 7])
    while a == b:
        b = rng.choice([3, 5, 7])
    return f"sin({a}*x)/sin({b}*x)", "pi", {"a": a, "b": b}

def _sample_linear_cos_pi(rng):
    k = rng.choice([1, 2, 3])
    return f"({k}*x + {k}*pi*cos(x))/(pi - x)", "pi", {"k": k}

def _sample_linear_sin_pi2(rng):
    k = rng.choice([1, 2])
    return f"({k}*x - {k}*(pi/2)*sin(x))/((pi/2) - x)", "pi/2", {"k": k}

def _sample_sin_poly_root(rng):
    a = rng.choice([2, 3, 4])
    return f"sin(pi*x)/(x**2 - {a}*x)", f"{a}", {"a": a}

def _sample_cos_conjugate_pi3(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*sin(3*x)/(1 - 2*cos(x))" if k != 1 else "sin(3*x)/(1 - 2*cos(x))", "pi/3", {"k": k}

def _sample_half_angle_pi2(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(1 - sin(x))/((pi/2) - x)**2", "pi/2", {"k": k}

def _sample_sin_cos_diff_ratio_pi2(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(1 - sin(x) + cos(x))/(1 - sin(x) - cos(x))" if k != 1 else "(1 - sin(x) + cos(x))/(1 - sin(x) - cos(x))", "pi/2", {"k": k}

def _sample_tan_singularity_pi2(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(x - pi/2)*tan(x)", "pi/2", {"k": k}

def _sample_cos2x_tan2x_pi4(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*cos(2*x)/tan(2*x)" if k != 1 else "cos(2*x)/tan(2*x)", "pi/4", {"k": k}

def _sample_shifted_cos_quad_root(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(1 + cos(pi*x))/(1 - x)**2", "1", {"k": k}

def _sample_shifted_sin_quad_root(rng):
    k = rng.choice([1, 2])
    return f"{k}*(1 - sin(pi*x/2))/(1 - x)**2", "1", {"k": k}

def _sample_shifted_sin_linear_pi(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(1 - sin(x/2))/(pi - x)" if k != 1 else "(1 - sin(x/2))/(pi - x)", "pi", {"k": k}

def _sample_tan_poly_root(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*tan(pi*x)/(1 - x**2)" if k != 1 else "tan(pi*x)/(1 - x**2)", "1", {"k": k}

def _sample_tan_linear_pi(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(pi - x)*tan(x/2)" if k != 1 else "(pi - x)*tan(x/2)", "pi", {"k": k}

def _sample_cos_diff_squares_pi2(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*cos(x)/(pi**2 - 4*x**2)" if k != 1 else "cos(x)/(pi**2 - 4*x**2)", "pi/2", {"k": k}

def _sample_simpson_linear_pi4(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(sin(x) - cos(x))/(pi - 4*x)" if k != 1 else "(sin(x) - cos(x))/(pi - 4*x)", "pi/4", {"k": k}

def _sample_sin_pi_linear_root(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*sin(pi*x)/(1 - x**2)" if k != 1 else "sin(pi*x)/(1 - x**2)", "1", {"k": k}

def _sample_cos_poly_root(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*cos(pi*x/2)/(x**2 - 1)" if k != 1 else "cos(pi*x/2)/(x**2 - 1)", "1", {"k": k}

def _sample_radical_tan_pi4(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(sqrt(2)*sin(x) - 1)/(tan(x) - 1)" if k != 1 else "(sqrt(2)*sin(x) - 1)/(tan(x) - 1)", "pi/4", {"k": k}

def _sample_simpson_sin3x_pi3(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(sin(x) - sqrt(3)*cos(x))/sin(3*x)" if k != 1 else "(sin(x) - sqrt(3)*cos(x))/sin(3*x)", "pi/3", {"k": k}

def _sample_sinc_poly_shifted(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*sin(x - 1)/(x**2 - 1)" if k != 1 else "sin(x - 1)/(x**2 - 1)", "1", {"k": k}

def _sample_cos2x_shifted_pi2(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(1 + cos(2*x))/((pi/2) - x)**2" if k != 1 else "(1 + cos(2*x))/((pi/2) - x)**2", "pi/2", {"k": k}

def _sample_tan_tan_product_pi(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*tan(x)*tan(x/2)" if k != 1 else "tan(x)*tan(x/2)", "pi", {"k": k}

def _sample_sin_pi_quad_frac(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*sin(pi*x)/(1 - x**2/4)" if k != 1 else "sin(pi*x)/(1 - x**2/4)", "2", {"k": k}

def _sample_cos2x_factor_diff_pi4(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(sin(x) - cos(x))/cos(2*x)" if k != 1 else "(sin(x) - cos(x))/cos(2*x)", "pi/4", {"k": k}

def _sample_linear_simpson_pi4(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(x - pi/4)/(cos(x) - sin(x))" if k != 1 else "(x - pi/4)/(cos(x) - sin(x))", "pi/4", {"k": k}

def _sample_sin_shifted_cos_pi3(rng):
    k = rng.choice([1, 2, 3])
    return f"{2*k}*sin(x - pi/3)/(1 - 2*cos(x))" if k != 1 else "2*sin(x - pi/3)/(1 - 2*cos(x))", "pi/3", {"k": k}

def _sample_poly_tan_pi4(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(4 - x**2)*tan(pi*x/4)" if k != 1 else "(4 - x**2)*tan(pi*x/4)", "2", {"k": k}

def _sample_tan_radical_pi4(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(1 - tan(x))/(1 - sqrt(2)*sin(x))" if k != 1 else "(1 - tan(x))/(1 - sqrt(2)*sin(x))", "pi/4", {"k": k}

def _sample_linear_sin_pi3(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(pi - 3*x)/(sqrt(3) - 2*sin(x))" if k != 1 else "(pi - 3*x)/(sqrt(3) - 2*sin(x))", "pi/3", {"k": k}

def _sample_double_radical_pi4(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(1 - sqrt(2)*cos(x))/(1 - sqrt(2)*sin(x))" if k != 1 else "(1 - sqrt(2)*cos(x))/(1 - sqrt(2)*sin(x))", "pi/4", {"k": k}

def _sample_cos2x_diff_denom_pi4(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*cos(2*x)/(cos(x) - sin(x))" if k != 1 else "cos(2*x)/(cos(x) - sin(x))", "pi/4", {"k": k}

def _sample_quad_trinomial_sin_pi6(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(2*sin(x)**2 - 3*sin(x) + 1)/(4*sin(x)**2 - 1)" if k != 1 else "(2*sin(x)**2 - 3*sin(x) + 1)/(4*sin(x)**2 - 1)", "pi/6", {"k": k}

def _sample_radical_cos2_pi2(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(sqrt(2) - sqrt(1 + sin(x)))/cos(x)**2" if k != 1 else "(sqrt(2) - sqrt(1 + sin(x)))/cos(x)**2", "pi/2", {"k": k}

def _sample_sin_cos2x_pi6(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(2*sin(x) - 1)/(1 - 2*cos(2*x))" if k != 1 else "(2*sin(x) - 1)/(1 - 2*cos(2*x))", "pi/6", {"k": k}

def _sample_cos_cos2x_pi3(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(2*cos(x) - 1)/(2*cos(2*x) + 1)" if k != 1 else "(2*cos(x) - 1)/(2*cos(2*x) + 1)", "pi/3", {"k": k}

def _sample_cos2x_radical_cos_pi3(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(2*cos(2*x) + 1)/(sqrt(2*cos(x)) - 1)" if k != 1 else "(2*cos(2*x) + 1)/(sqrt(2*cos(x)) - 1)", "pi/3", {"k": k}

def _sample_half_angle_cos2_pi2(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(1 - sin(x))/cos(x)**2" if k != 1 else "(1 - sin(x))/cos(x)**2", "pi/2", {"k": k}

def _sample_double_angle_combo_pi4(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(sin(2*x) - cos(2*x) - 1)/(sin(x) - cos(x))" if k != 1 else "(sin(2*x) - cos(2*x) - 1)/(sin(x) - cos(x))", "pi/4", {"k": k}

def _sample_radical_cos_sin_pi(rng):
    k = rng.choice([1, 2])
    return f"{k}*sqrt(1 + cos(x))/sin(x)" if k != 1 else "sqrt(1 + cos(x))/sin(x)", "pi", {"k": k, "side": "-"}

def _sample_radical_cos2x_sin2x_pi(rng):
    k = rng.choice([1, 2])
    return f"{k}*sqrt(1 - cos(2*x))/sin(2*x)" if k != 1 else "sqrt(1 - cos(2*x))/sin(2*x)", "pi", {"k": k, "side": "-"}


# ---------------------------------------------------------------------------
# Trigonometric Structure Definitions
# ---------------------------------------------------------------------------

TRIG_STRUCTURES = [
    {
        "id": "limit:trig:sinc_standard",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "sinc_standard",
        "title_km": "លីមីតគ្រឹះ sin(kx)/x",
        "title_en": "Fundamental limit sin(kx)/x",
        "difficulty": "easy",
        "pattern": "{c}*sin({k}*x)/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{c\,\sin(k x)}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_sinc_standard,
        "source_labels": ["2015c", "2016c", "2017b", "2018b", "2021b"],
    },
    {
        "id": "limit:trig:half_angle",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "half_angle",
        "title_km": "លីមីតកន្លះមុំ (1 - cos(mx))/x²",
        "title_en": "Half-angle trig limit (1 - cos(mx))/x²",
        "difficulty": "medium",
        "pattern": "(1 - cos({m}*x))/({b}*x**2)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{1 - \cos(m x)}{b x^{2}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_half_angle,
        "source_labels": ["2019b", "2019c"],
    },
    {
        "id": "limit:trig:sin_ratio_zero",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "sinc_standard",
        "title_km": "ផលធៀបស៊ីនុសត្រង់ 0",
        "title_en": "Ratio of sines at 0",
        "difficulty": "easy",
        "pattern": "sin({a}*x)/sin({b}*x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{\sin(a x)}{\sin(b x)}",
        "point": "0",
        "var": "x",
        "sampler": _sample_sin_ratio_zero,
        "source_labels": ["I-01"],
    },
    {
        "id": "limit:trig:sin_ratio_pi",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ផលធៀបស៊ីនុសត្រង់ π",
        "title_en": "Ratio of sines at pi",
        "difficulty": "medium",
        "pattern": "sin({a}*x)/sin({b}*x)",
        "pattern_latex": r"\lim_{x \to \pi} \dfrac{\sin(a x)}{\sin(b x)}",
        "point": "pi",
        "var": "x",
        "sampler": _sample_sin_ratio_pi,
        "source_labels": ["I-02"],
    },
    {
        "id": "limit:trig:linear_cos_pi",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ប្តូរអថេរត្រង់ π (កន្សោម x + π cos x)",
        "title_en": "Change of variable at pi (x + pi cos x)",
        "difficulty": "medium",
        "pattern": "({k}*x + {k}*pi*cos(x))/(pi - x)",
        "pattern_latex": r"\lim_{x \to \pi} \dfrac{k x + k\pi\cos x}{\pi - x}",
        "point": "pi",
        "var": "x",
        "sampler": _sample_linear_cos_pi,
        "source_labels": ["I-03"],
    },
    {
        "id": "limit:trig:linear_sin_pi2",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ប្តូរអថេរត្រង់ π/2 (កន្សោម x - (π/2) sin x)",
        "title_en": "Change of variable at pi/2 (x - (pi/2) sin x)",
        "difficulty": "medium",
        "pattern": "({k}*x - {k}*(pi/2)*sin(x))/((pi/2) - x)",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{2}} \dfrac{k x - k\frac{\pi}{2}\sin x}{\frac{\pi}{2} - x}",
        "point": "pi/2",
        "var": "x",
        "sampler": _sample_linear_sin_pi2,
        "source_labels": ["I-04"],
    },
    {
        "id": "limit:trig:sin_poly_root",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ប្តូរអថេរត្រង់ចំនួនគត់ (sin(πx) លើពហុធា)",
        "title_en": "Change of variable at integer root (sin(pi x)/(x^2 - ax))",
        "difficulty": "medium",
        "pattern": "sin(pi*x)/(x**2 - {a}*x)",
        "pattern_latex": r"\lim_{x \to a} \dfrac{\sin(\pi x)}{x^2 - a x}",
        "point": "2",
        "var": "x",
        "sampler": _sample_sin_poly_root,
        "source_labels": ["I-05", "I-18"],
    },
    {
        "id": "limit:trig:cos_conjugate_pi3",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ប្តូរអថេរត្រង់ π/3 (sin 3x លើ 1 - 2cos x)",
        "title_en": "Change of variable at pi/3 (sin 3x / (1 - 2cos x))",
        "difficulty": "medium",
        "pattern": "{k}*sin(3*x)/(1 - 2*cos(x))",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{3}} \dfrac{k\,\sin 3x}{1 - 2\cos x}",
        "point": "pi/3",
        "var": "x",
        "sampler": _sample_cos_conjugate_pi3,
        "source_labels": ["I-06"],
    },
    {
        "id": "limit:trig:half_angle_pi2",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "half_angle",
        "title_km": "លីមីតកន្លះមុំត្រង់ π/2 ((1 - sin x)/(π/2 - x)²)",
        "title_en": "Half-angle limit at pi/2 ((1 - sin x)/(pi/2 - x)^2)",
        "difficulty": "medium",
        "pattern": "{k}*(1 - sin(x))/((pi/2) - x)**2",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{2}} \dfrac{k(1 - \sin x)}{\left(\frac{\pi}{2} - x\right)^2}",
        "point": "pi/2",
        "var": "x",
        "sampler": _sample_half_angle_pi2,
        "source_labels": ["I-07"],
    },
    {
        "id": "limit:trig:sin_cos_diff_ratio_pi2",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "half_angle",
        "title_km": "ផលធៀបស៊ីនុសកូស៊ីនុសត្រង់ π/2",
        "title_en": "Sine-cosine linear ratio at pi/2",
        "difficulty": "hard",
        "pattern": "{k}*(1 - sin(x) + cos(x))/(1 - sin(x) - cos(x))",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{2}} \dfrac{k\left(1 - \sin x + \cos x\right)}{1 - \sin x - \cos x}",
        "point": "pi/2",
        "var": "x",
        "sampler": _sample_sin_cos_diff_ratio_pi2,
        "source_labels": ["I-08"],
    },
    {
        "id": "limit:trig:tan_singularity_pi2",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "តង់សង់ត្រង់អសនិទាន π/2 ((x - π/2) tan x)",
        "title_en": "Tangent singularity at pi/2 ((x - pi/2) tan x)",
        "difficulty": "medium",
        "pattern": "{k}*(x - pi/2)*tan(x)",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{2}} k\left(x - \frac{\pi}{2}\right)\tan x",
        "point": "pi/2",
        "var": "x",
        "sampler": _sample_tan_singularity_pi2,
        "source_labels": ["I-09"],
    },
    {
        "id": "limit:trig:cos2x_tan2x_pi4",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "double_angle",
        "title_km": "មុំទ្វេកូស៊ីនុសនិងតង់សង់ត្រង់ π/4 (cos 2x / tan 2x)",
        "title_en": "Double-angle cos 2x over tan 2x at pi/4",
        "difficulty": "medium",
        "pattern": "{k}*cos(2*x)/tan(2*x)",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{4}} \dfrac{k\,\cos 2x}{\tan 2x}",
        "point": "pi/4",
        "var": "x",
        "sampler": _sample_cos2x_tan2x_pi4,
        "source_labels": ["I-10"],
    },
    {
        "id": "limit:trig:shifted_cos_quad_root",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "half_angle",
        "title_km": "ប្តូរអថេរកន្លះមុំ ((1 + cos(πx))/(1 - x)²)",
        "title_en": "Shifted half-angle cos ((1 + cos(pi x))/(1 - x)^2)",
        "difficulty": "medium",
        "pattern": "{k}*(1 + cos(pi*x))/(1 - x)**2",
        "pattern_latex": r"\lim_{x \to 1} \dfrac{k(1 + \cos \pi x)}{(1 - x)^2}",
        "point": "1",
        "var": "x",
        "sampler": _sample_shifted_cos_quad_root,
        "source_labels": ["I-11"],
    },
    {
        "id": "limit:trig:shifted_sin_quad_root",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "half_angle",
        "title_km": "ប្តូរអថេរកន្លះមុំ ((1 - sin(πx/2))/(1 - x)²)",
        "title_en": "Shifted half-angle sin ((1 - sin(pi x/2))/(1 - x)^2)",
        "difficulty": "medium",
        "pattern": "{k}*(1 - sin(pi*x/2))/(1 - x)**2",
        "pattern_latex": r"\lim_{x \to 1} \dfrac{k(1 - \sin \frac{\pi}{2} x)}{(1 - x)^2}",
        "point": "1",
        "var": "x",
        "sampler": _sample_shifted_sin_quad_root,
        "source_labels": ["I-12"],
    },
    {
        "id": "limit:trig:shifted_sin_linear_pi",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ប្តូរអថេរត្រង់ π ((1 - sin(x/2))/(π - x))",
        "title_en": "Shifted linear trig at pi ((1 - sin(x/2))/(pi - x))",
        "difficulty": "easy",
        "pattern": "{k}*(1 - sin(x/2))/(pi - x)",
        "pattern_latex": r"\lim_{x \to \pi} \dfrac{k\left(1 - \sin \frac{x}{2}\right)}{\pi - x}",
        "point": "pi",
        "var": "x",
        "sampler": _sample_shifted_sin_linear_pi,
        "source_labels": ["I-13"],
    },
    {
        "id": "limit:trig:tan_poly_root",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ប្តូរអថេរតង់សង់ត្រង់ 1 (tan(πx)/(1 - x²))",
        "title_en": "Shifted tangent limit at 1 (tan(pi x)/(1 - x^2))",
        "difficulty": "medium",
        "pattern": "{k}*tan(pi*x)/(1 - x**2)",
        "pattern_latex": r"\lim_{x \to 1} \dfrac{k\,\tan \pi x}{1 - x^2}",
        "point": "1",
        "var": "x",
        "sampler": _sample_tan_poly_root,
        "source_labels": ["I-14"],
    },
    {
        "id": "limit:trig:tan_linear_pi",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ផលគុណលីនេអ៊ែរនិងតង់សង់ត្រង់ π ((π - x) tan(x/2))",
        "title_en": "Linear-tangent product at pi ((pi - x) tan(x/2))",
        "difficulty": "medium",
        "pattern": "{k}*(pi - x)*tan(x/2)",
        "pattern_latex": r"\lim_{x \to \pi} k\,(\pi - x) \tan \frac{x}{2}",
        "point": "pi",
        "var": "x",
        "sampler": _sample_tan_linear_pi,
        "source_labels": ["I-15"],
    },
    {
        "id": "limit:trig:cos_diff_squares_pi2",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ប្តូរអថេរត្រង់ π/2 (cos x លើ ផលដកការេ π² - 4x²)",
        "title_en": "Cos x over difference of squares (pi^2 - 4x^2) at pi/2",
        "difficulty": "medium",
        "pattern": "{k}*cos(x)/(pi**2 - 4*x**2)",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{2}} \dfrac{k\,\cos x}{\pi^2 - 4x^2}",
        "point": "pi/2",
        "var": "x",
        "sampler": _sample_cos_diff_squares_pi2,
        "source_labels": ["I-16"],
    },
    {
        "id": "limit:trig:simpson_linear_pi4",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "sum_product",
        "title_km": "បំប្លែងផលដកត្រង់ π/4 ((sin x - cos x)/(π - 4x))",
        "title_en": "Difference of sine and cosine at pi/4 ((sin x - cos x)/(pi - 4x))",
        "difficulty": "medium",
        "pattern": "{k}*(sin(x) - cos(x))/(pi - 4*x)",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{4}} \dfrac{k\left(\sin x - \cos x\right)}{\pi - 4x}",
        "point": "pi/4",
        "var": "x",
        "sampler": _sample_simpson_linear_pi4,
        "source_labels": ["I-17"],
    },
    {
        "id": "limit:trig:cos_poly_root",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ប្តូរអថេរត្រង់ 1 (cos(πx/2)/(x² - 1))",
        "title_en": "Shifted cosine limit at 1 (cos(pi x/2)/(x^2 - 1))",
        "difficulty": "medium",
        "pattern": "{k}*cos(pi*x/2)/(x**2 - 1)",
        "pattern_latex": r"\lim_{x \to 1} \dfrac{k\,\cos \frac{\pi}{2} x}{x^2 - 1}",
        "point": "1",
        "var": "x",
        "sampler": _sample_cos_poly_root,
        "source_labels": ["I-19"],
    },
    {
        "id": "limit:trig:radical_tan_pi4",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "radical_trig",
        "title_km": "គុណកន្សោមឆ្លាស់ត្រង់ π/4 ((√2 sin x - 1)/(tan x - 1))",
        "title_en": "Radical conjugate at pi/4 ((sqrt(2) sin x - 1)/(tan x - 1))",
        "difficulty": "hard",
        "pattern": "{k}*(sqrt(2)*sin(x) - 1)/(tan(x) - 1)",
        "pattern_latex": r"\lim_{x \to \frac{\pi} k\,{4}} \dfrac{\sqrt{2}\sin x - 1}{\tan x - 1}",
        "point": "pi/4",
        "var": "x",
        "sampler": _sample_radical_tan_pi4,
        "source_labels": ["I-20"],
    },
    {
        "id": "limit:trig:simpson_sin3x_pi3",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "sum_product",
        "title_km": "បំប្លែងផលបូកត្រីកោណមាត្រ (sin x - √3 cos x លើ sin 3x)",
        "title_en": "Trig linear combo (sin x - sqrt(3) cos x)/sin 3x at pi/3",
        "difficulty": "hard",
        "pattern": "{k}*(sin(x) - sqrt(3)*cos(x))/sin(3*x)",
        "pattern_latex": r"\lim_{x \to \frac{\pi} k\,{3}} \dfrac{\sin x - \sqrt{3}\cos x}{\sin 3x}",
        "point": "pi/3",
        "var": "x",
        "sampler": _sample_simpson_sin3x_pi3,
        "source_labels": ["I-21"],
    },
    {
        "id": "limit:trig:sinc_poly_shifted",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "sinc_standard",
        "title_km": "លីមីតគ្រឹះ sin(x - a) លើពហុធា",
        "title_en": "Standard sinc limit with shifted polynomial sin(x - 1)/(x^2 - 1)",
        "difficulty": "easy",
        "pattern": "{k}*sin(x - 1)/(x**2 - 1)",
        "pattern_latex": r"\lim_{x \to 1} \dfrac{k\left(\sin(x - 1)\right)}{x^2 - 1}",
        "point": "1",
        "var": "x",
        "sampler": _sample_sinc_poly_shifted,
        "source_labels": ["I-22"],
    },
    {
        "id": "limit:trig:cos2x_shifted_pi2",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "double_angle",
        "title_km": "ប្តូរអថេរមុំទ្វេត្រង់ π/2 ((1 + cos 2x)/(π/2 - x)²)",
        "title_en": "Double-angle limit at pi/2 ((1 + cos 2x)/(pi/2 - x)^2)",
        "difficulty": "medium",
        "pattern": "{k}*(1 + cos(2*x))/((pi/2) - x)**2",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{2}} \dfrac{k\left(1 + \cos 2x\right)}{\left(\frac{\pi}{2} - x\right)^2}",
        "point": "pi/2",
        "var": "x",
        "sampler": _sample_cos2x_shifted_pi2,
        "source_labels": ["I-23"],
    },
    {
        "id": "limit:trig:tan_tan_product_pi",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ផលគុណតង់សង់ត្រង់ π (tan x · tan(x/2))",
        "title_en": "Tangent product limit at pi (tan x * tan(x/2))",
        "difficulty": "medium",
        "pattern": "{k}*tan(x)*tan(x/2)",
        "pattern_latex": r"\lim_{x \to \pi} k\,\tan x \tan \frac{x}{2}",
        "point": "pi",
        "var": "x",
        "sampler": _sample_tan_tan_product_pi,
        "source_labels": ["I-24"],
    },
    {
        "id": "limit:trig:sin_pi_quad_frac",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ប្តូរអថេរត្រង់ 2 (sin(πx)/(1 - x²/4))",
        "title_en": "Shifted sine over quadratic at 2 (sin(pi x)/(1 - x^2/4))",
        "difficulty": "medium",
        "pattern": "{k}*sin(pi*x)/(1 - x**2/4)",
        "pattern_latex": r"\lim_{x \to 2} \dfrac{k\,\sin \pi x}{1 - \frac{x^2}{4}}",
        "point": "2",
        "var": "x",
        "sampler": _sample_sin_pi_quad_frac,
        "source_labels": ["I-25"],
    },
    {
        "id": "limit:trig:cos2x_factor_diff_pi4",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "double_angle",
        "title_km": "បំបែកមុំទ្វេកូស៊ីនុស ((sin x - cos x)/cos 2x)",
        "title_en": "Factoring double-angle cos 2x ((sin x - cos x)/cos 2x)",
        "difficulty": "medium",
        "pattern": "{k}*(sin(x) - cos(x))/cos(2*x)",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{4}} \dfrac{k\left(\sin x - \cos x\right)}{\cos 2x}",
        "point": "pi/4",
        "var": "x",
        "sampler": _sample_cos2x_factor_diff_pi4,
        "source_labels": ["I-26"],
    },
    {
        "id": "limit:trig:linear_simpson_pi4",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "sum_product",
        "title_km": "ប្តូរអថេរ និងបំប្លែងផលដក ((x - π/4)/(cos x - sin x))",
        "title_en": "Linear over trig difference at pi/4 ((x - pi/4)/(cos x - sin x))",
        "difficulty": "medium",
        "pattern": "{k}*(x - pi/4)/(cos(x) - sin(x))",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{4}} \dfrac{k\left(x - \frac{\pi}{4}\right)}{\cos x - \sin x}",
        "point": "pi/4",
        "var": "x",
        "sampler": _sample_linear_simpson_pi4,
        "source_labels": ["I-27"],
    },
    {
        "id": "limit:trig:sin_shifted_cos_pi3",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ប្តូរអថេរត្រង់ π/3 (2sin(x - π/3)/(1 - 2cos x))",
        "title_en": "Shifted sine over 1 - 2cos x at pi/3",
        "difficulty": "medium",
        "pattern": "{k}*2*sin(x - pi/3)/(1 - 2*cos(x))",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{3}} \dfrac{k\left(2\sin\left(x - \frac{\pi}{3}\right)\right)}{1 - 2\cos x}",
        "point": "pi/3",
        "var": "x",
        "sampler": _sample_sin_shifted_cos_pi3,
        "source_labels": ["I-28"],
    },
    {
        "id": "limit:trig:poly_tan_pi4",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ផលគុណពហុធានិងតង់សង់ ((4 - x²) tan(πx/4))",
        "title_en": "Polynomial tangent product ((4 - x^2) tan(pi x/4)) at 2",
        "difficulty": "medium",
        "pattern": "{k}*(4 - x**2)*tan(pi*x/4)",
        "pattern_latex": r"\lim_{x \to 2} k\,(4 - x^2) \tan \frac{\pi}{4} x",
        "point": "2",
        "var": "x",
        "sampler": _sample_poly_tan_pi4,
        "source_labels": ["I-29"],
    },
    {
        "id": "limit:trig:tan_radical_pi4",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "radical_trig",
        "title_km": "គុណកន្សោមឆ្លាស់និងប្តូរតង់សង់ ((1 - tan x)/(1 - √2 sin x))",
        "title_en": "Tangent and radical conjugate at pi/4",
        "difficulty": "hard",
        "pattern": "{k}*(1 - tan(x))/(1 - sqrt(2)*sin(x))",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{4}} \dfrac{k\left(1 - \tan x\right)}{1 - \sqrt{2}\sin x}",
        "point": "pi/4",
        "var": "x",
        "sampler": _sample_tan_radical_pi4,
        "source_labels": ["I-30"],
    },
    {
        "id": "limit:trig:linear_sin_pi3",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "change_var",
        "title_km": "ប្តូរអថេរត្រង់ π/3 ((π - 3x)/(√3 - 2sin x))",
        "title_en": "Linear over radical sine ((pi - 3x)/(sqrt(3) - 2sin x)) at pi/3",
        "difficulty": "medium",
        "pattern": "{k}*(pi - 3*x)/(sqrt(3) - 2*sin(x))",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{3}} \dfrac{k\left(\pi - 3x\right)}{\sqrt{3} - 2\sin x}",
        "point": "pi/3",
        "var": "x",
        "sampler": _sample_linear_sin_pi3,
        "source_labels": ["I-31"],
    },
    {
        "id": "limit:trig:double_radical_pi4",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "radical_trig",
        "title_km": "គុណកន្សោមឆ្លាស់ពីរជាន់ ((1 - √2 cos x)/(1 - √2 sin x))",
        "title_en": "Double conjugate trig limit at pi/4",
        "difficulty": "hard",
        "pattern": "{k}*(1 - sqrt(2)*cos(x))/(1 - sqrt(2)*sin(x))",
        "pattern_latex": r"\lim_{x \to \frac{\pi} k\,{4}} \dfrac{1 - \sqrt{2}\cos x}{1 - \sqrt{2}\sin x}",
        "point": "pi/4",
        "var": "x",
        "sampler": _sample_double_radical_pi4,
        "source_labels": ["I-32"],
    },
    {
        "id": "limit:trig:cos2x_diff_denom_pi4",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "double_angle",
        "title_km": "សម្រួលមុំទ្វេកូស៊ីនុស (cos 2x / (cos x - sin x))",
        "title_en": "Factoring double-angle cos 2x / (cos x - sin x)",
        "difficulty": "easy",
        "pattern": "{k}*cos(2*x)/(cos(x) - sin(x))",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{4}} \dfrac{k\,\cos 2x}{\cos x - \sin x}",
        "point": "pi/4",
        "var": "x",
        "sampler": _sample_cos2x_diff_denom_pi4,
        "source_labels": ["II-01"],
    },
    {
        "id": "limit:trig:quad_trinomial_sin_pi6",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "quadratic",
        "title_km": "បំបែកត្រីធាដឺក្រេទីពីរនៃស៊ីនុសត្រង់ π/6",
        "title_en": "Quadratic trinomial in sin(x) at pi/6",
        "difficulty": "medium",
        "pattern": "{k}*(2*sin(x)**2 - 3*sin(x) + 1)/(4*sin(x)**2 - 1)",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{6}} \dfrac{k\left(2\sin^2 x - 3\sin x + 1\right)}{4\sin^2 x - 1}",
        "point": "pi/6",
        "var": "x",
        "sampler": _sample_quad_trinomial_sin_pi6,
        "source_labels": ["II-02"],
    },
    {
        "id": "limit:trig:radical_cos2_pi2",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "radical_trig",
        "title_km": "គុណកន្សោមឆ្លាស់ឬសការេចម្រុះត្រីកោណមាត្រ",
        "title_en": "Radical conjugate with trig (sqrt(2) - sqrt(1 + sin x))/cos^2 x",
        "difficulty": "hard",
        "pattern": "{k}*(sqrt(2) - sqrt(1 + sin(x)))/cos(x)**2",
        "pattern_latex": r"\lim_{x \to \frac{\pi} k\,{2}} \dfrac{\sqrt{2} - \sqrt{1 + \sin x}}{\cos^2 x}",
        "point": "pi/2",
        "var": "x",
        "sampler": _sample_radical_cos2_pi2,
        "source_labels": ["II-03"],
    },
    {
        "id": "limit:trig:sin_cos2x_pi6",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "double_angle",
        "title_km": "បំប្លែងមុំទ្វេទៅត្រីធាស៊ីនុស ((2sin x - 1)/(1 - 2cos 2x))",
        "title_en": "Double-angle to sine trinomial (2sin x - 1)/(1 - 2cos 2x)",
        "difficulty": "medium",
        "pattern": "{k}*(2*sin(x) - 1)/(1 - 2*cos(2*x))",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{6}} \dfrac{k\left(2\sin x - 1\right)}{1 - 2\cos 2x}",
        "point": "pi/6",
        "var": "x",
        "sampler": _sample_sin_cos2x_pi6,
        "source_labels": ["II-04"],
    },
    {
        "id": "limit:trig:cos_cos2x_pi3",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "double_angle",
        "title_km": "បំប្លែងមុំទ្វេទៅត្រីធាកូស៊ីនុស ((2cos x - 1)/(2cos 2x + 1))",
        "title_en": "Double-angle to cosine trinomial (2cos x - 1)/(2cos 2x + 1)",
        "difficulty": "medium",
        "pattern": "{k}*(2*cos(x) - 1)/(2*cos(2*x) + 1)",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{3}} \dfrac{k\left(2\cos x - 1\right)}{2\cos 2x + 1}",
        "point": "pi/3",
        "var": "x",
        "sampler": _sample_cos_cos2x_pi3,
        "source_labels": ["II-05"],
    },
    {
        "id": "limit:trig:cos2x_radical_cos_pi3",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "radical_trig",
        "title_km": "កន្សោមឆ្លាស់ឬសការេនៃកូស៊ីនុសត្រង់ π/3",
        "title_en": "Radical cosine conjugate (2cos 2x + 1)/(sqrt(2cos x) - 1)",
        "difficulty": "hard",
        "pattern": "{k}*(2*cos(2*x) + 1)/(sqrt(2*cos(x)) - 1)",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{3}} \dfrac{k\left(2\cos 2x + 1\right)}{\sqrt{2\cos x} - 1}",
        "point": "pi/3",
        "var": "x",
        "sampler": _sample_cos2x_radical_cos_pi3,
        "source_labels": ["II-06"],
    },
    {
        "id": "limit:trig:half_angle_cos2_pi2",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "half_angle",
        "title_km": "កន្សោម (1 - sin x)/cos² x ត្រង់ π/2",
        "title_en": "Factoring (1 - sin x)/cos^2 x at pi/2",
        "difficulty": "easy",
        "pattern": "{k}*(1 - sin(x))/cos(x)**2",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{2}} \dfrac{k\left(1 - \sin x\right)}{\cos^2 x}",
        "point": "pi/2",
        "var": "x",
        "sampler": _sample_half_angle_cos2_pi2,
        "source_labels": ["II-07"],
    },
    {
        "id": "limit:trig:double_angle_combo_pi4",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "double_angle",
        "title_km": "បំប្លែងមុំទ្វេចម្រុះ ((sin 2x - cos 2x - 1)/(sin x - cos x))",
        "title_en": "Mixed double-angle identity at pi/4",
        "difficulty": "medium",
        "pattern": "{k}*(sin(2*x) - cos(2*x) - 1)/(sin(x) - cos(x))",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{4}} \dfrac{k\left(\sin 2x - \cos 2x - 1\right)}{\sin x - \cos x}",
        "point": "pi/4",
        "var": "x",
        "sampler": _sample_double_angle_combo_pi4,
        "source_labels": ["II-08"],
    },
    {
        "id": "limit:trig:radical_cos_sin_pi",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "half_angle",
        "title_km": "ឬសការេកន្លះមុំ √(1 + cos x) / sin x ត្រង់ π",
        "title_en": "Half-angle radical sqrt(1 + cos x)/sin x at pi",
        "difficulty": "hard",
        "pattern": "{k}*sqrt(1 + cos(x))/sin(x)",
        "pattern_latex": r"\lim_{x \to \pi^-} k\,\dfrac{\sqrt{1 + \cos x}}{\sin x}",
        "point": "pi",
        "var": "x",
        "side": "-",
        "sampler": _sample_radical_cos_sin_pi,
        "source_labels": ["II-09"],
    },
    {
        "id": "limit:trig:radical_cos2x_sin2x_pi",
        "question_type": "limit",
        "category": "trig",
        "subfamily": "double_angle",
        "title_km": "ឬសការេមុំទ្វេ √(1 - cos 2x) / sin 2x ត្រង់ π",
        "title_en": "Double-angle radical sqrt(1 - cos 2x)/sin 2x at pi",
        "difficulty": "hard",
        "pattern": "{k}*sqrt(1 - cos(2*x))/sin(2*x)",
        "pattern_latex": r"\lim_{x \to \pi^-} k\,\dfrac{\sqrt{1 - \cos 2x}}{\sin 2x}",
        "point": "pi",
        "var": "x",
        "side": "-",
        "sampler": _sample_radical_cos2x_sin2x_pi,
        "source_labels": ["II-10"],
    },
]
