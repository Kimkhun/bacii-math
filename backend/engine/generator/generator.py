"""``generate()`` dispatcher: routes a (topic, difficulty, ...) request to the
topic's generator module. ``TOPICS`` is the authoritative topic list."""
import random

from .complex import _generate_gemini, _generate_templates
from .integrals import _generate_indefinite, _generate_integral
from .limits import _LIMIT_VARIANT_BY_DIFFICULTY, _generate_limit
from .probability import _generate_probability


TOPICS = ("complex", "limit", "integral", "probability")

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