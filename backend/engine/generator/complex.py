"""Complex-number generation: template pools (Pythagorean triples, axis angles,
arithmetic/power/De Moivre/nth-root pools) and the Gemini-proposed variant
(SymPy still validates)."""
import random

from sympy import latex as _latex

from engine import llm
from engine.notation import pretty_expr
from engine.solver import QUESTION_TYPES, format_z, z_latex
from engine.solver.complex.nth_roots import _solve_nth_root
from engine.solver.complex.trig import STANDARD_ANGLES, angle_latex, z_from_polar
from engine.structures import _COMPLEX_CURATED_TEMPLATES


def _pretty_z(z_expr):
    """Plaintext fallback rendering of a SymPy complex expression (prompt_latex
    is what's actually shown; this is just the accessible plain-text form)."""
    return pretty_expr(str(z_expr).replace("*I", "i").replace("I", "i"))


_MODULUS_POOLS = {
    "easy": [(3, 4), (4, 3), (6, 8), (8, 6)],
    "medium": [(5, 12), (12, 5), (9, 12), (12, 9), (8, 15), (15, 8)],
    "hard": [(7, 24), (24, 7), (20, 21), (21, 20), (9, 40), (40, 9)],
}

_ARGUMENT_K = {"easy": 1, "medium": 2, "hard": 3}

_HI_RANGE = {"easy": 5, "medium": 12, "hard": 20}

_ARITHMETIC_OPS_BY_DIFFICULTY = {
    "easy": ["add", "subtract"],
    "medium": ["add", "subtract", "multiply"],
    "hard": ["multiply", "divide"],
}
_ARITHMETIC_HI = {"easy": 6, "medium": 9, "hard": 9}

_POWER_N_BY_DIFFICULTY = {"easy": 2, "medium": 3, "hard": 4}
_POWER_HI = {"easy": 5, "medium": 6, "hard": 4}

_DE_MOIVRE_R = {"easy": [1, 2], "medium": [1, 2, 3], "hard": [2, 3, 4]}
_DE_MOIVRE_N = {"easy": list(range(2, 8)), "medium": list(range(6, 20)), "hard": list(range(15, 41))}
# Cap r^n so the answer stays a genuinely large-but-displayable integer (the
# angle-reduction trick is the point of De Moivre, not raw digit count — the
# real exam's huge-exponent problems, e.g. (1-i)^2021, only stay tractable
# because students leave r^n in exponent form, which this app's plain-value
# grading doesn't support yet).
_DE_MOIVRE_MAGNITUDE_CAP = 10 ** 18

_NTH_ROOT_RHO = {"easy": [1, 2], "medium": [2, 3], "hard": [2, 3, 4]}
_NTH_ROOT_N = {"easy": [2], "medium": [2, 3], "hard": [3, 4, 5]}

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

_OP_WORD = {"add": "z1 + z2", "subtract": "z1 - z2", "multiply": "z1 \\times z2", "divide": "z1 / z2"}


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

def _build_curated_complex(item, difficulty):
    """A real textbook exercise from backend/data/complex_numbers/{formula_name}.json,
    replayed through the same a+bi solver as the procedural pool (SymPy still
    computes/grades the answer; the exam-authored technique note is carried
    for reference, mirroring the limits curated pool in generator/limits.py)."""
    problem = _build(item["question_type"], item["a"], item["b"], difficulty, "curated")
    problem["params"]["formula_name"] = item["formula_name"]
    problem["params"]["curated_technique"] = item["technique"]
    problem["params"]["source_id"] = item["id"]
    return problem

def _build_arithmetic(a1, b1, a2, b2, operation, difficulty):
    z1l, z2l = z_latex(a1, b1), z_latex(a2, b2)
    op_word = {"add": "sum", "subtract": "difference", "multiply": "product", "divide": "quotient"}[operation]
    return {
        "topic": "complex",
        "difficulty": difficulty,
        "question_type": "complex_arithmetic",
        "params": {"a1": a1, "b1": b1, "a2": a2, "b2": b2, "operation": operation},
        "prompt": f"Given z1 = {format_z(a1, b1)} and z2 = {format_z(a2, b2)}, find the {op_word} {'z1 + z2' if operation == 'add' else 'z1 - z2' if operation == 'subtract' else 'z1 * z2' if operation == 'multiply' else 'z1 / z2'}.",
        "prompt_latex": rf"\text{{Given }} z_1 = {z1l} \text{{ and }} z_2 = {z2l}\text{{, find }} {_OP_WORD[operation]}.",
        "source": "template",
    }

