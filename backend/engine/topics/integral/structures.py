"""Parameterized integral structure registry.

The single authoritative list of every integral template structure the engine
knows about — both the shapes the live generator emits and the parameterized
templates derived from the 124 BAC II integral exercises (so every exercise has
a structure it maps to). Used by:

- the admin `/templates/structures` endpoint (pattern + one filled sample per
  structure), and
- `scripts/verify_integral_structures.py` (solve + grade every structure).

This module deliberately imports only SymPy (and this topic's own
``solver.py``, which also only imports SymPy) so the host verify script can
load it without the Google LLM client dependencies.

The template pool constants here (``_INDEFINITE_TEMPLATES`` and friends) are
also imported by ``generator.py`` for live generation — one source of truth.
The slot/fill machinery itself (``fill_structured``, ``fill_bound``) lives in
``engine.core.slots``, shared with the ``limit`` topic's generator.
"""
import random

from sympy import E, Integral, N, Symbol, latex, oo, pi, sqrt, sympify, zoo

from ...core.slots import _SLOT_NAMES, fill_bound, fill_structured
from .solver import _solve_definite_integral, _solve_indefinite_integral

# ---------------------------------------------------------------------------
# The 15 curated Part-I shapes (the first 15 BAC II exercises). These mirror
# generator._INDEFINITE_TEMPLATES — the source labels are the photo numbers.
# ---------------------------------------------------------------------------
_INDEFINITE_TEMPLATES = [
    ("easy", ["{a}*x**2 + {b}*x + {c}", "x"]),
    ("easy", ["(1/2)*x**2 + {b}*x + {c}", "x"]),
    ("easy", ["{a}*x**3 + {b}*x**2 + {c}*x + {d}", "x"]),
    ("medium", ["{a}*x - {b}/x + e**x", "x"]),
    ("medium", ["({f})*e**x + {a}*x*sqrt(x)", "x"]),
    ("medium", ["{b}/x - {a}*e**x + e**2", "x"]),
    ("medium", ["1/({k}*x) - {b}/(2*x**2) + sqrt(5)", "x"]),
    ("medium", ["{b}/x + {d}/x**2 - {a}/sqrt(x)", "x"]),
    ("hard", ["{a}*sqrt(x) + {b}/x**3 + {c}*sin(x)", "x"]),
    ("hard", ["sqrt(x**3) - {b}/(2*sqrt(x)) + ln(3)", "x"]),
    ("hard", ["{a}*cos(x) + {b}*sin(x) - e", "x"]),
    ("hard", ["{a}*cos(t) - {b}*e**t + t/{k}", "t"]),
    ("hard", ["ln(2) + {a}*e**t - {b}*sin(t)", "t"]),
    ("hard", ["({f})*y**3 + {b}/(4*y) - pi", "y"]),
    ("hard", ["{d}/(3*sqrt(y)) + {b}/y**3 + {c}/y", "y"]),
]

# Indefinite "expand the product" shapes (Part I: x(x²+x−2), (2x+3)(x−4), ...)
_INDEF_EXPAND_TEMPLATES = [
    "{a}*{v}*({b}*{v}**2 + {c}*{v} - {d})",
    "{a}*{v}**2*({b}*{v} + {c})",
    "({a}*{v} + {b})*({c}*{v} - {d})",
    "({a}*{v} - {b})**2",
    "({a}*{v} + {b})*({a}*{v} - {b})",
    "{a}*{v}*({b}*{v} + {c})**2",
    "({a}*{v} - {b})*({c} - {d}*{v})",
]

# Indefinite "split the fraction" shapes (Part I: (2x²+3x−4)/x, ...)
_INDEF_SPLIT_TEMPLATES = [
    "({a}*{v}**2 + {b}*{v} - {c})/{v}",
    "({a}*{v}**3 - {b}*{v}**2 + {c}*{v} + {d})/({k}*{v}**2)",
    "({a}*{v}**3 + {b}*{v} - {c})/sqrt({v})",
    "({a}*{v}**3 - {b}*{v}**2 + {c}*{v})/{v}**3",
    "({a}*{v}**2 + {b}*{v} - {c})/({k}*{v})",
    "({a}*{v}**2*sin({v}) - sqrt({v}) + {b}*{v}**3)/{v}**2",
]

