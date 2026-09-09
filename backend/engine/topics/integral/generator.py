"""Integral generation: definite (polynomial, trig, linear_argument, u_substitution,
mixed_sum, by_parts) and indefinite (power, expand, split, linear_argument, usub,
trig_sec) variants, plus the difficulty variant tables."""
from engine.core.expr_shared import _build_expr_problem, _expr_latex, _fmt_poly
from engine.core.slots import _fill
from engine.notation import pretty_expr, pretty_point

from .structures import (
    _INDEF_EXPAND_TEMPLATES,
    _INDEFINITE_TEMPLATES,
    _INDEF_LINEAR_TEMPLATES,
    _INDEF_SPLIT_TEMPLATES,
    _INDEF_TRIG_SQ_TEMPLATES,
    _INDEF_USUB_TEMPLATES,
)


_INTEGRAL_VARIANT_BY_DIFFICULTY = {
    "easy": ["polynomial"],
    "medium": ["polynomial", "linear_argument", "mixed_sum"],
    "hard": ["trig", "u_substitution", "by_parts"],
}

_INDEFINITE_VARIANT_BY_DIFFICULTY = {
    "easy": ["power", "expand"],
    "medium": ["power", "expand", "split", "linear_argument"],
    "hard": ["usub", "split", "trig_sec", "linear_argument", "expand"],
}

