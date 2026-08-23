#!/usr/bin/env python3
"""Compute exact answers for the full BAC II integral exercise set with SymPy.

Reads the transcription data (scripts/integrals_part1.py, integrals_part2.py),
integrates everything, prints a per-exercise report, and writes
data/bacii-exam/integrals/answers.json {label: answer} for reference.
"""
import json
import os
import sys

import sympy as sp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integrals_part1 import PART1, PART2
from integrals_part2 import PART3_S1, PART3_S2, PART3_S3, PART3_S4

LOC = {"pi": sp.pi, "oo": sp.oo, "sqrt": sp.sqrt, "e": sp.E, "ln": sp.log}


def sym(expr, var):
    return sp.sympify(expr, locals={var: sp.Symbol(var), **LOC})


def main():
    out = {}
    failures = []

    def report(label, var, expr, bounds):
        try:
            f = sym(expr, var)
            if bounds is None:
                ans = sp.integrate(f, sp.Symbol(var))
                kind = "indef"
            else:
                lo, hi = bounds
                ans = sp.integrate(f, (sp.Symbol(var), sym(lo, var), sym(hi, var)))
                kind = "def"
            print(f"  {label:7} {kind:5} = {ans}")
            out[label] = {"var": var, "expr": expr, "bounds": bounds, "answer": str(ans)}
        except Exception as exc:
            failures.append((label, expr, str(exc)))
            print(f"  {label:7} FAILED: {exc}")

    print("== Part I (indefinite basics) ==")
    for label, var, expr in PART1:
        report(label, var, expr, None)
    print("== Part II (indefinite u-sub/linear arg) ==")
    for label, var, expr in PART2:
        report(label, var, expr, None)
    print("== Part III S1 ==")
    for label, var, expr, b in PART3_S1:
        report(label, var, expr, b)
    print("== Part III S2 ==")
    for label, var, expr, b in PART3_S2:
        report(label, var, expr, b)
    print("== Part III S3 ==")
    for label, var, expr, b in PART3_S3:
        report(label, var, expr, b)
    print("== Part III S4 (by parts) ==")
    for label, var, expr, b in PART3_S4:
        report(label, var, expr, b)

    total = len(PART1) + len(PART2) + len(PART3_S1) + len(PART3_S2) + len(PART3_S3) + len(PART3_S4)
    print(f"\nTotal: {total} exercises, {total - len(failures)} computed, {len(failures)} failed")
    if failures:
        for label, expr, err in failures:
            print(f"  FAIL {label} {expr}: {err}")

    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bacii-exam", "integrals", "answers.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"answers written to {dest}")


if __name__ == "__main__":
    main()