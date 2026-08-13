"""Step-by-step explanation.

`build_text()` produces a deterministic explanation directly from SymPy's steps
(always available). `explain()` optionally asks an LLM (Gemini, then Ollama) to
rewrite those steps in friendlier language; the LLM never invents new math.
"""
from engine import llm
from engine.solver import format_z, solve


def build_text(question_type, a, b, solution):
    z = format_z(a, b)
    lines = [f"Problem: {question_type} of z = {z}."]
    for i, step in enumerate(solution["steps"], 1):
        lines.append(f"Step {i}: {step['title']}")
        lines.append(f"    {step['detail']}")
    lines.append(f"Answer: {solution['answer_exact']}")
    return "\n".join(lines)


async def explain(question_type, a, b, use_ai=False):
    solution = solve(question_type, a, b)
    steps_text = build_text(question_type, a, b, solution)
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