# Indefinite u-substitution shapes (Part II). Each is exactly u'·f(u).
_INDEF_USUB_TEMPLATES = [
    ("power", "{a}*{v}*({b}*{v}**2 + {c})**{n}"),
    ("recip", "{a}*{v}/({b}*{v}**2 + {c})"),
    ("exp", "{a}*{v}*e**({b}*{v}**2 + {c})"),
    ("sin", "{a}*{v}*sin({b}*{v}**2 + {c})"),
    ("cos", "{a}*{v}*cos({b}*{v}**2 + {c})"),
    ("sqrt", "{a}*{v}/sqrt({b}*{v}**2 + {c})"),
    ("cuberoot", "{a}*{v}*({b}*{v}**2 - {c})**(1/3)"),
    ("quad_pow", "({a} + 2*{v})*({v}**2 + {a}*{v} + {c})**{n}"),
    ("quad_recip", "({a} + 2*{v})/({v}**2 + {a}*{v} + {c})"),
    ("quad_sqrt", "({a} + 2*{v})/sqrt({v}**2 + {a}*{v} + {c})"),
    ("ln_pow", "ln({v})**{n}/{v}"),
    ("ln_recip", "1/({v}*ln({v}))"),
    ("ln_recip3", "1/({v}*ln({v})**3)"),
    ("tpow_sin", "sin({v})*cos({v})**{n}"),
    ("tpow_cos", "cos({v})*sin({v})**{n}"),
    ("sqrt_sinx", "cos({v})/sqrt(sin({v}) + {c})"),
    ("sqrt_cubic", "({a} + 3*{v}**2)/sqrt({v}**3 + {a}*{v} + {c})"),
    ("e_recip", "e**{v}/({a}*e**{v} + {b})"),
    ("e_pow2", "e**(2*{v})/(2*e**(2*{v}) - {b})**2"),
    ("negpow", "{a}*{v}/({b}*{v}**2 + {c})**{n}"),
    ("quad_negpow", "({a} + 2*{v})/({v}**2 + {a}*{v} + {c})**{n}"),
    ("esqrt", "{a}*e**(-{v})/sqrt({b}*e**(-{v}) + {c})"),
    ("mix2", "{a}*{v}**2*sin({v}**3) - {a}*{v}*cos({v}**2)"),
    ("ln_mix", "{a}*ln({v})/{v} + {b}/({v}*ln({v})) - {c}/({v}*ln({v})**3)"),
]

# Indefinite linear-argument shapes (Part II: sin(kx), (2+x)⁸, 4/(3−2t)⁵, ...)
_INDEF_LINEAR_TEMPLATES = [
    "{a}*sin({k}*{v})",
    "{a}*cos({k}*{v})",
    "{a}*e**({k}*{v})",
    "({k}*{v} + {b})**{n}",
    "1/({k}*{v} + {b})",
    "1/({k}*{v} - {b})**{n}",
    "{a}*cos({k}*{v} + {b})",
    "e**({k}*{v} + {b})",
    "{v} + {a}/({v} - {b}) - {c}/({v} + {d})",
    "{a}*{v} + {b} - {c}/({v} + {d}) + {g}/({v} + {d})**2",
]

# Indefinite trig-identity square (Part I: (tan x + cot x)²)
_INDEF_TRIG_SQ_TEMPLATES = [
    "{a}*(tan({v}) + cot({v}))**2",
]


def _entry(qt, variant, difficulty, pattern, var="x", bounds=None, labels=(), sid=None):
    return {
        "id": sid,
        "question_type": qt,
        "variant": variant,
        "difficulty": difficulty,
        "pattern": pattern,
        "var": var,
        "bounds": bounds,
        "source_labels": list(labels),
    }


_IND = "indefinite_integral"
_DEF = "definite_integral"


def _indef_structures():
    expand_labels = {1: ["I23"], 2: ["I24"], 3: ["I26"], 4: ["I28"]}
    split_labels = {1: ["I31"], 2: ["I32"], 3: ["I33"], 4: ["I35"], 6: ["I36"]}
    usub_labels = {
        "power": ["II1"],
        "exp": ["II8"],
        "quad_recip": ["II12", "II23"],
        "ln_pow": ["II13"],
        "tpow_sin": ["II14"],
        "cuberoot": ["II16"],
        "recip": ["II21"],
        "e_recip": ["II25"],
        "quad_negpow": ["II27"],
        "e_pow2": ["II29"],
        "ln_mix": ["II32"],
        "sqrt_sinx": ["II34"],
        "sqrt": ["II35"],
    }
    linear_labels = {1: ["II5"], 2: ["II3"], 4: ["II2"], 9: ["II26"], 10: ["II30"]}
    structs = []
    for i, (diff, (tpl, var)) in enumerate(_INDEFINITE_TEMPLATES, 1):
        structs.append(_entry(_IND, "indefinite_sum", diff, tpl, var=var,
                              labels=[f"curated-{i}"], sid=f"curated_{i}"))
    for i, tpl in enumerate(_INDEF_EXPAND_TEMPLATES, 1):
        structs.append(_entry(_IND, "expand", "easy", tpl,
                              labels=expand_labels.get(i, []), sid=f"expand_{i}"))
    for i, tpl in enumerate(_INDEF_SPLIT_TEMPLATES, 1):
        structs.append(_entry(_IND, "split", "medium", tpl,
                              labels=split_labels.get(i, []), sid=f"split_{i}"))
    for key, tpl in _INDEF_USUB_TEMPLATES:
        structs.append(_entry(_IND, "usub", "hard", tpl,
                              labels=usub_labels.get(key, []), sid=f"usub_{key}"))
    for i, tpl in enumerate(_INDEF_LINEAR_TEMPLATES, 1):
        structs.append(_entry(_IND, "linear_argument", "medium", tpl,
                              labels=linear_labels.get(i, []), sid=f"linear_{i}"))
    for i, tpl in enumerate(_INDEF_TRIG_SQ_TEMPLATES, 1):
        structs.append(_entry(_IND, "trig_sec", "hard", tpl,
                              labels=["I38"] if i == 1 else [], sid=f"trig_sq_{i}"))
    return structs


