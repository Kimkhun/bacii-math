"""Parsing and judging of user answers against the SymPy-computed expected value.

The generic core shared by every topic: answer parsing, numeric/exact equivalence,
and step-by-step work checking (``analyze_work``). Probability's multi-part
grading lives in ``grader.probability``.
"""
import math
import re as _re

from sympy import E, I, N, Symbol, binomial, im, latex, pi, re, simplify, sqrt
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from ..solver import solve


_LOCAL = {"I": I, "i": I, "pi": pi, "e": E, "sqrt": sqrt, "binomial": binomial}
_TRANS = standard_transformations + (implicit_multiplication_application, convert_xor)

_DEFAULT_TOL = 1e-4

# Leading limit notation from the OCR, e.g. "lim_{x -> -2} (x^2-4)/(x+2)" or
# "lim(x->-2) (x^2-4)/(x+2)" or "lim_{x \to -2} (...)": strip it so the
# expression itself can be parsed and checked.
_LIM_PREFIX = _re.compile(
    r"^\s*lim\s*(?:"
    r"_\s*\{\s*[A-Za-z]\s*(?:->|→|\\to)\s*[^}]+\}\s*|"
    r"\(\s*[A-Za-z]\s*(?:->|→|\\to)\s*[^)]+\)\s*"
    r")?"
)

# Probability "C(6,2)"-style combination notation -> SymPy binomial. Only
# matches integer-argument C(,) tokens, so a lone "+C" (integration constant)
# is never touched.
_COMB_NOTATION = _re.compile(r"\bC\(\s*(\d+)\s*,\s*(\d+)\s*\)")

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
    text = _LIM_PREFIX.sub("", text)
    text = _re.sub(r"√\s*(\d+(?:\.\d+)?)", r"sqrt(\1)", text)
    text = text.replace("√", "sqrt")
    text = _COMB_NOTATION.sub(r"binomial(\1, \2)", text)
    return parse_expr(text, local_dict=_LOCAL, transformations=_TRANS)

def _numeric_close(user, expected, tol):
    try:
        u = N(user)
        e = N(expected)
        if u.is_real and e.is_real:
            return abs(float(u) - float(e)) <= tol
        dr = float(N(re(user) - re(expected)))
        di = float(N(im(user) - im(expected)))
        return abs(dr) <= tol and abs(di) <= tol
    except (TypeError, ValueError):
        return False

def _angle_close(user, expected, tol):
    d = float(N(user - expected))
    d = (d + math.pi) % (2 * math.pi) - math.pi
    return abs(d) <= tol

# --- hybrid equivalence (CAS + numeric safety net) ---
#
# `simplify` is not a decision procedure: exotic equivalent forms (trig/exponential
# disguises) can fail to reduce to 0 / "no variable". The ladder below escalates
# only when needed: exact simplify, trig-intensified simplify (fu), then numeric
# sampling at deliberately non-special points (0.37, 1.23, ... — two non-equal
# high-school expressions agreeing at all of them is effectively impossible).

_SAMPLE_POINTS = (0.37, 1.23, 2.71, 3.87, 5.03)
_SAMPLE_TOL = 1e-6

def _sample_values(expr, var):
    """Evaluate expr at the sample points, skipping poles/non-real results."""
    vals = []
    for p in _SAMPLE_POINTS:
        try:
            v = N(expr.subs(var, p))
        except Exception:
            continue
        if not v.is_real or not v.is_finite:
            continue
        vals.append(float(v))
    return vals

def _equivalent_const(value, expected, var, diff=None):
    """True when value == expected + constant (in var) — the rule for any
    antiderivative line (constants cancel in F(b) − F(a))."""
    try:
        if diff is None:
            diff = simplify(value - expected)
        if not diff.has(var):
            return True
        if not simplify(diff, fu=True).has(var):
            return True
        vals = _sample_values(diff, var)
        return len(vals) >= 3 and all(abs(v - vals[0]) <= _SAMPLE_TOL for v in vals[1:])
    except Exception:
        return False

def _equivalent_exact(value, expected, var, diff=None):
    """True when value == expected exactly, via the same hybrid ladder."""
    try:
        if value == expected:
            return True
        if diff is None:
            diff = simplify(value - expected)
        if diff == 0:
            return True
        if simplify(diff, fu=True) == 0:
            return True
        vals = _sample_values(diff, var)
        return len(vals) >= 3 and all(abs(v) <= _SAMPLE_TOL for v in vals)
    except Exception:
        return False

