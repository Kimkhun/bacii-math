"""``solve()`` dispatcher: routes a (topic, question_type, params) to the topic
module that owns the SymPy computation, plus ``serialize()`` for the HTTP API."""
from .complex import _solve_complex
from .functions import _solve_function_study
from .integrals import _solve_definite_integral, _solve_indefinite_integral
from .limits import _solve_limit
from .probability import _solve_probability


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
        return _solve_probability(params)
    if topic == "functions":
        return _solve_function_study(params)
    raise ValueError(f"unknown topic: {topic}")
def serialize(solution):
    return {
        "answer_exact": str(solution["answer_exact"]),
        "answer_decimal": solution["answer_decimal"],
        "answer_latex": solution["answer_latex"],
        "steps": solution["steps"],
    }