"""``generate()`` dispatcher: routes a (topic, difficulty, ...) request to the
topic's generator module. ``TOPICS`` is the authoritative topic list."""
import random
import zlib

from engine import scenarios
from engine.solver import QUESTION_TYPES_BY_TOPIC, solve as _solve

from .complex import _generate_gemini, _generate_templates
from .functions import _generate_functions
from .integrals import (
    _INDEFINITE_VARIANT_BY_DIFFICULTY,
    _INTEGRAL_VARIANT_BY_DIFFICULTY,
    _generate_indefinite,
    _generate_integral,
)
from .limits import _LIMIT_TECHNIQUES_BY_DIFFICULTY, _generate_limit
from .probability import _generate_probability


TOPICS = ("complex", "limit", "integral", "probability", "functions")
_VALID_DIFFICULTIES = ("easy", "medium", "hard")

def _generate_expr_templates(topic, difficulty, seed, question_type, variant=None):
    rng = random.Random(seed)
    allowed = {
        "limit": ("limit",),
        "integral": ("definite_integral", "indefinite_integral"),
    }[topic]
    qt = question_type or (rng.choice(allowed) if len(allowed) > 1 else allowed[0])
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
        return _generate_probability(random.Random(seed), difficulty, question_type, variant)

    if topic == "functions":
        return _generate_functions(random.Random(seed), difficulty, question_type)

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
                        solution = _solve(topic, problem["question_type"], problem["params"])
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