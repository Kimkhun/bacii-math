"""Step-by-step explanation.

`build_text()` produces a deterministic explanation directly from SymPy's steps
(always available). `explain()` optionally asks an LLM (Gemini, then Ollama) to
rewrite those steps in friendlier language; the LLM never invents new math.
"""
from sympy import I, Symbol, sympify

from engine import llm
from engine.solver import _calc_locals, inline_latex, solve


def _problem_desc(topic, question_type, params):
    if topic == "complex":
        z_sym = params["a"] + params["b"] * I
        return f"{question_type} of \\(z\\) = {inline_latex(z_sym)}"
    if topic == "limit":
        var = params["var"]
        expr = sympify(params["expr"], locals=_calc_locals(var))
        point = sympify(params["point"], locals=_calc_locals(var))
        return f"limit of {inline_latex(expr)} as \\({var} \\to {point}\\)"
    if topic == "integral":
        var = params["var"]
        expr = sympify(params["expr"], locals=_calc_locals(var))
        if question_type == "indefinite_integral":
            return f"indefinite integral of {inline_latex(expr)} with respect to \\({var}\\)"
        lower = sympify(params["lower"], locals=_calc_locals(var))
        upper = sympify(params["upper"], locals=_calc_locals(var))
        return f"integral of {inline_latex(expr)} \\(d{var}\\) from \\({var} = {lower}\\) to \\({var} = {upper}\\)"
    if topic == "probability":
        structure = params.get("structure", "?")
        want = params.get("want")
        label = f"{structure}" + (f" ({want})" if want else "")
        return f"probability word problem ({label})"
    if topic == "functions":
        var = params.get("var", "x")
        expr = sympify(params.get("function_expr"), locals=_calc_locals(var))
        return f"function study of {inline_latex(expr)}"
    return f"{question_type} with {params}"


def build_text(topic, question_type, params, solution):
    lines = [f"Problem: {_problem_desc(topic, question_type, params)}."]
    for i, step in enumerate(solution["steps"], 1):
        lines.append(f"Step {i}: {step['title']}")
        lines.append(f"    {step['detail']}")
    lines.append(f"Answer: {inline_latex(solution['answer_exact'])}")
    return "\n".join(lines)


async def explain(topic, question_type, params, use_ai=False):
    solution = solve(topic, question_type, params)
    steps_text = solution.get("solution_km") or build_text(topic, question_type, params, solution)
    ai = None
    if use_ai:
        ai, _ = await llm.narrate(steps_text)
    return {
        "question_type": question_type,
        "deterministic": steps_text,
        "ai": ai,
        "steps": solution["steps"],
        "answer": str(solution["answer_exact"]),
    }