def _generate_integral(rng, difficulty, variant=None):
    variant = variant or rng.choice(_INTEGRAL_VARIANT_BY_DIFFICULTY[difficulty])

    if variant == "trig":
        # c·sin(x) or c·cos(x) over bounds whose answers stay clean:
        # sin: 0→π/2 gives c, 0→π/3 gives c/2; cos: 0→π/2 gives c, 0→π/6 gives c/2.
        coef = rng.choice([1, 2, 3, 5])
        kind = rng.choice(["sin", "cos"])
        upper = rng.choice(["pi/2", "pi/3"] if kind == "sin" else ["pi/2", "pi/6"])
        func = f"{coef}*{kind}(x)" if coef != 1 else f"{kind}(x)"
        lower = "0"
        bounds_latex = ("0", upper.replace("pi", r"\pi"))
    elif variant == "linear_argument":
        # ∫f(kx+b) forms over [0,1] (or clean trig bounds). Trig keeps b=0;
        # reciprocal/sqrt force b ≥ 1 so the integral is proper at x = 0.
        k = rng.randint(2, 5)
        kind = rng.choice(["sin", "cos", "e", "power", "reciprocal", "sqrt"])
        b = rng.choice([0, 0, 1, 2, -1])
        if kind in ("reciprocal", "sqrt") and b <= 0:
            b = 1
        if kind in ("sin", "cos"):
            func = f"{kind}({k}*x)"
            lower, upper = "0", f"pi/(2*{k})"
            bounds_latex = ("0", rf"\pi/(2\cdot{k})")
        elif kind == "e":
            func = f"e**({k}*x+{b})" if b else f"e**({k}*x)"
            lower, upper = "0", "1"
            bounds_latex = ("0", "1")
        elif kind == "power":
            n = rng.randint(2, 3)
            arg = f"{k}*x+{b}" if b else f"{k}*x"
            func = f"({arg})**{n}"
            lower, upper = "0", "1"
            bounds_latex = ("0", "1")
        elif kind == "sqrt":
            arg = f"{k}*x+{b}" if b else f"{k}*x"
            func = f"1/sqrt({arg})"
            lower, upper = "0", "1"
            bounds_latex = ("0", "1")
        else:  # reciprocal
            arg = f"{k}*x+{b}" if b else f"{k}*x"
            func = f"1/({arg})"
            lower, upper = "0", "1"
            bounds_latex = ("0", "1")
    elif variant == "u_substitution":
        # ∫u'·f(u) definite forms. Bounds are chosen so the substituted
        # endpoints stay clean numbers (or special trig values).
        ukind = rng.choice([
            "power", "reciprocal", "exp", "sin", "cos", "quad_pow", "quad_recip",
            "trig_power", "ln_pow", "e_recip", "kx2_exp", "sqrt", "sinx_over",
        ])
        if ukind in ("power", "reciprocal", "exp", "sin", "cos"):
            c = rng.randint(1, 3)
            degree = rng.choice([2, 2, 3])
            if degree == 2:
                u, ud = f"x**2+{c}", "2*x"
            else:
                u, ud = f"x**3+{c}", "3*x**2"
            lower, upper = "0", "1"
            bounds_latex = ("0", "1")
            if ukind == "power":
                n = rng.randint(2, 3)
                func = f"{ud}*({u})**{n}"
            elif ukind == "reciprocal":
                func = f"{ud}/({u})"
            elif ukind == "exp":
                func = f"{ud}*e**({u})"
            else:
                func = f"{ud}*{ukind}({u})"
        elif ukind in ("quad_pow", "quad_recip"):
            a = rng.randint(1, 3)
            c = rng.randint(1, 4)
            u = f"x**2 + {a}*x + {c}"
            ud = f"{a} + 2*x"
            if ukind == "quad_pow":
                n = rng.randint(2, 3)
                func = f"({ud})*({u})**{n}"
            else:
                func = f"({ud})/({u})"
            lower, upper = "0", "1"
            bounds_latex = ("0", "1")
        elif ukind == "trig_power":
            n = rng.randint(2, 4)
            func = rng.choice([f"sin(x)*cos(x)**{n}", f"cos(x)*sin(x)**{n}"])
            lower, upper = "0", "pi/2"
            bounds_latex = ("0", r"\pi/2")
        elif ukind == "ln_pow":
            n = rng.randint(2, 4)
            func = f"ln(x)**{n}/x"
            lower, upper = "1", "e"
            bounds_latex = ("1", "e")
        elif ukind == "e_recip":
            c = rng.randint(2, 4)
            func = f"e**x/(e**x + {c})"
            lower, upper = "0", "1"
            bounds_latex = ("0", "1")
        elif ukind == "kx2_exp":
            k = rng.randint(2, 3)
            c = rng.randint(1, 3)
            func = f"{k}*x*e**({k}*x**2 + {c})"
            lower, upper = "0", "1"
            bounds_latex = ("0", "1")
        elif ukind == "sqrt":
            b = rng.randint(1, 3)
            c = rng.randint(1, 4)
            func = f"{b}*x/sqrt({b}*x**2 + {c})"
            lower, upper = "0", "1"
            bounds_latex = ("0", "1")
        else:  # sinx_over — u = a + cos x, u' = -sin x, clean on (π/3, π/2)
            a = rng.randint(1, 3)
            func = f"sin(x)/({a} + cos(x))"
            lower, upper = "pi/3", "pi/2"
            bounds_latex = (r"\pi/3", r"\pi/2")
    elif variant == "mixed_sum":
        # Sums of basic terms (Part III S1): algebraic+exponential over integer
        # bounds, or a trig set over special-angle bounds. Bounds avoid the
        # singularities of the source material (never 1/x through 0).
        if rng.random() < 0.6:
            # algebraic + exponential over integer bounds (products, negative
            # bounds and 1/xⁿ forms are safe — no 1/x through 0).
            tpl, safe_bounds = rng.choice([
                ("{a}*x**2 + {b}*x + {c}", [("1", "2"), ("1", "3"), ("2", "3")]),
                ("{a}*x**2 + {b}/x + {f}*e**x", [("1", "2"), ("1", "3"), ("2", "3")]),
                ("{a}/x + {b}/x**2 + {f}*e**x", [("1", "2"), ("1", "3"), ("2", "3")]),
                ("{a}*x**2 - {b}*x + {c} + {d}/x", [("1", "2"), ("1", "3"), ("2", "3")]),
                ("{a}*sqrt(x) + {b}/sqrt(x) + {c}", [("1", "2"), ("1", "3"), ("2", "3")]),
                ("{a}*x**2 + {b}*x + {c} + {f}*e**x", [("1", "2"), ("1", "3"), ("2", "3")]),
                ("({a}*x - {b})*({c}*x + {d})", [("1", "2"), ("0", "1"), ("-1", "0"), ("-2", "-1")]),
                ("{a} + {b}/x**2 + {c}/x**3", [("-2", "-1"), ("-3", "-1"), ("1", "2")]),
                ("{a}*x + {b} + e**x/(e**x + {c})", [("0", "1"), ("1", "2")]),
                ("{a}*x/(x**2 + {b}) - {c}/(x - {s})", [("0", "1")]),
            ])
            func = _fill(rng, tpl, "x")
            lo, hi = rng.choice(safe_bounds)
            lower, upper = lo, hi
            bounds_latex = (lo, hi)
        else:
            # Each trig template carries only bounds where its terms are finite
            # (csc² diverges at 0, sec² at π/2).
            tpl, safe = rng.choice([
                ("{a}*sin(x) + {b}*cos(x)", [("0", "pi/4"), ("0", "pi/6"), ("pi/4", "pi/3")]),
                ("{a}/cos(x)**2 + {b}/sin(x)**2", [("pi/4", "pi/3"), ("pi/6", "pi/4")]),
                ("{a}*sin({k}*x) + {b}*cos({k}*x)", [("0", "pi/4"), ("0", "pi/6"), ("pi/4", "pi/3")]),
                ("{a}*sin(x) + {b}/cos(x)**2", [("0", "pi/4"), ("0", "pi/6")]),
                ("{a}*tan(x) + {b}*sin(x)", [("0", "pi/4"), ("0", "pi/6")]),
                ("sin(x) + {a}*cos(x)/({s} - sin(x))", [("0", "pi/2")]),
            ])
            func = _fill(rng, tpl, "x")
            lo, hi = rng.choice(safe)
            lower, upper = lo, hi
            bounds_latex = (lo.replace("pi", r"\pi"), hi.replace("pi", r"\pi"))
    elif variant == "by_parts":
        # Integration by parts (Part III S4): x·sin/cos(kx), x·eˣ, xⁿln x,
        # ln²x/x — all over bounds with clean exact answers.
        kind = rng.choice(["x_sin", "x_cos", "x_e", "x_ln", "x2_ln", "x3_ln", "ln2_x"])
        if kind == "x_sin":
            k = rng.randint(2, 4)
            a = rng.choice([1, 2, 3])
            func = f"{a}*x*sin({k}*x)"
            lower, upper = "0", f"pi/(2*{k})"
            bounds_latex = ("0", rf"\pi/(2\cdot{k})")
        elif kind == "x_cos":
            k = rng.randint(2, 4)
            a = rng.choice([1, 2, 3])
            func = f"{a}*x*cos({k}*x)"
            lower, upper = "0", f"pi/(2*{k})"
            bounds_latex = ("0", rf"\pi/(2\cdot{k})")
        elif kind == "x_e":
            a = rng.choice([1, 2, 3])
            func = f"{a}*x*e**x"
            lower, upper = "0", "1"
            bounds_latex = ("0", "1")
        elif kind == "x_ln":
            func = "x*ln(x)"
            lower, upper = "1", "2"
            bounds_latex = ("1", "2")
        elif kind == "x2_ln":
            func = "x**2*ln(x)"
            lower, upper = "1", "2"
            bounds_latex = ("1", "2")
        elif kind == "x3_ln":
            func = "x**3*ln(x)"
            lower, upper = "1", "2"
            bounds_latex = ("1", "2")
        else:  # ln2_x
            func = "ln(x)**2/x"
            lower, upper = "1", "2"
            bounds_latex = ("1", "2")
    else:
        hi = 3 if difficulty == "easy" else 6
        p = rng.randint(-hi, hi)
        q = rng.randint(-hi, hi)
        r = rng.randint(-hi, hi)
        lower_n = rng.randint(-2, 1) if difficulty != "easy" else 0
        upper_n = rng.randint(lower_n + 1, lower_n + 3)
        func = _fmt_poly(p, q, r)
        lower, upper = str(lower_n), str(upper_n)
        bounds_latex = (lower, upper)

    params = {"expr": func, "var": "x", "lower": lower, "upper": upper, "variant": variant}
    prompt = f"Compute ∫ from x = {pretty_point(lower)} to x = {pretty_point(upper)} of {pretty_expr(func)} dx."
    expr_latex = _expr_latex(func)
    prompt_latex = rf"\text{{Compute }} \int_{{{bounds_latex[0]}}}^{{{bounds_latex[1]}}} {expr_latex}\,dx"
    display = f"\\int_{{{lower}}}^{{{upper}}} ({func})\\,dx"

    return _build_expr_problem("integral", "definite_integral", params, difficulty, prompt, prompt_latex, display)