# ---------------------------------------------------------------------------
# Source-derived labels (the 109 transcribed exercises). The 2 broken source
# exercises (III-30 complex answer, III-34 nan) are excluded from every
# structure and noted only in the audit.
# ---------------------------------------------------------------------------
_SRC_EXCLUDED = {"III-30", "III-34"}


def _new_indef_structures():
    return [
        _entry(_IND, "power", "easy", "{a}/{v} + {b}*sin({v}) + {c}*cos({v})",
               labels=["I16"], sid="ind_basics_recip_trig"),
        _entry(_IND, "power", "easy", "{a}/{v} + {b}/{v}**2 + {c}*e**{v} - {d}*sin({v})",
               labels=["I17"], sid="ind_basics_mix4"),
        _entry(_IND, "power", "medium", "({f})*cos({v}) - ({g})*e + {a}/{v} - {v}*ln({c})",
               labels=["I18"], sid="ind_basics_const_mix"),
        _entry(_IND, "power", "easy", "{v}**(2/3) + ({f})/sqrt({v}) + {c}*{v}*ln({d})",
               labels=["I19"], sid="ind_basics_frac_pow"),
        _entry(_IND, "power", "easy", "{v}**(1/3) + {v}*{v}**(2/3) - {a}*e**{v}",
               labels=["I20"], sid="ind_basics_frac_pow2"),
        _entry(_IND, "power", "medium", "{a}/cos({v})**2 - {c}*e**{v} + {b}/sqrt({v})",
               labels=["I21"], sid="ind_basics_sec_exp_sqrt"),
        _entry(_IND, "power", "medium", "{a}/cos({v})**2 - {b}/sin({v})**2 + {c}*e**{v}",
               labels=["I22"], sid="ind_basics_sec_csc_exp"),
        _entry(_IND, "expand", "easy", "{v}*(sqrt({v}) + {v} + {a}/{v})",
               labels=["I25"], sid="ind_expand_sqrt"),
        _entry(_IND, "expand", "easy", "({a}*{v} - {b}*{v}**2)*({c}*{v} + {d})",
               labels=["I27"], sid="ind_expand_quad"),
        _entry(_IND, "expand", "easy", "({a}*{v} + {b})*({c} - {d}*{v})",
               labels=["I29"], sid="ind_expand_opposite"),
        _entry(_IND, "expand", "easy", "-{a}*{v}*({b}*{v} + {c})**2",
               labels=["I30"], sid="ind_expand_neg_sq"),
        _entry(_IND, "split", "medium", "({v}*e**{v} + ln({c}) - {v}*cos({v}))/{v}",
               labels=["I34"], sid="ind_split_exp_trig"),
        _entry(_IND, "power", "medium", "{a}/sin({v})**2 - {b}/cos({v})**2",
               labels=["I37"], sid="ind_basics_csc_sec"),
        # Part II — new shapes not covered by the existing usub/linear lists.
        _entry(_IND, "usub", "hard", "({a} + 2*{k}*{v})*cos({k}*{v}**2 + {a}*{v})",
               labels=["II4"], sid="ind_quad_cos"),
        _entry(_IND, "usub", "hard", "({a} + 2*{k}*{v})*sin({k}*{v}**2 + {a}*{v} - {c})",
               labels=["II6"], sid="ind_quad_sin"),
        _entry(_IND, "linear_argument", "medium", "e**({k}*{v}) + {a}*sin({k}*{v}) - {b}*cos({s}*{v})",
               labels=["II7"], sid="ind_linear_mix_exp"),
        _entry(_IND, "linear_argument", "medium", "e**(-{f}*{v}) - {a}*sin({k}*{v})",
               labels=["II9"], sid="ind_linear_mix_negexp"),
        _entry(_IND, "linear_argument", "medium", "-{a}*cos({k}*{v} + {b})",
               labels=["II10"], sid="ind_linear_neg_cos"),
        _entry(_IND, "usub", "hard", "(cos({v}) - sin({v}))*(sin({v}) + cos({v}))**{n}",
               labels=["II11"], sid="ind_usub_trig_mix"),
        _entry(_IND, "usub", "hard", "({a} + 2*{v})*sqrt({v}**2 + {a}*{v} - {c})",
               labels=["II15"], sid="ind_quad_sqrt_pow"),
        _entry(_IND, "usub", "hard", "sin({v})*({c} - cos({v}))**{n}",
               labels=["II18"], sid="ind_usub_cos_shift"),
        _entry(_IND, "usub", "hard", "({f})*({a} + 2*{v})/({v}**2 + {a}*{v} - {c})",
               labels=["II22"], sid="ind_quad_recip_frac"),
        _entry(_IND, "usub", "hard", "(cos({v}) - sin({v}))/(sin({v}) + cos({v}))",
               labels=["II24"], sid="ind_usub_trig_frac"),
        _entry(_IND, "linear_argument", "hard", "{a}/({b} - {k}*{v})**{n}",
               labels=["II28"], sid="ind_linear_recip_negpow"),
        _entry(_IND, "usub", "hard", "-{a}*{v} + {b} + {c}/({v}*ln({v})**{n})",
               labels=["II31"], sid="ind_linear_ln_mix"),
        _entry(_IND, "usub", "hard", "(2*{v} - {a})/sqrt({v}**2 - {a}*{v} + {c})",
               labels=["II36"], sid="ind_quad_sqrt_neg"),
        _entry(_IND, "usub", "hard", "{a}/({v}*sqrt({b} + ln({v})))",
               labels=["II37"], sid="ind_ln_sqrt_recip"),
        _entry(_IND, "usub", "hard", "-{a}*e**(-{v})/sqrt({b}*e**(-{v}) + {c})",
               labels=["II38"], sid="ind_esqrt_neg"),
        # Part II — near-duplicates of existing usub shapes (kept as separate
        # structures so the live generator's own templates stay untouched).
        _entry(_IND, "usub", "hard", "{a}*{v}**2*sin({v}**3) - {b}*{v}*cos({v}**2)",
               labels=["II17"], sid="usub_mix2b"),
        _entry(_IND, "usub", "hard", "{a}*sin({v})*cos({v})**{n}",
               labels=["II19"], sid="usub_tpow_sin_coef"),
        _entry(_IND, "usub", "hard", "{a}*cos({v})*sin({v})**{n}",
               labels=["II20"], sid="usub_tpow_cos_coef"),
        _entry(_IND, "usub", "hard", "({a} + 3*{v}**2)/sqrt({v}**3 + {a}*{v} - {c})",
               labels=["II33"], sid="usub_sqrt_cubic_neg"),
    ]


