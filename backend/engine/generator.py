"""Random complex-number problem generation.

Template mode keeps all coordinates integer so answers stay clean: modulus uses
Pythagorean triples (integer answer), argument uses pairs yielding a multiple of
pi/4 or an axis angle. In Gemini mode, the LLM proposes a problem and SymPy
recomputes/validates the answer.
"""
import random

from . import llm
from .solver import QUESTION_TYPES, format_z, z_latex

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


def _build(question_type, a, b, difficulty):
    z = format_z(a, b)
    return {
        "topic": "complex",
        "difficulty": difficulty,
        "question_type": question_type,
        "a": a,
        "b": b,
        "z_display": z,
        "z_latex": z_latex(a, b),
        "prompt": _PROMPTS[question_type](z),
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

    return _build(qt, a, b, difficulty)


def _generate_gemini(difficulty):
    candidate = llm.propose_problem("complex", difficulty)
    if not candidate:
        return None
    qt, a, b = candidate["question_type"], candidate["a"], candidate["b"]
    if qt not in QUESTION_TYPES:
        return None
    if not (-20 <= a <= 20 and -20 <= b <= 20 and b != 0):
        return None
    return _build(qt, a, b, difficulty)


def generate(difficulty="medium", seed=None, question_type=None, generation_mode="templates"):
    if generation_mode == "gemini":
        problem = _generate_gemini(difficulty)
        if problem is not None:
            return problem
    return _generate_templates(difficulty, seed, question_type)
