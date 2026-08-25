"""Complex-number generation: template pools (Pythagorean triples, axis angles)
and the Gemini-proposed variant (SymPy still validates)."""
import random

from engine import llm
from engine.solver import QUESTION_TYPES, format_z, z_latex
from engine.structures import _COMPLEX_CURATED_TEMPLATES


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