# ---------------------------------------------------------------------------
# Definite structures — existing shapes from generator._generate_integral.
# ---------------------------------------------------------------------------
def _def_structures():
    return [
        _entry(_DEF, "polynomial", "easy", "{a}*{v}**2 + {b}*{v} + {c}",
               bounds=[("0", "1"), ("1", "2"), ("-1", "0"), ("-2", "-1")],
               labels=["III-1", "III-4"], sid="def_poly"),
        _entry(_DEF, "trig", "hard", "{a}*sin({v})",
               bounds=[("0", "pi/2"), ("0", "pi/3")], sid="def_trig_sin"),
        _entry(_DEF, "trig", "hard", "{a}*cos({v})",
               bounds=[("0", "pi/2"), ("0", "pi/6")], sid="def_trig_cos"),
        _entry(_DEF, "linear_argument", "medium", "sin({k}*{v})",
               bounds=[("0", "pi/(2*{k})")], sid="def_linarg_sin"),
        _entry(_DEF, "linear_argument", "medium", "cos({k}*{v})",
               bounds=[("0", "pi/(2*{k})")], sid="def_linarg_cos"),
        _entry(_DEF, "linear_argument", "medium", "e**({k}*{v} + {b})",
               bounds=[("0", "1")], sid="def_linarg_exp"),
        _entry(_DEF, "linear_argument", "medium", "({k}*{v} + {b})**{n}",
               bounds=[("0", "1")], labels=["III-16"], sid="def_linarg_power"),
        _entry(_DEF, "linear_argument", "medium", "1/({k}*{v} + {b})",
               bounds=[("0", "1")], sid="def_linarg_recip"),
        _entry(_DEF, "linear_argument", "medium", "1/sqrt({k}*{v} + {b})",
               bounds=[("0", "1")], sid="def_linarg_sqrt"),
        # u-substitution (degree-2 and degree-3 inner shapes).
        _entry(_DEF, "u_substitution", "hard", "2*{v}*({v}**2 + {c})**{n}",
               bounds=[("0", "1")], labels=["III-13"], sid="def_usub_power2"),
        _entry(_DEF, "u_substitution", "hard", "3*{v}**2*({v}**3 + {c})**{n}",
               bounds=[("0", "1")], sid="def_usub_power3"),
        _entry(_DEF, "u_substitution", "hard", "2*{v}/({v}**2 + {c})",
               bounds=[("0", "1")], sid="def_usub_recip2"),
        _entry(_DEF, "u_substitution", "hard", "3*{v}**2/({v}**3 + {c})",
               bounds=[("0", "1")], sid="def_usub_recip3"),
        _entry(_DEF, "u_substitution", "hard", "2*{v}*e**({v}**2 + {c})",
               bounds=[("0", "1")], sid="def_usub_exp2"),
        _entry(_DEF, "u_substitution", "hard", "3*{v}**2*e**({v}**3 + {c})",
               bounds=[("0", "1")], sid="def_usub_exp3"),
        _entry(_DEF, "u_substitution", "hard", "2*{v}*sin({v}**2 + {c})",
               bounds=[("0", "1")], sid="def_usub_sin2"),
        _entry(_DEF, "u_substitution", "hard", "3*{v}**2*sin({v}**3 + {c})",
               bounds=[("0", "1")], sid="def_usub_sin3"),
        _entry(_DEF, "u_substitution", "hard", "2*{v}*cos({v}**2 + {c})",
               bounds=[("0", "1")], sid="def_usub_cos2"),
        _entry(_DEF, "u_substitution", "hard", "3*{v}**2*cos({v}**3 + {c})",
               bounds=[("0", "1")], sid="def_usub_cos3"),
        _entry(_DEF, "u_substitution", "hard", "({a} + 2*{v})*({v}**2 + {a}*{v} + {c})**{n}",
               bounds=[("0", "1")], sid="def_usub_quad_pow"),
        _entry(_DEF, "u_substitution", "hard", "({a} + 2*{v})/({v}**2 + {a}*{v} + {c})",
               bounds=[("0", "1")], sid="def_usub_quad_recip"),
        _entry(_DEF, "u_substitution", "hard", "sin({v})*cos({v})**{n}",
               bounds=[("0", "pi/2")], sid="def_usub_trig_pow_sin"),
        _entry(_DEF, "u_substitution", "hard", "cos({v})*sin({v})**{n}",
               bounds=[("0", "pi/2")], labels=["III-21"], sid="def_usub_trig_pow_cos"),
        _entry(_DEF, "u_substitution", "hard", "ln({v})**{n}/{v}",
               bounds=[("1", "e")], labels=["III-20", "III-22"], sid="def_usub_ln_pow"),
        _entry(_DEF, "u_substitution", "hard", "e**{v}/(e**{v} + {c})",
               bounds=[("0", "1")], sid="def_usub_e_recip"),
        _entry(_DEF, "u_substitution", "hard", "{k}*{v}*e**({k}*{v}**2 + {c})",
               bounds=[("0", "1")], sid="def_usub_kx2_exp"),
        _entry(_DEF, "u_substitution", "hard", "{b}*{v}/sqrt({b}*{v}**2 + {c})",
               bounds=[("0", "1")], sid="def_usub_sqrt"),
        _entry(_DEF, "u_substitution", "hard", "sin({v})/({a} + cos({v}))",
               bounds=[("pi/3", "pi/2")], labels=["III-28"], sid="def_usub_sinx_over"),
        # mixed sums (Part III S1/S3 shapes).
        _entry(_DEF, "mixed_sum", "medium", "{a}*{v}**2 + {b}*{v} + {c}",
               bounds=[("1", "2"), ("1", "3"), ("2", "3")], sid="def_mixed_1"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*{v}**2 + {b}/{v} + {f}*e**{v}",
               bounds=[("1", "2"), ("1", "3"), ("2", "3")], sid="def_mixed_2"),
        _entry(_DEF, "mixed_sum", "medium", "{a}/{v} + {b}/{v}**2 + {f}*e**{v}",
               bounds=[("1", "2"), ("1", "3"), ("2", "3")], sid="def_mixed_3"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*{v}**2 - {b}*{v} + {c} + {d}/{v}",
               bounds=[("1", "2"), ("1", "3"), ("2", "3")], sid="def_mixed_4"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*sqrt({v}) + {b}/sqrt({v}) + {c}",
               bounds=[("1", "2"), ("1", "3"), ("2", "3")], sid="def_mixed_5"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*{v}**2 + {b}*{v} + {c} + {f}*e**{v}",
               bounds=[("1", "2"), ("1", "3"), ("2", "3")], sid="def_mixed_6"),
        _entry(_DEF, "mixed_sum", "medium", "({a}*{v} - {b})*({c}*{v} + {d})",
               bounds=[("1", "2"), ("0", "1"), ("-1", "0"), ("-2", "-1")],
               labels=["III-11"], sid="def_mixed_7"),
        _entry(_DEF, "mixed_sum", "medium", "{a} + {b}/{v}**2 + {c}/{v}**3",
               bounds=[("-2", "-1"), ("-3", "-1"), ("1", "2")],
               labels=["III-7"], sid="def_mixed_8"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*{v} + {b} + e**{v}/(e**{v} + {c})",
               bounds=[("0", "1"), ("1", "2")], labels=["III-38"], sid="def_mixed_9"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*{v}/({v}**2 + {b}) - {c}/({v} - {s})",
               bounds=[("0", "1")], labels=["III-24"], sid="def_mixed_10"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*sin({v}) + {b}*cos({v})",
               bounds=[("0", "pi/4"), ("0", "pi/6"), ("pi/4", "pi/3")],
               labels=["III-9"], sid="def_mixed_11"),
        _entry(_DEF, "mixed_sum", "medium", "{a}/cos({v})**2 + {b}/sin({v})**2",
               bounds=[("pi/4", "pi/3"), ("pi/6", "pi/4")],
               labels=["III-10"], sid="def_mixed_12"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*sin({k}*{v}) + {b}*cos({k}*{v})",
               bounds=[("0", "pi/4"), ("0", "pi/6"), ("pi/4", "pi/3")], sid="def_mixed_13"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*sin({v}) + {b}/cos({v})**2",
               bounds=[("0", "pi/4"), ("0", "pi/6")], sid="def_mixed_14"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*tan({v}) + {b}*sin({v})",
               bounds=[("0", "pi/4"), ("0", "pi/6")], labels=["III-25"], sid="def_mixed_15"),
        _entry(_DEF, "mixed_sum", "medium", "sin({v}) + {a}*cos({v})/({s} - sin({v}))",
               bounds=[("0", "pi/2")], labels=["III-37"], sid="def_mixed_16"),
        # integration by parts (Part III S4).
        _entry(_DEF, "by_parts", "hard", "{a}*{v}*sin({k}*{v})",
               bounds=[("0", "pi/(2*{k})")], labels=["III-A", "III-D"], sid="def_byparts_x_sin"),
        _entry(_DEF, "by_parts", "hard", "{a}*{v}*cos({k}*{v})",
               bounds=[("0", "pi/(2*{k})")], labels=["III-B", "III-H"], sid="def_byparts_x_cos"),
        _entry(_DEF, "by_parts", "hard", "{a}*{v}*e**{v}",
               bounds=[("0", "1")], labels=["III-C"], sid="def_byparts_x_exp"),
        _entry(_DEF, "by_parts", "hard", "{v}*ln({v})",
               bounds=[("1", "2")], sid="def_byparts_x_ln"),
        _entry(_DEF, "by_parts", "hard", "{v}**2*ln({v})",
               bounds=[("1", "2")], sid="def_byparts_x2_ln"),
        _entry(_DEF, "by_parts", "hard", "{v}**3*ln({v})",
               bounds=[("1", "2")], labels=["III-E"], sid="def_byparts_x3_ln"),
        _entry(_DEF, "by_parts", "hard", "ln({v})**2/{v}",
               bounds=[("1", "2")], labels=["III-I"], sid="def_byparts_ln2_x"),
    ]


