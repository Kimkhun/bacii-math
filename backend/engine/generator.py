"""Random problem generation for complex-number, limit, and integral questions.

Complex template mode keeps all coordinates integer so answers stay clean: modulus
uses Pythagorean triples (integer answer), argument uses pairs yielding a multiple of
pi/4 or an axis angle. Limit/integral template mode keeps problems restricted to
patterns with clean, exactly-computable SymPy answers (direct substitution, factorable
0/0 forms, rational limits at infinity, polynomial/simple-trig antiderivatives) — the
same spirit as the BAC II mock-exam problems this was modeled on. In Gemini mode, the
LLM proposes a complex-number problem and SymPy recomputes/validates the answer;
Gemini generation is not offered for limits/integrals (proof/study-style problems
don't reduce to a simple SymPy-checkable numeric answer the way these templates do).
"""
import random

from sympy import Symbol, latex, sympify

from engine import llm, scenarios
from engine.notation import pretty_expr, pretty_point
from engine.solver import QUESTION_TYPES, format_z, z_latex
from engine.structures import (
    _COEFF_POOLS,
    _fill,
    _INDEF_EXPAND_TEMPLATES,
    _INDEFINITE_TEMPLATES,
    _INDEF_LINEAR_TEMPLATES,
    _INDEF_SPLIT_TEMPLATES,
    _INDEF_TRIG_SQ_TEMPLATES,
    _INDEF_USUB_TEMPLATES,
)

TOPICS = ("complex", "limit", "integral", "probability")

_MODULUS_POOLS = {
    "easy": [(3, 4), (4, 3), (6, 8), (8, 6)],
    "medium": [(5, 12), (12, 5), (9, 12), (12, 9), (8, 15), (15, 8)],
    "hard": [(7, 24), (24, 7), (20, 21), (21, 20), (9, 40), (40, 9)],
}

_ARGUMENT_K = {"easy": 1, "medium": 2, "hard": 3}

_HI_RANGE = {"easy": 5, "medium": 12, "hard": 20}

_PROMPTS = {
    "modulus": lambda z: f"Find the modulus |z| of z = {z}.",
    "argument": lambda z: f"Find the principal argument arg(z), in radians, of z = {z}.",
    "conjugate": lambda z: f"Find the complex conjugate of z = {z}.",
    "real_part": lambda z: f"Find the real part Re(z) of z = {z}.",
    "imaginary_part": lambda z: f"Find the imaginary part Im(z) of z = {z}.",
}

_PROMPTS_LATEX = {
    "modulus": lambda zl: rf"\text{{Find the modulus }} |z| \text{{ of }} z = {zl}.",
    "argument": lambda zl: rf"\text{{Find the principal argument }} \arg(z) \text{{ of }} z = {zl}.",
    "conjugate": lambda zl: rf"\text{{Find the complex conjugate of }} z = {zl}.",
    "real_part": lambda zl: rf"\text{{Find }} \operatorname{{Re}}(z) \text{{ of }} z = {zl}.",
    "imaginary_part": lambda zl: rf"\text{{Find }} \operatorname{{Im}}(z) \text{{ of }} z = {zl}.",
}
_LIMIT_VARIANT_BY_DIFFICULTY = {
    "easy": "polynomial",
    "medium": "removable",
    "hard": "infinity_rational",
}

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


def _build(question_type, a, b, difficulty, source):
    z = format_z(a, b)
    zl = z_latex(a, b)
    return {
        "topic": "complex",
        "difficulty": difficulty,
        "question_type": question_type,
        "params": {"a": a, "b": b},
        "a": a,
        "b": b,
        "z_display": z,
        "z_latex": zl,
        "prompt": _PROMPTS[question_type](z),
        "prompt_latex": _PROMPTS_LATEX[question_type](zl),
        "source": source,
    }


def _sign(rng, v):
    return v if rng.random() < 0.5 else -v


def _generate_templates(difficulty, seed, question_type):
    rng = random.Random(seed)
    qt = question_type or rng.choice(QUESTION_TYPES)
    if qt not in QUESTION_TYPES:
        raise ValueError(f"unknown question_type: {qt}")
    if difficulty not in _HI_RANGE:
        raise ValueError(f"unknown difficulty: {difficulty}")

    if qt == "modulus":
        x, y = rng.choice(_MODULUS_POOLS[difficulty])
        a, b = _sign(rng, x), _sign(rng, y)
    elif qt == "argument":
        k = _ARGUMENT_K[difficulty]
        a, b = rng.choice([
            (k, k), (k, -k), (-k, k), (-k, -k),
            (k, 0), (0, k), (0, -k), (-k, 0),
        ])
    else:
        hi = _HI_RANGE[difficulty]
        a = rng.randint(-hi, hi)
        b = rng.randint(-hi, hi)
        while b == 0:
            b = rng.randint(-hi, hi)

    return _build(qt, a, b, difficulty, "template")


async def _generate_gemini(difficulty):
    candidate = await llm.propose_problem("complex", difficulty)
    if not candidate:
        return None
    qt, a, b = candidate["question_type"], candidate["a"], candidate["b"]
    if qt not in QUESTION_TYPES:
        return None
    if not (-20 <= a <= 20 and -20 <= b <= 20 and b != 0):
        return None
    return _build(qt, a, b, difficulty, "gemini")


def _build_expr_problem(topic, question_type, params, difficulty, prompt, prompt_latex, display):
    return {
        "topic": topic,
        "difficulty": difficulty,
        "question_type": question_type,
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": prompt,
        "prompt_latex": prompt_latex,
        "source": "template",
    }


def _expr_latex(expr_str, var="x"):
    return latex(sympify(expr_str, locals={var: Symbol(var)}))