def _build_power(a, b, n, difficulty):
    zl = z_latex(a, b)
    return {
        "topic": "complex",
        "difficulty": difficulty,
        "question_type": "complex_power",
        "params": {"a": a, "b": b, "n": n},
        "prompt": f"Given z = {format_z(a, b)}, compute z^{n}.",
        "prompt_latex": rf"\text{{Given }} z = {zl}\text{{, compute }} z^{{{n}}}.",
        "source": "template",
    }

def _build_de_moivre(r, k, d, n, difficulty):
    z = z_from_polar(r, k, d)
    return {
        "topic": "complex",
        "difficulty": difficulty,
        "question_type": "de_moivre_power",
        "params": {"r": r, "k": k, "d": d, "n": n},
        "prompt": f"Given z = {_pretty_z(z)}, compute z^{n} using De Moivre's formula.",
        "prompt_latex": rf"\text{{Given }} z = {_latex(z)}\text{{, compute }} z^{{{n}}}.",
        "source": "template",
    }

def _build_nth_root(rho, k0, d0, n, difficulty):
    solution = _solve_nth_root(rho, k0, d0, n)
    z_plain = _pretty_z(solution["given_z"])
    return {
        "topic": "complex",
        "difficulty": difficulty,
        "question_type": "nth_roots",
        "params": {"rho": rho, "k0": k0, "d0": d0, "n": n},
        "prompt": f"Find a value w such that w^{n} = {z_plain}.",
        "prompt_latex": rf"\text{{Find }} w \text{{ such that }} w^{{{n}}} = {solution['given_z_latex']}.",
        "source": "template",
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

    curated_pool = [
        t for t in _COMPLEX_CURATED_TEMPLATES
        if t["difficulty"] == difficulty and t["question_type"] == qt
    ]
    if curated_pool and rng.random() < 0.5:
        return _build_curated_complex(rng.choice(curated_pool), difficulty)

    if qt == "modulus":
        x, y = rng.choice(_MODULUS_POOLS[difficulty])
        a, b = _sign(rng, x), _sign(rng, y)
        return _build(qt, a, b, difficulty, "template")
    if qt == "argument":
        k = _ARGUMENT_K[difficulty]
        a, b = rng.choice([
            (k, k), (k, -k), (-k, k), (-k, -k),
            (k, 0), (0, k), (0, -k), (-k, 0),
        ])
        return _build(qt, a, b, difficulty, "template")
    if qt in ("conjugate", "real_part", "imaginary_part"):
        hi = _HI_RANGE[difficulty]
        a = rng.randint(-hi, hi)
        b = rng.randint(-hi, hi)
        while b == 0:
            b = rng.randint(-hi, hi)
        return _build(qt, a, b, difficulty, "template")
    if qt == "complex_arithmetic":
        hi = _ARITHMETIC_HI[difficulty]
        operation = rng.choice(_ARITHMETIC_OPS_BY_DIFFICULTY[difficulty])
        a1, b1 = rng.randint(-hi, hi), rng.randint(-hi, hi)
        a2, b2 = rng.randint(-hi, hi), rng.randint(-hi, hi)
        while operation == "divide" and a2 == 0 and b2 == 0:
            a2, b2 = rng.randint(-hi, hi), rng.randint(-hi, hi)
        return _build_arithmetic(a1, b1, a2, b2, operation, difficulty)
    if qt == "complex_power":
        hi = _POWER_HI[difficulty]
        n = _POWER_N_BY_DIFFICULTY[difficulty]
        a, b = rng.randint(-hi, hi), rng.randint(-hi, hi)
        while b == 0:
            b = rng.randint(-hi, hi)
        return _build_power(a, b, n, difficulty)
    if qt == "de_moivre_power":
        r = rng.choice(_DE_MOIVRE_R[difficulty])
        k, d = rng.choice(STANDARD_ANGLES)
        n_pool = [n for n in _DE_MOIVRE_N[difficulty] if r ** n <= _DE_MOIVRE_MAGNITUDE_CAP] or [_DE_MOIVRE_N[difficulty][0]]
        n = rng.choice(n_pool)
        return _build_de_moivre(r, k, d, n, difficulty)
    if qt == "nth_roots":
        rho = rng.choice(_NTH_ROOT_RHO[difficulty])
        k0, d0 = rng.choice(STANDARD_ANGLES)
        n = rng.choice(_NTH_ROOT_N[difficulty])
        return _build_nth_root(rho, k0, d0, n, difficulty)
    raise ValueError(f"unknown question_type: {qt}")

async def _generate_gemini(difficulty):
    candidate = await llm.propose_problem("complex", difficulty)
    if not candidate:
        return None
    qt, a, b = candidate["question_type"], candidate["a"], candidate["b"]
    if qt not in ("modulus", "argument", "conjugate", "real_part", "imaginary_part"):
        return None
    if not (-20 <= a <= 20 and -20 <= b <= 20 and b != 0):
        return None
    return _build(qt, a, b, difficulty, "gemini")