def _new_def_structures():
    return [
        _entry(_DEF, "mixed_sum", "medium", "{a}*{v}**2 + {b}/{v} - {f}*e**{v}",
               bounds=[("1", "2"), ("1", "3")], labels=["III-2", "III-3"], sid="def_x2_recip_negexp"),
        _entry(_DEF, "mixed_sum", "medium", "-{a}*{v}**5 - {b}*{v}**2 + {c}*{v} + {d}",
               bounds=[("-1", "0")], labels=["III-5"], sid="def_quintic_mix"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*sqrt({v}) - {b}/sqrt({v}) + {c}",
               bounds=[("1", "4")], labels=["III-6"], sid="def_sqrt_recip_mix"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*cos({k}*{v}) - {b}*sin({k}*{v})",
               bounds=[("0", "pi/4")], labels=["III-8"], sid="def_cos_sin_k"),
        _entry(_DEF, "mixed_sum", "medium", "({a}*{v} + {b})*({c} - {d}*{v})",
               bounds=[("-1", "0")], labels=["III-12"], sid="def_expand_opposite"),
        _entry(_DEF, "u_substitution", "hard", "({f})*({a} + 2*{v})*({v}**2 + {a}*{v} - {c})**{n}",
               bounds=[("-2", "1")], labels=["III-14"], sid="def_quad_pow_frac"),
        _entry(_DEF, "u_substitution", "hard", "(2*{v} - {a})*({v}**2 - {a}*{v} + {c})**{n}",
               bounds=[("-2", "2")], labels=["III-15"], sid="def_quad_pow_neg"),
        _entry(_DEF, "u_substitution", "hard", "({a} + 2*{v})*sqrt({v}**2 + {a}*{v})",
               bounds=[("0", "1")], labels=["III-17"], sid="def_quad_sqrt_pow"),
        _entry(_DEF, "u_substitution", "hard", "-sin({v})*cos({v})**{n}",
               bounds=[("0", "pi/4")], labels=["III-18"], sid="def_neg_sin_cos"),
        _entry(_DEF, "u_substitution", "hard", "(e**{v} + {b})*(e**{v} + {b}*{v})",
               bounds=[("0", "1")], labels=["III-19"], sid="def_exp_x_prod"),
        _entry(_DEF, "linear_argument", "medium", "{a}/({k}*{v} + {b})",
               bounds=[("0", "2")], labels=["III-23"], sid="def_linarg_recip_coef"),
        _entry(_DEF, "mixed_sum", "medium", "cos({v})**2 - sin({v})**2",
               bounds=[("0", "pi/4")], labels=["III-26"], sid="def_cos2_sin2"),
        _entry(_DEF, "u_substitution", "hard", "cos({v})/({b} + sin({v}))",
               bounds=[("0", "pi/2")], labels=["III-27"], sid="def_cos_over_sin"),
        _entry(_DEF, "linear_argument", "medium", "{a}/sqrt({k}*{v} + {b})",
               bounds=[("-1", "7")], labels=["III-29"], sid="def_linarg_sqrt_coef"),
        _entry(_DEF, "u_substitution", "hard", "{a}*{v}**2/({b}*{v}**3 + {c})**{n}",
               bounds=[("1", "2")], labels=["III-31"], sid="def_usub_cubic_negpow"),
        _entry(_DEF, "u_substitution", "hard", "{a}/({v}*ln({v})**{n})",
               bounds=[("e**2", "e**3")], labels=["III-32"], sid="def_ln_recip_pow"),
        _entry(_DEF, "mixed_sum", "medium", "{a}*{v} + {b} + {c}/({v} + {d})",
               bounds=[("1", "2")], labels=["III-33"], sid="def_lin_recip_mix"),
        _entry(_DEF, "mixed_sum", "medium", "{a}/({v} - {b}) + {c}/({v} - {b})**2",
               bounds=[("2", "3")], labels=["III-35"], sid="def_recip2_mix"),
        _entry(_DEF, "mixed_sum", "medium", "{a}/({v} + {b}) - {c}/({v} + {d}) + {g}/({v} + {d})**2",
               bounds=[("0", "1")], labels=["III-36"], sid="def_recip3_mix"),
        _entry(_DEF, "by_parts", "hard", "{a}*{v}**2*ln({k}*{v})",
               bounds=[("1", "2")], labels=["III-F"], sid="def_byparts_x2_lnkx"),
        _entry(_DEF, "by_parts", "hard", "{a}*{v}*sqrt({v} - {b})",
               bounds=[("1", "5")], labels=["III-G"], sid="def_byparts_x_sqrt_lin"),
        # III-J: ∫ ln(x)/√x dx — solvable via the antiderivative fallback.
        _entry(_DEF, "by_parts", "hard", "{a}*ln({v})/sqrt({v})",
               bounds=[("1", "4")], labels=["III-J"], sid="def_byparts_ln_sqrt"),
    ]


