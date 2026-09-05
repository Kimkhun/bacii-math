"""``solve()``/``generate()`` dispatchers: route a (topic, question_type, ...)
request to the ``engine.topics.<topic>`` package that owns it, plus
``serialize()`` for the HTTP API and ``variants_for_formula()`` for the
adaptive-practice "practice this formula" links.
"""
import random
import zlib

from ..topics.complex.generator import _generate_gemini, _generate_templates
from ..topics.complex.solver import _solve_complex
from ..topics.conics.generator import _generate_conics
from ..topics.conics.solver import _solve_conic
from ..topics.continuity.generator import _generate_continuity
from ..topics.continuity.solver import _solve_continuity
from ..topics.derivatives.generator import _generate_derivatives
from ..topics.derivatives.solver import _solve_derivative
from ..topics.differential_equations.generator import _generate_differential_equations
from ..topics.differential_equations.solver import _solve_differential_equation
from ..topics.functions.generator import _generate_functions
from ..topics.functions.solver import _solve_function_study
from ..topics.integral.generator import (
    _INDEFINITE_VARIANT_BY_DIFFICULTY,
    _INTEGRAL_VARIANT_BY_DIFFICULTY,
    _generate_indefinite,
    _generate_integral,
)
from ..topics.integral.solver import _solve_definite_integral, _solve_indefinite_integral
from ..topics.limit.generator import _LIMIT_TECHNIQUES_BY_DIFFICULTY, _generate_limit
from ..topics.limit.solver import _solve_limit
from ..topics.probability import scenarios
from ..topics.probability.counting import _generate_counting, _solve_counting
from ..topics.probability.generator import _generate_probability
from ..topics.probability.solver import _solve_probability
from ..topics.vectors_space.generator import _generate_vectors_space
from ..topics.vectors_space.solver import _solve_vector_ops
from .shared import QUESTION_TYPES_BY_TOPIC


def solve(topic, question_type, params):
    if topic == "complex":
        return _solve_complex(question_type, params)
    if topic == "limit":
        return _solve_limit(params)
    if topic == "integral":
        if question_type == "indefinite_integral":
            return _solve_indefinite_integral(params)
        return _solve_definite_integral(params)
    if topic == "probability":
        if question_type == "counting":
            return _solve_counting(params)
        return _solve_probability(params)
    if topic == "functions":
        return _solve_function_study(params)
    if topic == "continuity":
        return _solve_continuity(params)
    if topic == "derivatives":
        return _solve_derivative(params)
    if topic == "differential_equations":
        return _solve_differential_equation(params)
    if topic == "vectors_space":
        return _solve_vector_ops(params)
    if topic == "conics":
        return _solve_conic(params)
    raise ValueError(f"unknown topic: {topic}")


def serialize(solution):
    return {
        "answer_exact": str(solution["answer_exact"]),
        "answer_decimal": solution["answer_decimal"],
        "answer_latex": solution["answer_latex"],
        "steps": solution["steps"],
    }


TOPICS = (
    "complex", "limit", "integral", "probability", "functions",
    "continuity", "derivatives", "differential_equations", "vectors_space", "conics",
)
_VALID_DIFFICULTIES = ("easy", "medium", "hard")

def _generate_expr_templates(topic, difficulty, seed, question_type, variant=None):
    rng = random.Random(seed)
    allowed = {
        "limit": ("limit",),
        "integral": ("definite_integral", "indefinite_integral"),
    }[topic]
    qt = question_type or allowed[0]
    if qt not in allowed:
        raise ValueError(f"question_type {qt} does not match topic {topic}")
    if difficulty not in _VALID_DIFFICULTIES:
        raise ValueError(f"unknown difficulty: {difficulty}")

    if topic == "limit":
        return _generate_limit(rng, difficulty, variant)
    if qt == "indefinite_integral":
        return _generate_indefinite(rng, difficulty, variant)
    return _generate_integral(rng, difficulty, variant)