_INDEFINITE_VARIABLES = ("x", "t", "y")

# Term pools for indefinite sums (terms are written with x; the variable is
# substituted in). Constants like ln2, e, pi, sqrt5 mirror the BAC II exercises.
_INDEFINITE_TERM_POOLS = {
    "power": [
        "3*x**2", "2*x", "-4", "5", "1", "-3*x**3", "4*x**2", "-7*x", "x**3",
        "(1/2)*x**2", "-6*x", "9", "x**(2/3)", "x*sqrt(x)",
    ],
    "reciprocal": [
        "2/x", "5/x", "1/x", "-3/x", "6/x", "4/x**2", "-5/sqrt(x)", "3/(2*x)",
        "-3/(2*x**2)", "7/x",
    ],
    "exponential": ["e**x", "2*e**x", "-2*e**x", "(3/4)*e**x", "4*e**x", "-e**x"],
    "trig": ["sin(x)", "cos(x)", "2*sin(x)", "3*cos(x)", "-3*sin(x)", "5*cos(x)", "-cos(x)"],
    "trig_sec": ["1/cos(x)**2", "2/sin(x)**2", "1/sin(x)**2", "3/cos(x)**2", "2/cos(x)**2", "-1/sin(x)**2"],
    "special": ["ln(2)", "ln(3)", "e", "e**2", "pi", "sqrt(5)", "sqrt(3)", "-e", "-pi", "x*ln(2)"],
}

