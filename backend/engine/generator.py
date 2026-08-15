"""Random problem generation for complex-number and calculus questions.

Complex template mode keeps all coordinates integer so answers stay clean: modulus
uses Pythagorean triples (integer answer), argument uses pairs yielding a multiple of
pi/4 or an axis angle. Calculus template mode keeps limits/integrals restricted to
patterns with clean, exactly-computable SymPy answers (direct substitution, factorable
0/0 forms, rational limits at infinity, polynomial/simple-trig antiderivatives) — the
same spirit as the BAC II mock-exam problems this was modeled on. In Gemini mode, the
LLM proposes a complex-number problem and SymPy recomputes/validates the answer;
Gemini generation is not offered for calculus (proof/study-style calculus problems
don't reduce to a simple SymPy-checkable numeric answer the way these templates do).
"""
import random

from sympy import Symbol, latex, sympify

from engine import llm
from engine.notation import pretty_expr, pretty_point
from engine.solver import QUESTION_TYPES, format_z, z_latex

TOPICS = ("complex", "calculus")

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

CALCULUS_QUESTION_TYPES = ("limit", "definite_integral")

_LIMIT_VARIANT_BY_DIFFICULTY = {
    "easy": "polynomial",
    "medium": "removable",
    "hard": "infinity_rational",
}

_INTEGRAL_VARIANT_BY_DIFFICULTY = {
    "easy": "polynomial",
    "medium": "polynomial",
    "hard": "trig",
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


def _build_calculus(question_type, params, difficulty, prompt, prompt_latex, display):
    return {
        "topic": "calculus",
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

    return _build_calculus("limit", params, difficulty, prompt, prompt_latex, display)


def _generate_integral(rng, difficulty):
    variant = _INTEGRAL_VARIANT_BY_DIFFICULTY[difficulty]

    if variant == "trig":
        func = rng.choice(["sin(x)", "cos(x)"])
        lower, upper = "0", "pi/2"
        bounds_latex = ("0", r"\pi/2")
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

    params = {"expr": func, "var": "x", "lower": lower, "upper": upper}
    prompt = f"Compute ∫ from x = {pretty_point(lower)} to x = {pretty_point(upper)} of {pretty_expr(func)} dx."
    expr_latex = _expr_latex(func)
    prompt_latex = rf"\text{{Compute }} \int_{{{bounds_latex[0]}}}^{{{bounds_latex[1]}}} {expr_latex}\,dx"
    display = f"\\int_{{{lower}}}^{{{upper}}} ({func})\\,dx"

    return _build_calculus("definite_integral", params, difficulty, prompt, prompt_latex, display)


def _generate_calculus_templates(difficulty, seed, question_type):
    rng = random.Random(seed)
    qt = question_type or rng.choice(CALCULUS_QUESTION_TYPES)
    if qt not in CALCULUS_QUESTION_TYPES:
        raise ValueError(f"unknown question_type: {qt}")
    if difficulty not in _LIMIT_VARIANT_BY_DIFFICULTY:
        raise ValueError(f"unknown difficulty: {difficulty}")

    if qt == "limit":
        return _generate_limit(rng, difficulty)
    return _generate_integral(rng, difficulty)


async def generate(topic="complex", difficulty="medium", seed=None, question_type=None, generation_mode="templates"):
    if topic not in TOPICS:
        raise ValueError(f"unknown topic: {topic}")

    if topic == "calculus":
        return _generate_calculus_templates(difficulty, seed, question_type)

    if generation_mode == "gemini":
        problem = await _generate_gemini(difficulty)
        if problem is not None:
            return problem
    return _generate_templates(difficulty, seed, question_type)
