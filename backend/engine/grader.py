"""Parsing and judging of user answers against the SymPy-computed expected value."""
import math
import re as _re

from sympy import E, I, N, im, latex, pi, re, simplify, sqrt
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from .solver import solve

_LOCAL = {"I": I, "i": I, "pi": pi, "e": E, "sqrt": sqrt}
_TRANS = standard_transformations + (implicit_multiplication_application, convert_xor)

_DEFAULT_TOL = 1e-4


def parse_answer(text):
    text = text.strip()
    if not text:
        raise ValueError("empty answer")
    text = (
        text.replace("π", "pi")
        .replace("×", "*")
        .replace("÷", "/")
        .replace("–", "-")
    )
    text = _re.sub(r"√\s*(\d+(?:\.\d+)?)", r"sqrt(\1)", text)
    text = text.replace("√", "sqrt")
    return parse_expr(text, local_dict=_LOCAL, transformations=_TRANS)


def _numeric_close(user, expected, tol):
    u = N(user)
    e = N(expected)
    if u.is_real and e.is_real:
        return abs(float(u) - float(e)) <= tol
    dr = float(N(re(user) - re(expected)))
    di = float(N(im(user) - im(expected)))
    return abs(dr) <= tol and abs(di) <= tol


def _angle_close(user, expected, tol):
    d = float(N(user - expected))
    d = (d + math.pi) % (2 * math.pi) - math.pi
    return abs(d) <= tol


def grade(question_type, a, b, user_answer, tolerance=None):
    tol = tolerance if tolerance is not None else _DEFAULT_TOL
    solution = solve(question_type, a, b)
    expected = solution["answer_exact"]

    try:
        user = parse_answer(user_answer)
    except Exception as exc:
        return {
            "correct": False,
            "reason": f"could not parse answer: {exc}",
            "given": user_answer,
            "expected": str(expected),
            "answer_decimal": solution["answer_decimal"],
            "steps": solution["steps"],
        }

    if simplify(user - expected) == 0:
        verdict, reason = True, "exact"
    elif question_type == "argument" and _angle_close(user, expected, tol):
        verdict, reason = True, "numeric"
    elif _numeric_close(user, expected, tol):
        verdict, reason = True, "numeric"
    else:
        verdict, reason = False, "mismatch"

    return {
        "correct": verdict,
        "reason": reason,
        "given": str(user),
        "expected": str(expected),
        "expected_latex": latex(expected),
        "answer_decimal": solution["answer_decimal"],
        "steps": solution["steps"],
    }
