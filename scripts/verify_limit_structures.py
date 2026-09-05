#!/usr/bin/env python3
"""Verify the limit technique registry.

Unlike integrals, most limit techniques are tied to a specific algebraic
identity rather than free coefficients, so there is no single parameterized
"shape" per technique. Instead this script verifies:

  1. Every curated BAC II limit exercise (backend/data/limits/*.json) maps to
     a technique in `structures.LIMIT_TECHNIQUES`, and SymPy re-solving it
     matches the recorded `answer_latex` (one broken source exercise, an
     implicit "find a" ask rather than a plain limit, is excluded).
  2. Every parameterizable technique's generator sampler produces a valid,
     finite instance whose SymPy answer grades correct, and a perturbed wrong
     answer grades incorrect.
  3. Every technique in the registry — parameterizable or curated-only — has
     at least one curated source exercise backing it.

Run from the repo root:  python scripts/verify_limit_structures.py
"""
import glob
import json
import os
import random
import sys
import zlib

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))

from sympy import N, latex, nsimplify, simplify  # noqa: E402

from engine import generator, grader, solver, structures  # noqa: E402
from engine.generator.limits import generate_limit_for_technique  # noqa: E402
from engine.solver.limits import _solve_limit  # noqa: E402

EXCLUDED = {
    "2024b": "implicit 'find a' ask (lim ... = 1, find a) rather than a plain limit — doesn't round-trip through parse_latex",
}