_INTEGRAL_STRUCTURES = (
    _indef_structures() + _new_indef_structures() + _def_structures() + _new_def_structures()
)

_STRUCT_BY_ID = {s["id"]: s for s in _INTEGRAL_STRUCTURES}

# All source exercise labels (the 124 = 15 curated + 109 transcribed). Broken
# source exercises stay excluded from structures and are listed here for the
# audit to assert they are *not* covered.
SOURCE_EXCLUDED_LABELS = ["III-30", "III-34"]


def all_integral_structures():
    return list(_INTEGRAL_STRUCTURES)


def structure_by_id(struct_id):
    return _STRUCT_BY_ID.get(struct_id)


def source_label_map():
    """label -> structure id, for every mapped exercise label."""
    out = {}
    for s in _INTEGRAL_STRUCTURES:
        for label in s["source_labels"]:
            out[label] = s["id"]
    return out


_LOCALS = {"pi": pi, "oo": oo, "sqrt": sqrt, "e": E}


def _slot_expr(tpl, var):
    s = tpl.replace("{v}", var)
    for slot in _SLOT_NAMES:
        s = s.replace("{" + slot + "}", slot)
    loc = {var: Symbol(var), **_LOCALS}
    for slot in _SLOT_NAMES:
        loc[slot] = Symbol(slot)
    return sympify(s, locals=loc)