def _fmt_poly(p, q, r, var="x"):
    terms = []
    if p:
        terms.append(f"{p}*{var}**2" if p != 1 else f"{var}**2")
    if q:
        sign = "+" if (q > 0 and terms) else ""
        terms.append(f"{sign}{q}*{var}" if abs(q) != 1 else f"{sign}{'-' if q<0 else ''}{var}")
    if r:
        sign = "+" if (r > 0 and terms) else ""
        terms.append(f"{sign}{r}")
    return "".join(terms) or "0"


def _generate_limit(rng, difficulty):
    variant = _LIMIT_VARIANT_BY_DIFFICULTY[difficulty]

    if variant == "polynomial":
        p = rng.randint(1, 3)
        q = rng.randint(-5, 5)
        r = rng.randint(-5, 5)
        c = rng.randint(-3, 3)
        expr = _fmt_poly(p, q, r)
        point_latex = str(c)
    elif variant == "removable":
        c = rng.choice([v for v in range(-5, 6) if v != 0])
        expr = f"(x**2 - {c * c})/(x - {c})"
        point_latex = str(c)
    else:  # infinity_rational
        p = rng.randint(1, 5)
        q = rng.randint(-9, 9)
        r = rng.randint(1, 5)
        s = rng.randint(-9, 9)
        num = _fmt_poly(p, q, 0)
        den = _fmt_poly(r, 0, s)
        expr = f"({num})/({den})"
        point_latex = r"+\infty"

    point = "oo" if variant == "infinity_rational" else str(c)
    params = {"expr": expr, "var": "x", "point": point}
    point_display = "+∞" if variant == "infinity_rational" else str(c)
    prompt = f"Find lim(x → {point_display}) of {pretty_expr(expr)}."
    expr_latex = _expr_latex(expr)
    prompt_latex = rf"\text{{Find }} \lim_{{x \to {point_latex}}} {expr_latex}"
    display = f"lim_{{x \\to {point_display}}} {expr}"

    return _build_expr_problem("limit", "limit", params, difficulty, prompt, prompt_latex, display)


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


def _generate_expr_templates(topic, difficulty, seed, question_type, variant=None):
    rng = random.Random(seed)
    allowed = {
        "limit": ("limit",),
        "integral": ("definite_integral", "indefinite_integral"),
    }[topic]
    qt = question_type or allowed[0]
    if qt not in allowed:
        raise ValueError(f"question_type {qt} does not match topic {topic}")
    if difficulty not in _LIMIT_VARIANT_BY_DIFFICULTY:
        raise ValueError(f"unknown difficulty: {difficulty}")

    if topic == "limit":
        return _generate_limit(rng, difficulty)
    if qt == "indefinite_integral":
        return _generate_indefinite(rng, difficulty, variant)
    return _generate_integral(rng, difficulty, variant)


def _generate_probability(rng, difficulty, question_type=None, variant=None):
    """Pick a multi-part exercise from the user-owned catalog, sample valid
    params, fill the Khmer (or English) sentences — setup on its own line, then
    every sub-part A/B/C/D on its own line — and return the problem. The solver
    computes every part's answer afterwards; the catalog only owns the story and
    the param *possibility* constraints."""
    if question_type not in (None, "probability"):
        raise ValueError(f"question_type {question_type} does not match topic probability")
    if difficulty not in scenarios.VARIANT_BY_DIFFICULTY:
        raise ValueError(f"unknown difficulty: {difficulty}")

    pool = [variant] if variant and variant in scenarios.SCENARIOS else None
    if pool is None:
        pool = list(scenarios.VARIANT_BY_DIFFICULTY.get(difficulty, ()))
        if not pool:
            pool = list(scenarios.SCENARIOS)
    if not pool:
        raise ValueError(f"no probability scenarios for difficulty {difficulty}")
    rng.shuffle(pool)

    for sid in pool:
        entry = scenarios.by_id(sid)
        envs = scenarios.sample_scenario(entry, rng)
        if not envs:
            continue

        lines = []
        setup = entry.get("setup_km") or entry.get("setup_en") or ""
        if setup:
            lines.append(scenarios.fill_frame(setup, envs[0]["env"]))
        parts = entry.get("parts") or []
        part_params = []
        for i, pe in enumerate(envs):
            part = parts[i] if i < len(parts) else {}
            frame = part.get("km") or part.get("en") or pe.get("km") or ""
            if not frame:
                continue
            lines.append(scenarios.fill_frame(frame, pe["env"]))
            part_params.append({"label": pe["label"], "want": pe["want"], **pe["env"]})
        if len(part_params) < 1:
            continue
        try:
            text = "\n".join(lines)
        except ValueError:
            continue

        params = {
            "structure": entry["structure"],
            "variant": sid,
            "scenario_id": sid,
            "target": part_params[-1]["label"],
            "parts": part_params,
        }
        display = f"probability ({entry['structure']})"
        return _build_expr_problem(
            "probability", "probability", params, difficulty, text, None, display
        )
    raise ValueError(f"no scenario could produce a valid problem for difficulty {difficulty}")


async def generate(topic="complex", difficulty="medium", seed=None, question_type=None, generation_mode="templates", variant=None):
    if topic not in TOPICS:
        raise ValueError(f"unknown topic: {topic}")

    if topic == "probability":
        return _generate_probability(random.Random(seed), difficulty, question_type, variant)

    if topic in ("limit", "integral"):
        return _generate_expr_templates(topic, difficulty, seed, question_type, variant)

    if generation_mode == "gemini":
        problem = await _generate_gemini(difficulty)
        if problem is not None:
            return problem
    return _generate_templates(difficulty, seed, question_type)