def _is_given_restatement(lhs: str) -> bool:
    return lhs.strip().lower() in ("z", "z bar", "z_bar", "z̄")

def analyze_work(topic, question_type, params, lines, tolerance=None) -> dict:
    """Deterministically check each line of a student's work against the SymPy-computed
    checkpoints for this solution. Returns the first line whose claimed value
    doesn't match the correct value at that point in the solution — a verified fact, not
    an LLM guess. Lines that don't parse, or that just restate the given z, are skipped
    rather than flagged (SymPy can't judge a definition, only a computation).

    Every checkpoint also carries the `formula` it exercises, so the same pass yields
    `formula_breakdown` — per-formula reached/missed data used for weakness stats.

    Matching strategy is per-topic via the solution's `work_mode`:
      - default (complex, limits, integrals, ...): strict sequential pointer — a
        line is checked against the next expected checkpoint in order.
      - "any_order" (probability): a line matches any checkpoint value (exact, then
        numeric), so the natural count/ratio ordering and repeated-equivalent
        expansion lines all verify; formula-definition and jot lines (symbolic or
        non-real values) are skipped rather than flagged.
    """
    tol = tolerance if tolerance is not None else _DEFAULT_TOL
    solution = solve(topic, question_type, params)
    if solution.get("work_mode") == "any_order":
        return _analyze_work_any_order(solution, params, lines, tol)
    given_expr = solution.get("given")
    checkpoints = list(solution.get("checkpoints", []))
    if not checkpoints or checkpoints[-1]["value"] != solution["answer_exact"]:
        checkpoints.append({"label": "final answer", "value": solution["answer_exact"], "formula": None})

    line_results = []
    pointer = 0
    first_error_line = None
    matched_checkpoints = set()

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

        if given_expr is not None and value == given_expr:
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "given"})
            continue

        matched_idx = None
        var_sym = Symbol(params.get("var", "x"))
        for idx in range(pointer, len(checkpoints)):
            expected = checkpoints[idx]["value"]
            try:
                diff = simplify(value - expected)
                ok = diff == 0 or _numeric_close(value, expected, tol)
                if not ok and checkpoints[idx].get("constant_ok"):
                    # Antiderivative checkpoints: any F(x) + constant is a valid
                    # antiderivative (constants cancel in F(b) − F(a)). The diff
                    # is already computed; the fu/sampling escalation happens
                    # only here, so numeric checkpoints never pay for it.
                    ok = _equivalent_const(value, expected, var_sym, diff=diff)
            except Exception:
                ok = False
            if ok:
                matched_idx = idx
                break

        if matched_idx is not None:
            label = checkpoints[matched_idx]["label"]
            matched_checkpoints.add(matched_idx)
            line_results.append({
                "line": i,
                "text": raw,
                "checked": True,
                "correct": True,
                "matches": label,
                "formula": checkpoints[matched_idx].get("formula"),
                "expected": str(checkpoints[matched_idx]["value"]),
            })
            pointer = matched_idx + 1
        else:
            target = checkpoints[pointer] if pointer < len(checkpoints) else None
            line_results.append({
                "line": i,
                "text": raw,
                "checked": True,
                "correct": False,
                "formula": target.get("formula") if target else None,
                "expected": str(target["value"]) if target else None,
            })
            if first_error_line is None:
                first_error_line = i

    formula_breakdown = []
    for idx, cp in enumerate(checkpoints):
        if cp.get("formula"):
            formula_breakdown.append({
                "formula": cp["formula"],
                "label": cp["label"],
                "reached": idx in matched_checkpoints,
                "line": next((r["line"] for r in line_results if r.get("matches") == cp["label"]), None),
            })

    return {
        "line_results": line_results,
        "first_error_line": first_error_line,
        "reached_final_answer": pointer >= len(checkpoints),
        "formula_breakdown": formula_breakdown,
    }