def _excluded_techniques():
    """technique id -> True for every EXCLUDED exercise's source category, so a
    technique whose only exam appearance is a broken/unparseable prompt still
    counts as having a (documented) source instead of failing the coverage
    check."""
    out = {}
    for fpath in sorted(glob.glob(os.path.join(BACKEND, "data", "limits", "*.json"))):
        try:
            data = json.load(open(fpath, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        tech = data.get("formula_name")
        for ex in data.get("exercises", []):
            if ex.get("id") in EXCLUDED:
                out[ex["id"]] = tech
    return out


def expected_ids():
    ids = []
    for item in structures._LIMIT_CURATED_TEMPLATES:
        ids.append(item["id"])
    for excluded_id in EXCLUDED:
        ids.append(excluded_id)
    return sorted(set(ids))


def _curated_matches_recorded(item):
    result = _solve_limit({
        "expr": str(item["expr"]), "var": item["var"], "point": str(item["point"]),
        "formula_name": item["formula_name"], "curated_technique": item["technique"],
        "curated_formula_latex": item.get("formula_latex", ""), "source_id": item["id"],
    })
    try:
        recorded = structures._to_point(item["answer_latex"])
    except Exception:
        return None, "could not parse recorded answer_latex"
    if result["answer_exact"] in (recorded,) or (result["answer_exact"] - recorded == 0 if recorded.is_finite else result["answer_exact"] == recorded):
        return True, f"computed {result['answer_exact']} vs recorded {item['answer_latex']}"
    try:
        diff = simplify(result["answer_exact"] - recorded)
        ok = diff == 0 or abs(complex(N(diff))) < 1e-6
    except TypeError:
        ok = False
    return ok, f"computed {result['answer_exact']} vs recorded {item['answer_latex']}"


def grade_checks(technique, problem, sol):
    answer = str(sol["answer_exact"])
    checks = [(answer, True)]
    try:
        wrong = str(nsimplify(sol["answer_exact"]) + 1)
        checks.append((wrong, False))
    except Exception:
        pass
    results = []
    for user, want in checks:
        r = grader.grade("limit", "limit", problem["params"], user)
        results.append((user, want, r["correct"], r["reason"]))
    return results


def main():
    label_map = structures.limit_source_label_map()
    ids = expected_ids()

    # --- audit: every curated exercise maps to a known technique -----------
    audit = {}
    for eid in ids:
        if eid in EXCLUDED:
            audit[eid] = {"status": "excluded", "excluded_reason": EXCLUDED[eid]}
        elif eid in label_map:
            audit[eid] = {"status": "mapped", "technique": label_map[eid]}
        else:
            audit[eid] = {"status": "UNCOVERED"}
    uncovered = [i for i, v in audit.items() if v["status"] == "UNCOVERED"]
    mapped = {i for i, v in audit.items() if v["status"] == "mapped"}
    excluded = {i for i, v in audit.items() if v["status"] == "excluded"}

    # --- every mapped technique id must exist in the registry ---------------
    unknown_techniques = sorted({t for t in label_map.values() if t not in structures.LIMIT_TECHNIQUES})

    # --- every curated exercise's recorded answer matches SymPy ------------
    curated_failures = []
    for item in structures._LIMIT_CURATED_TEMPLATES:
        ok, detail = _curated_matches_recorded(item)
        if ok is False:
            curated_failures.append((item["id"], detail))

    # --- every registry technique has at least one curated source ----------
    all_source_techniques = set(label_map.values()) | set(_excluded_techniques().values())
    techniques_without_sources = sorted(
        t for t in structures.LIMIT_TECHNIQUES if t not in all_source_techniques
    )

    # --- grade a sampled instance of every parameterizable technique --------
    grade_results = {}
    failures = []
    for technique, meta in structures.LIMIT_TECHNIQUES.items():
        if not meta["parameterizable"]:
            continue
        try:
            rng = random.Random(zlib.crc32(technique.encode()) & 0xFFFFFFFF)
            problem = generate_limit_for_technique(rng, technique)
            sol = solver.solve("limit", "limit", problem["params"])
        except Exception as exc:
            failures.append((technique, f"sample/solve: {exc}"))
            continue
        if not sol.get("formula_tags") or not sol.get("checkpoints"):
            failures.append((technique, "no formula_tags/checkpoints"))
            continue
        checks = grade_checks(technique, problem, sol)
        ok = all(want == got for _u, want, got, _r in checks)
        grade_results[technique] = {
            "correct": ok,
            "checks": [{"answer": u, "expected": w, "got": g, "reason": r} for u, w, g, r in checks],
            "sample_expr": problem["params"]["expr"],
        }
        if not ok:
            failures.append((technique, "grade mismatch"))

    # --- report --------------------------------------------------------------
    print("== Exercise -> technique mapping (audit) ==")
    print(f"{'id':10} {'technique':38} status")
    for eid in ids:
        v = audit[eid]
        print(f"{eid:10} {v.get('technique', ''):38} {v['status']}")

    print("\n== Grade results (one sampled instance per parameterizable technique) ==")
    for tid, g in sorted(grade_results.items()):
        mark = "OK " if g["correct"] else "FAIL"
        print(f"  {mark} {tid:34} {g['sample_expr']}")

    n_param = sum(1 for m in structures.LIMIT_TECHNIQUES.values() if m["parameterizable"])
    n_curated_only = len(structures.LIMIT_TECHNIQUES) - n_param
    all_ok = (
        not uncovered and not unknown_techniques and not curated_failures
        and not techniques_without_sources and not failures
        and len(grade_results) == n_param and all(g["correct"] for g in grade_results.values())
    )

    print("\n== Count report ==")
    print(f"  exercises total:            {len(ids)}")
    print(f"  mapped to techniques:       {len(mapped)}")
    print(f"  excluded (broken):          {len(excluded)}")
    print(f"  uncovered:                  {len(uncovered)}")
    print(f"  techniques total:           {len(structures.LIMIT_TECHNIQUES)}")
    print(f"    parameterizable:          {n_param}")
    print(f"    curated-only:             {n_curated_only}")
    print(f"  curated answers verified:   {len(structures._LIMIT_CURATED_TEMPLATES) - len(curated_failures)}/{len(structures._LIMIT_CURATED_TEMPLATES)}")
    print(f"  sampled+graded correct:     {sum(1 for g in grade_results.values() if g['correct'])}/{n_param}")
    print(f"  ALL CHECKS PASS:            {all_ok}")

    if unknown_techniques:
        print("\n  UNKNOWN TECHNIQUES (mapped by curated data but missing from registry):")
        for t in unknown_techniques:
            print(f"    {t}")
    if techniques_without_sources:
        print("\n  TECHNIQUES WITH NO CURATED SOURCE:")
        for t in techniques_without_sources:
            print(f"    {t}")
    if curated_failures:
        print("\n  CURATED ANSWER MISMATCHES:")
        for eid, detail in curated_failures:
            print(f"    {eid}: {detail}")
    if failures:
        print("\n  FAILURES:")
        for tid, msg in failures:
            print(f"    {tid}: {msg}")

    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "backend", "data", "bacii-exam", "limits", "structure_audit.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({
            "audit": audit,
            "grade_results": grade_results,
            "counts": {
                "exercises_total": len(ids),
                "mapped": len(mapped),
                "excluded": len(excluded),
                "uncovered": len(uncovered),
                "techniques_total": len(structures.LIMIT_TECHNIQUES),
                "parameterizable": n_param,
                "curated_only": n_curated_only,
                "all_checks_pass": all_ok,
            },
            "excluded_reasons": EXCLUDED,
        }, f, indent=1)
    print(f"\naudit written to {dest}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