async def generate(topic="complex", difficulty="medium", seed=None, question_type=None, generation_mode="templates", variant=None):
    if topic not in TOPICS:
        raise ValueError(f"unknown topic: {topic}")

    if topic == "probability":
        if question_type == "counting":
            return _generate_counting(random.Random(seed), difficulty)
        return _generate_probability(random.Random(seed), difficulty, question_type, variant)

    if topic == "functions":
        return _generate_functions(random.Random(seed), difficulty, question_type)

    if topic == "continuity":
        return _generate_continuity(random.Random(seed), difficulty, question_type)

    if topic == "derivatives":
        return _generate_derivatives(random.Random(seed), difficulty, question_type)

    if topic == "differential_equations":
        return _generate_differential_equations(random.Random(seed), difficulty, question_type)

    if topic == "vectors_space":
        return _generate_vectors_space(random.Random(seed), difficulty, question_type)

    if topic == "conics":
        return _generate_conics(random.Random(seed), difficulty, question_type)

    if topic in ("limit", "integral"):
        return _generate_expr_templates(topic, difficulty, seed, question_type, variant)

    if generation_mode == "gemini":
        problem = await _generate_gemini(difficulty)
        if problem is not None:
            return problem
    return _generate_templates(difficulty, seed, question_type)


# ---------------------------------------------------------------------------
# formula tag -> variant index, for adaptive practice ("Practice this formula"
# links on /formulas and /stats, and the ?formula=<id> forced-practice mode).
# Built lazily on first use by generating + solving one deterministic sample
# per (topic, question_type, difficulty, variant) combination and recording
# every formula_tag each sample's solution touches. Cached in-process; a
# formula can legitimately come from several variants, so callers get the
# full list back and choose (e.g. prefer a difficulty match).
# ---------------------------------------------------------------------------

_VARIANT_INDEX = None


def _variants_for(topic, question_type, difficulty):
    if topic == "integral" and question_type == "definite_integral":
        return _INTEGRAL_VARIANT_BY_DIFFICULTY.get(difficulty, [])
    if topic == "integral" and question_type == "indefinite_integral":
        return _INDEFINITE_VARIANT_BY_DIFFICULTY.get(difficulty, [])
    if topic == "limit":
        return _LIMIT_TECHNIQUES_BY_DIFFICULTY.get(difficulty, [])
    if topic == "probability":
        return list(scenarios.VARIANT_BY_DIFFICULTY.get(difficulty, ()))
    return [None]


async def _build_variant_index():
    index: dict[str, list[dict]] = {}
    for topic in TOPICS:
        for qt in QUESTION_TYPES_BY_TOPIC.get(topic, ()):
            for difficulty in _VALID_DIFFICULTIES:
                for variant in _variants_for(topic, qt, difficulty) or [None]:
                    seed = zlib.crc32(f"{topic}:{qt}:{difficulty}:{variant}".encode()) & 0xFFFFFFFF
                    try:
                        problem = await generate(
                            topic, difficulty, seed=seed, question_type=qt,
                            generation_mode="templates", variant=variant,
                        )
                        solution = solve(topic, problem["question_type"], problem["params"])
                    except Exception:
                        continue
                    ref = {"topic": topic, "question_type": qt, "variant": variant, "difficulty": difficulty}
                    for tag in solution.get("formula_tags") or []:
                        index.setdefault(tag, []).append(ref)
    return index


async def variants_for_formula(tag: str) -> list[dict]:
    """All (topic, question_type, variant, difficulty) refs that produced a
    question touching formula `tag`, most-recently-built index. Empty list if
    the formula has no known generator variant (e.g. curated-only)."""
    global _VARIANT_INDEX
    if _VARIANT_INDEX is None:
        _VARIANT_INDEX = await _build_variant_index()
    return _VARIANT_INDEX.get(tag, [])
