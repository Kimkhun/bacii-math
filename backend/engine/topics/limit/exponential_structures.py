"""Exponential and Euler 1^infinity limit structures registry matching textbook exercises.

Contains authentic exponential and Euler limit structures with:
- semantic IDs
- authentic textbook labels ['exp_01'], ['one_inf_01'], etc.
- deterministic SymPy closed-form samplers
- authentic Khmer titles (no fake code abbreviations)
"""
import random

def _sample_expo_diff_ratio(rng):
    a = rng.choice([2, 3, 4, 5])
    b = rng.choice([1, 2, 3])
    while a == b:
        b = rng.choice([1, 2, 3])
    return f"(e**({a}*x) - e**({b}*x))/x", "0", {"a": a, "b": b}

def _sample_expo_standard_single(rng):
    k = rng.choice([2, 3, 4, 5])
    return f"(e**({k}*x) - 1)/x", "0", {"k": k}

def _sample_expo_den_multiplier(rng):
    a = rng.choice([2, 3, 4])
    b = rng.choice([2, 3, 5, 6])
    return f"(e**({a}*x) - 1)/({b}*x)", "0", {"a": a, "b": b}

def _sample_expo_symmetric_diff(rng):
    a = rng.choice([2, 3, 4])
    return f"(e**({a}*x) - e**(-{a}*x))/x", "0", {"a": a}

def _sample_expo_trig_sinc(rng):
    a = rng.choice([2, 3, 4])
    b = rng.choice([1, 2])
    return f"(e**({a}*x) - e**({b}*x))/sin(x)", "0", {"a": a, "b": b}

def _sample_expo_linear_add(rng):
    a = rng.choice([2, 3, 4])
    b = rng.choice([1, 2, 3])
    return f"(e**({a}*x) + {b}*x - 1)/x", "0", {"a": a, "b": b}

def _sample_expo_trinomial(rng):
    k = rng.choice([1, 2])
    return f"{k}*(2*e**(2*x) - 3*e**x + 1)/x" if k != 1 else "(2*e**(2*x) - 3*e**x + 1)/x", "0", {"k": k}

