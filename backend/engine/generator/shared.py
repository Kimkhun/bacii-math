"""Shared builders for the topic generators: the problem-dict factory and small
expression formatters used by every ``generator/*`` module."""
from sympy import Symbol, latex, sympify


def _build_expr_problem(topic, question_type, params, difficulty, prompt, prompt_latex, display):
    return {
        "topic": topic,
        "difficulty": difficulty,
        "question_type": question_type,
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": prompt,
        "prompt_latex": prompt_latex,
        "source": "template",
    }

def _expr_latex(expr_str, var="x"):
    return latex(sympify(expr_str, locals={var: Symbol(var)}))

def _fmt_poly(p, q, r, var="x"):
    terms = []
    if p:
        terms.append(f"{p}*{var}**2" if p != 1 else f"{var}**2")
    if q:
        sign = "+" if (q > 0 and terms) else ""
        terms.append(f"{sign}{q}*{var}" if abs(q) != 1 else f"{sign}{'-' if q<0 else ''}{var}")
    if r:
        sign = "+" if (r > 0 and terms) else ""
        terms.append(f"{sign}{r}")
    return "".join(terms) or "0"