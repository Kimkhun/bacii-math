#!/usr/bin/env python3
"""Verify the integral structures registry.

For every parameterized integral structure (the ones derived from the 124 BAC II
integral exercises), build a deterministic filled instance, solve it with SymPy
and grade the exact answer (indefinite: F, F+C, F+5 correct / F+x wrong;
definite: exact answer correct / answer+1 wrong). Also audits the mapping of all
124 exercise labels to structures (2 broken source exercises are excluded).

Run from the repo root:  python scripts/verify_integral_structures.py
"""
import json
import os
import sys
import zlib

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))

from engine import grader  # noqa: E402  (sympy-only deps)
from engine.topics.integral import structures  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from integrals_part1 import PART1, PART2  # noqa: E402
from integrals_part2 import PART3_S1, PART3_S2, PART3_S3, PART3_S4  # noqa: E402

EXCLUDED = {"III-30": "complex answer (2-2i): radicand negative inside interval",
            "III-34": "nan: 5/(x-1) has a singularity at x=1 inside [0,2]"}


def expected_labels():
    labels = [f"curated-{i}" for i in range(1, 16)]
    labels += [label for label, _v, _e in PART1]
    labels += [label for label, _v, _e in PART2]
    labels += [label for label, _v, _e, _b in PART3_S1]
    labels += [label for label, _v, _e, _b in PART3_S2]
    labels += [label for label, _v, _e, _b in PART3_S3]
    labels += [label for label, _v, _e, _b in PART3_S4]
    return labels


def grade_checks(struct, sample):
    """Return list of (user_answer, expected_verdict) checks for a structure."""
    qt = struct["question_type"]
    var = struct["var"]
    answer = str(sample["solution"]["answer_exact"])
    params = sample["params"]
    checks = [(answer, True)]
    if qt == "indefinite_integral":
        checks += [(answer + " + C", True), (answer + " + 5", True), (answer + f" + {var}", False)]
    else:
        checks += [(f"({answer}) + 1", False)]
    results = []
    for user, want in checks:
        r = grader.grade("integral", qt, params, user)
        results.append((user, want, r["correct"], r["reason"]))
    return results


def main():
    structs = structures.all_integral_structures()
    label_map = structures.source_label_map()

    # --- audit: every source label is mapped exactly once, or excluded -------
    labels = expected_labels()
    audit = {}
    for label in labels:
        if label in label_map:
            audit[label] = {"status": "mapped", "structure_id": label_map[label]}
        elif label in EXCLUDED:
            audit[label] = {"status": "excluded", "excluded_reason": EXCLUDED[label]}
        else:
            audit[label] = {"status": "UNCOVERED"}
    uncovered = [l for l, v in audit.items() if v["status"] == "UNCOVERED"]
    mapped = {l for l, v in audit.items() if v["status"] == "mapped"}
    excluded = {l for l, v in audit.items() if v["status"] == "excluded"}

    # --- grade every structure ----------------------------------------------
    grade_results = {}
    failures = []
    for struct in structs:
        try:
            sample = structures.build_sample(struct, seed=zlib.crc32(struct["id"].encode()) & 0xFFFFFFFF)
        except Exception as exc:
            failures.append((struct["id"], f"sample: {exc}"))
            continue
        sol = sample["solution"]
        if not sol.get("formula_tags") or not sol.get("checkpoints"):
            failures.append((struct["id"], "no formula_tags/checkpoints"))
            continue
        checks = grade_checks(struct, sample)
        ok = all(want == got for _u, want, got, _r in checks)
        grade_results[struct["id"]] = {
            "correct": ok,
            "checks": [{"answer": u, "expected": w, "got": g, "reason": r} for u, w, g, r in checks],
            "sample_expr": sample["params"]["expr"],
            "source_labels": struct["source_labels"],
        }
        if not ok:
            failures.append((struct["id"], "grade mismatch"))

    # --- report --------------------------------------------------------------
    def _print_table():
        print("== Exercise -> structure mapping (audit) ==")
        print(f"{'label':10} {'structure_id':28} status")
        for label in sorted(labels, key=lambda s: (len(s), s)):
            v = audit[label]
            print(f"{label:10} {v.get('structure_id',''):28} {v['status']}")

    _print_table()

    print("\n== Grade results (one parameterized instance per structure) ==")
    for sid, g in sorted(grade_results.items()):
        mark = "OK " if g["correct"] else "FAIL"
        print(f"  {mark} {sid:30} {g['sample_expr']}")

    n_ind = sum(1 for s in structs if s["question_type"] == "indefinite_integral")
    n_def = len(structs) - n_ind
    all_ok = len(grade_results) == len(structs) and all(g["correct"] for g in grade_results.values()) and not failures

    print("\n== Count report ==")
    print(f"  exercises total:        {len(labels)}")
    print(f"  mapped to structures:   {len(mapped)}")
    print(f"  excluded (broken):      {len(excluded)}")
    print(f"  uncovered:              {len(uncovered)}")
    print(f"  unique structures:      {len(structs)}")
    print(f"    indefinite:           {n_ind}")
    print(f"    definite:             {n_def}")
    print(f"  graded correct:         {sum(1 for g in grade_results.values() if g['correct'])}/{len(grade_results)}")
    print(f"  ALL STRUCTURES PASS:    {all_ok}")
    if failures:
        print("\n  FAILURES:")
        for fid, msg in failures:
            print(f"    {fid}: {msg}")

    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "backend", "data", "bacii-exam", "integrals", "structure_audit.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({
            "audit": audit,
            "grade_results": grade_results,
            "counts": {
                "exercises_total": len(labels),
                "mapped": len(mapped),
                "excluded": len(excluded),
                "uncovered": len(uncovered),
                "unique_structures": len(structs),
                "indefinite_structures": n_ind,
                "definite_structures": n_def,
                "all_graded_correct": all_ok,
            },
            "excluded_reasons": EXCLUDED,
        }, f, indent=1)
    print(f"\naudit written to {dest}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()