def _sample_expo_second_order(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(e**x + e**(-x) - 2)/x**2" if k != 1 else "(e**x + e**(-x) - 2)/x**2", "0", {"k": k}

def _sample_expo_tan_sinc(rng):
    k = rng.choice([1, 2])
    denom = f"{k}*(x**3 + x)" if k != 1 else "(x**3 + x)"
    return f"(e**(-2*sin(x)) - e**tan(x))/{denom}", "0", {"k": k}

def _sample_expo_cos_combo(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*(e**(-x**2) - cos(2*x))/x**2" if k != 1 else "(e**(-x**2) - cos(2*x))/x**2", "0", {"k": k}

def _sample_expo_sin_denom(rng):
    k = rng.choice([1, 2])
    return f"(e**({k}*x) - e**(-{k}*x))/sin(2*x)", "0", {"k": k}

def _sample_expo_sum_minus_n(rng):
    n = rng.choice([2, 3, 4])
    return f"(e**x + e**(2*x) + e**({n}*x) - {n})/x", "0", {"n": n}

def _sample_expo_power_growth_oo(rng):
    n = rng.choice([1, 2, 3])
    return f"e**x/x**{n}", "oo", {"n": n}

def _sample_expo_neg_inf(rng):
    k = rng.choice([1, 2, 3])
    return f"{k}*e**x" if k != 1 else "e**x", "-oo", {"k": k}

def _sample_expo_linear_growth_oo(rng):
    a = rng.choice([2, 3])
    return f"e**({a}*x) - x", "oo", {"a": a}

def _sample_euler_rational_base(rng):
    k = rng.choice([1, 2, 3, 4])
    return f"((x + {k})/x)**x", "oo", {"k": k}

def _sample_euler_fraction_base(rng):
    a = rng.choice([1, 2])
    b = rng.choice([2, 3, 4])
    return f"((x - {a})/(x + {b}))**x", "oo", {"a": a, "b": b}

def _sample_euler_zero_linear(rng):
    a = rng.choice([2, 3, 4])
    return f"(1 + {a}*x)**(1/x)", "0", {"a": a}

def _sample_euler_zero_rational_power(rng):
    a = rng.choice([2, 3])
    b = rng.choice([2, 3])
    return f"(1 - {a}*x)**({b}/x)", "0", {"a": a, "b": b}

def _sample_euler_sin_zero(rng):
    k = rng.choice([1, 2, 3])
    return f"(1 + sin({k}*x))**(1/x)", "0", {"k": k}

def _sample_euler_cos_zero(rng):
    k = rng.choice([1, 2])
    return f"(cos({k}*x))**(1/x**2)", "0", {"k": k}

def _sample_euler_cos_pi2(rng):
    k = rng.choice([1, 2])
    return f"(1 + {k}*cos(x))**(1/(x - pi/2))", "pi/2", {"k": k}


EXPONENTIAL_STRUCTURES = [
    {
        "id": "limit:exponential:diff_ratio",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "zero",
        "title_km": "ផលដកអិចស្ប៉ូណង់ស្យែលត្រង់ 0 ((eᵃˣ - eᵇˣ)/x)",
        "title_en": "Difference of exponentials at 0",
        "difficulty": "medium",
        "pattern": "(e**({a}*x) - e**({b}*x))/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{e^{a x} - e^{b x}}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_diff_ratio,
        "source_labels": ["exp_01"],
    },
    {
        "id": "limit:exponential:standard_single",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "zero",
        "title_km": "លីមីតគ្រឹះ (eᵏˣ - 1)/x",
        "title_en": "Standard exponential limit (e^{kx} - 1)/x",
        "difficulty": "easy",
        "pattern": "(e**({k}*x) - 1)/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{e^{k x} - 1}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_standard_single,
        "source_labels": ["exp_02"],
    },
    {
        "id": "limit:exponential:den_multiplier",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "zero",
        "title_km": "ផលធៀបអិចស្ប៉ូណង់ស្យែលលើ bx",
        "title_en": "Exponential limit over bx",
        "difficulty": "easy",
        "pattern": "(e**({a}*x) - 1)/({b}*x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{e^{a x} - 1}{b x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_den_multiplier,
        "source_labels": ["exp_03"],
    },
    {
        "id": "limit:exponential:symmetric_diff",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "zero",
        "title_km": "ផលដកស៊ីមេទ្រី (eᵃˣ - e⁻ᵃˣ)/x",
        "title_en": "Symmetric exponential difference (e^{ax} - e^{-ax})/x",
        "difficulty": "medium",
        "pattern": "(e**({a}*x) - e**(-{a}*x))/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{e^{a x} - e^{-a x}}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_symmetric_diff,
        "source_labels": ["exp_04"],
    },
    {
        "id": "limit:exponential:trig_sinc",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "trig_combo",
        "title_km": "អិចស្ប៉ូណង់ស្យែលចម្រុះស៊ីនុស ((eᵃˣ - eᵇˣ)/sin x)",
        "title_en": "Exponential difference over sine",
        "difficulty": "medium",
        "pattern": "(e**({a}*x) - e**({b}*x))/sin(x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{e^{a x} - e^{b x}}{\sin x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_trig_sinc,
        "source_labels": ["exp_05"],
    },
    {
        "id": "limit:exponential:linear_add",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "zero",
        "title_km": "អិចស្ប៉ូណង់ស្យែលបូកលីនេអ៊ែរ ((eᵃˣ + bx - 1)/x)",
        "title_en": "Exponential with linear term (e^{ax} + bx - 1)/x",
        "difficulty": "medium",
        "pattern": "(e**({a}*x) + {b}*x - 1)/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{e^{a x} + b x - 1}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_linear_add,
        "source_labels": ["exp_06"],
    },
    {
        "id": "limit:exponential:quad_trinomial",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "zero",
        "title_km": "ត្រីធាអិចស្ប៉ូណង់ស្យែលត្រង់ 0",
        "title_en": "Quadratic trinomial in e^x at 0",
        "difficulty": "medium",
        "pattern": "{k}*(2*e**(2*x) - 3*e**x + 1)/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{k\left(2e^{2x} - 3e^{x} + 1\right)}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_trinomial,
        "source_labels": ["exp_07"],
    },
    {
        "id": "limit:exponential:second_order",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "zero",
        "title_km": "លីមីតអិចស្ប៉ូណង់ស្យែលដឺក្រេពីរ ((eˣ + e⁻ˣ - 2)/x²)",
        "title_en": "Second-order exponential limit (e^x + e^{-x} - 2)/x^2",
        "difficulty": "hard",
        "pattern": "{k}*(e**x + e**(-x) - 2)/x**2",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{k\left(e^{x} + e^{-x} - 2\right)}{x^{2}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_second_order,
        "source_labels": ["exp_08"],
    },
    {
        "id": "limit:exponential:tan_sinc",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "trig_combo",
        "title_km": "អិចស្ប៉ូណង់ស្យែលចម្រុះតង់សង់និងស៊ីនុស",
        "title_en": "Exponential mixed with tangent and sine",
        "difficulty": "hard",
        "pattern": "(e**(-2*sin(x)) - e**tan(x))/({k}*(x**3 + x))",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{e^{-2\sin x} - e^{\tan x}}{k\left(x^{3} + x\right)}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_tan_sinc,
        "source_labels": ["exp_10"],
    },
    {
        "id": "limit:exponential:cos_combo",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "trig_combo",
        "title_km": "អិចស្ប៉ូណង់ស្យែលចម្រុះកូស៊ីនុស ((e⁻ˣ² - cos 2x)/x²)",
        "title_en": "Exponential mixed with cosine (e^{-x^2} - cos 2x)/x^2",
        "difficulty": "hard",
        "pattern": "{k}*(e**(-x**2) - cos(2*x))/x**2",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{k\left(e^{-x^{2}} - \cos 2x\right)}{x^{2}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_cos_combo,
        "source_labels": ["exp_11"],
    },
    {
        "id": "limit:exponential:sin_denom",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "trig_combo",
        "title_km": "ផលដកអិចស្ប៉ូណង់ស្យែលលើស៊ីនុសមុំទ្វេ",
        "title_en": "Exponential difference over double-angle sine",
        "difficulty": "medium",
        "pattern": "(e**({k}*x) - e**(-{k}*x))/sin(2*x)",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{e^{k x} - e^{-k x}}{\sin 2x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_sin_denom,
        "source_labels": ["exp_12"],
    },
    {
        "id": "limit:exponential:sum_minus_n",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "zero",
        "title_km": "ផលបូកអិចស្ប៉ូណង់ស្យែលដកចំនួនថេរ ((∑ eᵏˣ - n)/x)",
        "title_en": "Sum of exponentials minus n over x",
        "difficulty": "hard",
        "pattern": "(e**x + e**(2*x) + e**(3*x) - 3)/x",
        "pattern_latex": r"\lim_{x \to 0} \dfrac{e^{x} + e^{2x} + \dots + e^{nx} - n}{x}",
        "point": "0",
        "var": "x",
        "sampler": _sample_expo_sum_minus_n,
        "source_labels": ["exp_13"],
    },
    {
        "id": "limit:exponential:power_growth_oo",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "infinity",
        "title_km": "លំដាប់កំណើនអិចស្ប៉ូណង់ស្យែលនៅ +∞ (eˣ/xⁿ)",
        "title_en": "Exponential growth dominance at +infinity (e^x / x^n)",
        "difficulty": "medium",
        "pattern": "e**x/x**{n}",
        "pattern_latex": r"\lim_{x \to +\infty} \dfrac{e^{x}}{x^{n}}",
        "point": "oo",
        "var": "x",
        "sampler": _sample_expo_power_growth_oo,
        "source_labels": ["exp_20"],
    },
    {
        "id": "limit:exponential:neg_inf",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "infinity",
        "title_km": "លីមីតអិចស្ប៉ូណង់ស្យែលនៅ -∞ (eˣ → 0)",
        "title_en": "Exponential limit at -infinity (e^x -> 0)",
        "difficulty": "easy",
        "pattern": "{k}*e**x",
        "pattern_latex": r"\lim_{x \to -\infty} k e^{x}",
        "point": "-oo",
        "var": "x",
        "sampler": _sample_expo_neg_inf,
        "source_labels": ["exp_21"],
    },
    {
        "id": "limit:exponential:linear_growth_oo",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "infinity",
        "title_km": "ផលដកអិចស្ប៉ូណង់ស្យែលនិងពហុធានៅ +∞ (eᵃˣ - x)",
        "title_en": "Difference of exponential and linear at +infinity",
        "difficulty": "medium",
        "pattern": "e**({a}*x) - x",
        "pattern_latex": r"\lim_{x \to +\infty} (e^{a x} - x)",
        "point": "oo",
        "var": "x",
        "sampler": _sample_expo_linear_growth_oo,
        "source_labels": ["exp_25"],
    },
    # Euler 1^infinity forms
    {
        "id": "limit:euler:rational_base",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "one_inf",
        "title_km": "រាងមិនកំណត់ 1^អនន្ត (ប្រភាគសនិទាន ((x+k)/x)ˣ)",
        "title_en": "Indeterminate form 1^infinity (rational base ((x+k)/x)^x)",
        "difficulty": "hard",
        "pattern": "((x + {k})/x)**x",
        "pattern_latex": r"\lim_{x \to +\infty} \left(\dfrac{x + k}{x}\right)^{x}",
        "point": "oo",
        "var": "x",
        "sampler": _sample_euler_rational_base,
        "source_labels": ["one_inf_01"],
    },
    {
        "id": "limit:euler:fraction_base",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "one_inf",
        "title_km": "រាងមិនកំណត់ 1^អនន្ត (((x-a)/(x+b))ˣ)",
        "title_en": "Indeterminate form 1^infinity (((x-a)/(x+b))^x)",
        "difficulty": "hard",
        "pattern": "((x - {a})/(x + {b}))**x",
        "pattern_latex": r"\lim_{x \to +\infty} \left(\dfrac{x - a}{x + b}\right)^{x}",
        "point": "oo",
        "var": "x",
        "sampler": _sample_euler_fraction_base,
        "source_labels": ["one_inf_02"],
    },
    {
        "id": "limit:euler:zero_linear",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "one_inf",
        "title_km": "រាងមិនកំណត់ 1^អនន្តត្រង់ 0 ((1 + ax)^(1/x))",
        "title_en": "Indeterminate form 1^infinity at 0 ((1 + ax)^(1/x))",
        "difficulty": "medium",
        "pattern": "(1 + {a}*x)**(1/x)",
        "pattern_latex": r"\lim_{x \to 0} (1 + a x)^{\frac{1}{x}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_euler_zero_linear,
        "source_labels": ["one_inf_03"],
    },
    {
        "id": "limit:euler:zero_rational_power",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "one_inf",
        "title_km": "រាងមិនកំណត់ 1^អនន្តត្រង់ 0 ((1 - ax)^(b/x))",
        "title_en": "Indeterminate form 1^infinity at 0 ((1 - ax)^(b/x))",
        "difficulty": "medium",
        "pattern": "(1 - {a}*x)**({b}/x)",
        "pattern_latex": r"\lim_{x \to 0} (1 - a x)^{\frac{b}{x}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_euler_zero_rational_power,
        "source_labels": ["one_inf_04"],
    },
    {
        "id": "limit:euler:sin_zero",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "one_inf",
        "title_km": "រាងមិនកំណត់ 1^អនន្តចម្រុះស៊ីនុស ((1 + sin x)^(1/x))",
        "title_en": "Indeterminate form 1^infinity with sine ((1 + sin x)^(1/x))",
        "difficulty": "hard",
        "pattern": "(1 + sin({k}*x))**(1/x)",
        "pattern_latex": r"\lim_{x \to 0} (1 + \sin kx)^{\frac{1}{x}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_euler_sin_zero,
        "source_labels": ["one_inf_05"],
    },
    {
        "id": "limit:euler:cos_zero",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "one_inf",
        "title_km": "រាងមិនកំណត់ 1^អនន្តចម្រុះកូស៊ីនុស ((cos x)^(1/x²))",
        "title_en": "Indeterminate form 1^infinity with cosine ((cos x)^(1/x^2))",
        "difficulty": "hard",
        "pattern": "(cos({k}*x))**(1/x**2)",
        "pattern_latex": r"\lim_{x \to 0} (\cos kx)^{\frac{1}{x^{2}}}",
        "point": "0",
        "var": "x",
        "sampler": _sample_euler_cos_zero,
        "source_labels": ["one_inf_06"],
    },
    {
        "id": "limit:euler:cos_pi2",
        "question_type": "limit",
        "category": "exponential",
        "subfamily": "one_inf",
        "title_km": "រាងមិនកំណត់ 1^អនន្តត្រង់ π/2 ((1 + cos x)^(1/(x - π/2)))",
        "title_en": "Indeterminate form 1^infinity at pi/2",
        "difficulty": "hard",
        "pattern": "(1 + {k}*cos(x))**(1/(x - pi/2))",
        "pattern_latex": r"\lim_{x \to \frac{\pi}{2}} (1 + k\cos x)^{\frac{1}{x - \frac{\pi}{2}}}",
        "point": "pi/2",
        "var": "x",
        "sampler": _sample_euler_cos_pi2,
        "source_labels": ["one_inf_07"],
    },
]
