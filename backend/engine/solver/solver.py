"""``solve()`` dispatcher: routes a (topic, question_type, params) to the topic
module that owns the SymPy computation, plus ``serialize()`` for the HTTP API."""
from .complex import _solve_complex
from .conics import _solve_conic
from .continuity import _solve_continuity
from .counting import _solve_counting
from .derivatives import _solve_derivative
from .differential_equations import _solve_differential_equation
from .functions import _solve_function_study
from .integrals import _solve_definite_integral, _solve_indefinite_integral
from .limits import _solve_limit
from .probability import _solve_probability
from .vectors_space import _solve_vector_ops


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