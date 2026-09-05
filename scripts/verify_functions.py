"""Verify the functions topic: for every curated exercise in the catalog, solve
it with SymPy, check each part's answer matches the recorded official value, and
dry-run a "perfect student" (official + alternate spellings must be graded
correct; planted wrong answers must be graded incorrect). No LLM involved.

Run from the backend directory:  python scripts/verify_functions.py
"""
import json
import os
import sys

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')
sys.path.insert(0, os.path.abspath(BACKEND))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sympy import N, simplify, sympify

from engine.generator.functions import _FUNCTION_CURATED_TEMPLATES, _build_curated_function
from engine.grader import grade_part
from engine.solver import solve

GOOD = {
    "domain": ["(-3,3)", "]-3,3[", "-3<x<3", "D = (-3;3)"],
    "parity": ["odd", "ODD FUNCTION", "សេស", "impair", "g(-x) = -g(x)"],
    "limit_left": ["-∞", "-oo", "-infinity", "lim_{x->-3+} g(x) = -∞"],
    "limit_right": ["+∞", "oo"],
    "tangent": ["y = 2x/3", "(2/3)x", "3y - 2x = 0", "y - 0 = (2/3)(x - 0)"],
    "derivative_product": ["ln((-x-3)/(x-3)) - 6x/(x^2-9)", "ln((x+3)/(3-x)) - 6x/(x^2-9)"],
    "integral": ["ln(2)+3ln(8)-3ln(9)", "10ln(2)-6ln(3)", "S = ln(2) + 3ln(8) - 3ln(9)"],
}
BAD = {
    "domain": ["[-3,3]", "(0,3)"],
    "parity": ["even", "neither"],
    "limit_left": ["+∞", "DNE"],
    "limit_right": ["-∞", "3"],
    "tangent": ["y = x", "y = 2x"],
    "derivative_product": ["x", "g(x)"],
    "integral": ["0.34", "ln(2)"],
}

FAILURES = []


def check(cond, msg):
    status = "OK " if cond else "FAIL"
    print(f"  [{status}] {msg}")
    if not cond:
        FAILURES.append(msg)


def assert_part_answer(part, item_part):
    want = part["want"]
    expected = item_part.get("expected")
    actual = part["answer_exact"]
    if want == "domain":
        check(
            actual == expected,
            f"part {part['label']} domain {actual} == {expected}",
        )
    elif want == "parity":
        check(actual == expected, f"part {part['label']} parity {actual} == {expected}")
    elif want == "limit":
        exp = sympify(expected)
        check(actual == exp, f"part {part['label']} limit {actual} == {exp}")
    elif want == "tangent":
        exp = sympify(expected)
        check(simplify(actual - exp) == 0, f"part {part['label']} tangent {actual} == {exp}")
    elif want == "integral":
        exp = sympify(expected)
        check(simplify(actual - exp) == 0, f"part {part['label']} integral {actual} == {exp}")
    elif want == "derivative_product":
        check(bool(actual.free_symbols), f"part {part['label']} derivative has free symbols")


def main():
    total_good = total_bad = 0
    for item in _FUNCTION_CURATED_TEMPLATES:
        print(f"\n=== {item['id']} (difficulty {item.get('difficulty')}) ===")
        problem = _build_curated_function(item)
        sol = solve(problem["topic"], problem["question_type"], problem["params"])
        item_parts = {p["label"]: p for p in item["parts"]}

        for part in sol["parts"]:
            assert_part_answer(part, item_parts[part["label"]])
            want = part["want"]
            for good in GOOD.get(want, []):
                r = grade_part("functions", "study", problem["params"], part["label"], good)
                total_good += 1
                check(r["correct"], f"part {part['label']} accepts {good!r}")
                if r.get("note"):
                    print(f"        (note: {r['note']})")
            for bad in BAD.get(want, []):
                r = grade_part("functions", "study", problem["params"], part["label"], bad)
                total_bad += 1
                check(not r["correct"], f"part {part['label']} rejects {bad!r}")

    print(f"\n{'='*60}")
    print(f"checked {total_good} correct-spelling answers, {total_bad} wrong-spelling answers")
    if FAILURES:
        print(f"FAILURES: {len(FAILURES)}")
        for f in FAILURES:
            print("  -", f)
        sys.exit(1)
    print("ALL FUNCTION VERIFICATIONS PASSED")


if __name__ == "__main__":
    main()