def _bound_latex(bound, var):
    s = bound.replace("{v}", var)
    loc = {var: Symbol(var), **_LOCALS}
    for slot in _SLOT_NAMES:
        if "{" + slot + "}" in s:
            s = s.replace("{" + slot + "}", slot)
            loc[slot] = Symbol(slot)
    return latex(sympify(s, locals=loc))


def build_pattern_latex(struct):
    """Symbolic slot form of the integrand rendered as LaTeX (slots shown as
    a, b, c, ... — e.g. \\int (a x - b)(c x + d)\\,dx)."""
    var = struct["var"]
    expr = _slot_expr(struct["pattern"], var)
    body = f"\\int {latex(expr)}\\,d{var}"
    if struct["question_type"] == _DEF:
        lo, hi = struct["bounds"][0]
        body = f"\\int_{{{_bound_latex(lo, var)}}}^{{{_bound_latex(hi, var)}}} {latex(expr)}\\,d{var}"
    return body


def _expr_latex(expr_str, var):
    return latex(sympify(expr_str, locals={var: Symbol(var), **_LOCALS}))


def _build_prompt(struct, params, expr, var):
    expr_latex = _expr_latex(expr, var)
    if struct["question_type"] == _IND:
        prompt = f"Compute ∫ ({expr}) d{var} (indefinite — include +C)."
        prompt_latex = rf"\text{{Compute }} \int ({expr_latex})\,d{var} \text{{ (indefinite, +C)}}"
        display = f"\\int ({expr})\\,d{var}"
    else:
        lo, hi = params["lower"], params["upper"]
        lo_l, hi_l = _bound_latex(lo, var), _bound_latex(hi, var)
        prompt = f"Compute ∫ from {lo} to {hi} of {expr} d{var}."
        prompt_latex = rf"\text{{Compute }} \int_{{{lo_l}}}^{{{hi_l}}} {expr_latex}\,d{var}"
        display = f"\\int_{{{lo}}}^{{{hi}}} ({expr})\\,d{var}"
    return prompt, prompt_latex, display