def _build_indefinite(func, var, difficulty, variant, curated=False):
    params = {"expr": func, "var": var, "variant": variant, "curated": curated}
    prompt = f"Compute ∫ ({pretty_expr(func)}) d{var} (indefinite — include +C)."
    expr_latex = _expr_latex(func, var)
    prompt_latex = rf"\text{{Compute }} \int ({expr_latex})\,d{var} \text{{ (indefinite, +C)}}"
    display = f"\\int ({func})\\,d{var}"
    return _build_expr_problem("integral", "indefinite_integral", params, difficulty, prompt, prompt_latex, display)

def _generate_indefinite(rng, difficulty, variant=None):
    variant = variant or rng.choice(_INDEFINITE_VARIANT_BY_DIFFICULTY[difficulty])
    var = rng.choice(_INDEFINITE_VARIABLES)

    if variant == "expand":
        return _build_indefinite(_fill(rng, rng.choice(_INDEF_EXPAND_TEMPLATES), var), var, difficulty, variant)
    if variant == "split":
        return _build_indefinite(_fill(rng, rng.choice(_INDEF_SPLIT_TEMPLATES), var), var, difficulty, variant)
    if variant == "usub":
        _, tpl = rng.choice(_INDEF_USUB_TEMPLATES)
        return _build_indefinite(_fill(rng, tpl, var), var, difficulty, variant)
    if variant == "linear_argument":
        return _build_indefinite(_fill(rng, rng.choice(_INDEF_LINEAR_TEMPLATES), var), var, difficulty, variant)
    if variant == "trig_sec" and rng.random() < 0.5:
        return _build_indefinite(
            _fill(rng, rng.choice(_INDEF_TRIG_SQ_TEMPLATES), var), var, difficulty, variant
        )

    # "power" (easy) and "trig_sec" (hard): curated shapes + random term sums.
    if rng.random() < 0.4:
        pool = [t for d, t in _INDEFINITE_TEMPLATES if d == difficulty]
        if not pool:
            pool = [t for d, t in _INDEFINITE_TEMPLATES]
        tpl, tvar = rng.choice(pool)
        return _build_indefinite(_fill(rng, tpl, tvar), tvar, difficulty, "indefinite_sum", curated=True)

    groups = ["power"]
    if difficulty == "medium":
        groups = rng.sample(["power", "reciprocal", "exponential"], k=2)
    elif difficulty == "hard":
        groups = rng.sample(
            ["power", "reciprocal", "exponential", "trig", "trig_sec", "special"],
            k=rng.randint(3, 4),
        )
    terms = [rng.choice(_INDEFINITE_TERM_POOLS[g]) for g in groups]
    func = " + ".join(terms).replace("x", var)
    return _build_indefinite(func, var, difficulty, variant)