def _analyze_work_any_order(solution, params, lines, tol):
    """Probability's work-checking mode.

    Matches each line against ANY checkpoint value (exact, then numeric) instead
    of a strict sequence, so students writing the natural count/ratio order, or
    chains of equivalent expansion lines (`= 10 * 5 = 50`), all verify. Lines that
    parse to a symbolic expression (formula definitions like (n!)/(r!(n-r)!)) or
    to a non-real value (jot lines like "7 7 1,3,5,7") are skipped rather than
    flagged — they're restatements, not computations. The authoritative verdicts
    are the per-part final answers from `grade`/`grade_part`; this only drives
    the red-pen overlay and formula_breakdown."""
    given_expr = solution.get("given")
    checkpoints = list(solution.get("checkpoints", []))
    if not checkpoints or checkpoints[-1]["value"] != solution["answer_exact"]:
        checkpoints.append({"label": "final answer", "value": solution["answer_exact"], "formula": None})

    line_results = []
    first_error_line = None
    matched_checkpoints = set()

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
        if given_expr is not None and value == given_expr:
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "given"})
            continue
        # Symbolic or non-real lines are formula definitions / jotted sets, not
        # computed checkpoints — never mark them wrong.
        try:
            symbolic = bool(value.free_symbols) or not value.is_number or value.is_real is False
        except AttributeError:
            symbolic = True  # e.g. parse returned a plain tuple from "7 7 1,3,5,7"
        if symbolic:
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "symbolic"})
            continue

        best_idx = None
        for idx, cp in enumerate(checkpoints):
            try:
                if simplify(value - cp["value"]) == 0:
                    best_idx = idx
                    break
            except Exception:
                continue
        if best_idx is None:
            for idx, cp in enumerate(checkpoints):
                if _numeric_close(value, cp["value"], tol):
                    best_idx = idx
                    break
        if best_idx is not None:
            matched_checkpoints.add(best_idx)
            line_results.append({
                "line": i,
                "text": raw,
                "checked": True,
                "correct": True,
                "matches": checkpoints[best_idx]["label"],
                "formula": checkpoints[best_idx].get("formula"),
                "expected": str(checkpoints[best_idx]["value"]),
            })
        else:
            line_results.append({
                "line": i,
                "text": raw,
                "checked": True,
                "correct": False,
                "formula": None,
                "expected": None,
            })
            if first_error_line is None:
                first_error_line = i

    formula_breakdown = []
    for idx, cp in enumerate(checkpoints):
        if cp.get("formula"):
            formula_breakdown.append({
                "formula": cp["formula"],
                "label": cp["label"],
                "reached": idx in matched_checkpoints,
                "line": next((r["line"] for r in line_results if r.get("matches") == cp["label"]), None),
            })

    return {
        "line_results": line_results,
        "first_error_line": first_error_line,
        "reached_final_answer": len(matched_checkpoints) >= len(checkpoints),
        "formula_breakdown": formula_breakdown,
    }

def grade_part(topic, question_type, params, label, user_answer, tolerance=None):
    """Grade one sub-part of a multi-part exercise (the progressive flow: check
    A, then B, then C). Accepts a bare value or a label-prefixed value."""
    from .probability import _judge_value

    solution = solve(topic, question_type, params)
    part = next((p for p in solution.get("parts", []) if p["label"] == label), None)
    if part is None:
        raise ValueError(f"unknown part label: {label}")
    m = _re.match(rf"^\s*{_re.escape(str(label))}\s*[:=]\s*(.+)$", user_answer)
    if m:
        user_answer = m.group(1)
    expected = part["answer_exact"]
    try:
        correct, reason = _judge_value(expected, user_answer, tolerance if tolerance is not None else _DEFAULT_TOL)
        given = str(parse_answer(user_answer))
    except Exception as exc:
        correct, reason, given = False, f"could not parse answer: {exc}", user_answer
    verdict = {
        "label": label,
        "correct": correct,
        "reason": reason,
        "given": given,
        "expected": str(expected),
        "answer_decimal": part["answer_decimal"],
    }
    return {
        **verdict,
        "part": label,
        "parts": [verdict],
        "expected_latex": latex(expected),
        "steps": solution["steps"],
        "all_complete": correct and str(solution.get("target_label")) == str(label),
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

    var_sym = Symbol(params.get("var", "x"))
    if question_type == "indefinite_integral":
        # Any F(x) + constant is a valid antiderivative — decide here alone,
        # never fall through to the numeric branches (symbolic F can't be
        # converted to a float).
        verdict = _equivalent_const(user, expected, var_sym)
        reason = "indefinite" if verdict else "mismatch"
    elif _equivalent_exact(user, expected, var_sym):
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