def _sample_ok(solution, qt, var):
    r = solution["answer_exact"]
    if r.has(Integral):
        return False
    if qt == _IND:
        # A symbolic antiderivative is fine as an expression; reject only
        # degenerate results (infinities / not-a-number).
        return not (r.has(oo, -oo, zoo) or getattr(r, "is_nan", False) or r.is_finite is False)
    try:
        val = N(r, 8)
    except Exception:
        return False
    return bool(val.is_finite and val.is_real)


def _solve_struct(qt, params):
    if qt == _IND:
        return _solve_indefinite_integral(params)
    return _solve_definite_integral(params)


def build_sample(struct, seed):
    """Deterministic filled instance of a structure: params + solved solution,
    reseeding until the answer is a clean finite real result."""
    var = struct["var"]
    for attempt in range(40):
        rng = random.Random(seed + attempt * 7919)
        expr, vals = fill_structured(rng, struct["pattern"], var)
        params = {"expr": expr, "var": var, "variant": struct["variant"]}
        if struct["question_type"] == _DEF:
            lo_t, hi_t = rng.choice(struct["bounds"])
            params["lower"] = fill_bound(rng, lo_t, var, vals)
            params["upper"] = fill_bound(rng, hi_t, var, vals)
        try:
            solution = _solve_struct(struct["question_type"], params)
        except Exception:
            continue
        if not _sample_ok(solution, struct["question_type"], var):
            continue
        prompt, prompt_latex, display = _build_prompt(struct, params, expr, var)
        return {
            "structure": struct,
            "params": params,
            "prompt": prompt,
            "prompt_latex": prompt_latex,
            "display": display,
            "solution": solution,
        }
    raise ValueError(f"could not build a valid sample for {struct['id']}")
