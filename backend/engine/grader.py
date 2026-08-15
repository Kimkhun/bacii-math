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


def _is_given_restatement(lhs: str) -> bool:
    return lhs.strip().lower() in ("z", "z bar", "z_bar", "z̄")


def analyze_work(topic, question_type, params, lines, tolerance=None) -> dict:
    """Deterministically check each line of a student's work against the SymPy-computed
    checkpoints for this solution, in order. Returns the first line whose claimed value
    doesn't match the correct value at that point in the solution — a verified fact, not
    an LLM guess. Lines that don't parse, or that just restate the given z, are skipped
    rather than flagged (SymPy can't judge a definition, only a computation).

    Checkpoints are only populated for some question types (currently modulus); when
    absent, only the final answer is checked.
    """
    tol = tolerance if tolerance is not None else _DEFAULT_TOL
    solution = solve(topic, question_type, params)
    checkpoints = list(solution.get("checkpoints", [])) + [("final answer", solution["answer_exact"])]

    line_results = []
    pointer = 0
    first_error_line = None

    for i, raw in enumerate(lines, 1):
        text = raw.strip()
        if not text:
            continue

        if "=" in text:
            lhs, _, value_str = text.rpartition("=")
            if _is_given_restatement(lhs):
                line_results.append({"line": i, "text": raw, "checked": False, "reason": "given"})
                continue
        else:
            value_str = text

        try:
            value = parse_answer(value_str)
        except Exception:
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "unparsed"})
            continue

        matched_label = None
        for idx in range(pointer, len(checkpoints)):
            label, expected = checkpoints[idx]
            try:
                ok = simplify(value - expected) == 0 or _numeric_close(value, expected, tol)
            except Exception:
                ok = False
            if ok:
                matched_label = label
                pointer = idx + 1
                break

        if matched_label is not None:
            line_results.append({"line": i, "text": raw, "checked": True, "correct": True, "matches": matched_label})
        else:
            line_results.append({"line": i, "text": raw, "checked": True, "correct": False})
            if first_error_line is None:
                first_error_line = i

    return {
        "line_results": line_results,
        "first_error_line": first_error_line,
        "reached_final_answer": pointer >= len(checkpoints),
    }


def grade(topic, question_type, params, user_answer, tolerance=None):
    tol = tolerance if tolerance is not None else _DEFAULT_TOL
    solution = solve(topic, question_type, params)
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
