#!/usr/bin/env python3
"""Verify the probability topic end to end.

1. Real BAC II exercises: construct multi-part params for the exact slot values
   of the six supplied problems and assert every sub-part's answer matches the
   known exam answer.
2. Rolls: for every catalog exercise, generate -> solve -> grade many times,
   asserting: each part solves with 0 < P < 1, the target part is the graded
   answer, prompt contains every part label with no leftover slots, grade_multi
   accepts all-correct / rejects any-wrong / reports unanswered, work-line
   extraction recovers per-part answers, and analyze_work line-checks the
   merged checkpoints.
3. Direct single-part structures (laplace, binomial, union, conditional).
4. Regression: existing topics still roll and grade.

Run:  cd backend && python ../scripts/verify_probability.py
"""
import asyncio
import os
import random
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from engine import generator, grader, solver  # noqa: E402
from engine.topics.probability import scenarios  # noqa: E402


def generate_sync(*args, **kwargs):
    return asyncio.run(generator.generate(*args, **kwargs))


def multipart_params(structure, base, parts):
    """Build solver params for a multi-part exercise from fixed slot values."""
    return {
        "structure": structure,
        "target": parts[-1][0],
        "parts": [{"label": label, "want": want, **base, **extra} for label, want, extra in parts],
    }


# (structure, base slots, parts [(label, want, extra), ...], expected {label: answer})
REAL_CASES = [
    (
        "hypergeometric", {"w": 4, "b": 8, "k": 5},
        [("A", "exactly_split", {"a": 3}), ("B", "exactly_split", {"a": 2}),
         ("C", "all_black", {}), ("D", "at_least_white", {})],
        {"A": "14/99", "B": "14/33", "C": "7/99", "D": "92/99"}, "P1",
    ),
    (
        "two_bag_numbers", {"n": 9, "k1": 2, "k2": 1},
        [("A", "all_odd", {}), ("B", "all_even", {}), ("C", "at_least_one_odd", {})],
        {"A": "25/162", "B": "2/27", "C": "25/27"}, "P2",
    ),
    (
        "two_box", {"w1": 8, "b1": 4, "w2": 5, "b2": 3},
        [("ក", "both_white", {}), ("ខ", "both_black", {}),
         ("គ", "cross", {}), ("ឃ", "exactly_one_white", {})],
        {"ក": "5/12", "ខ": "1/8", "គ": "1/4", "ឃ": "11/24"}, "P3",
    ),
    (
        "hypergeometric", {"w": 7, "b": 5, "k": 4},
        [("ក", "all_white", {}),
         ("ខ", "at_least_white", {"wanted": "b", "want_label": "10000-riel note", "other_label": "5000-riel note"}),
         ("គ", "exactly_split", {"a": 3})],
        {"ក": "7/99", "ខ": "92/99", "គ": "35/99"}, "P4",
    ),
    (
        "hypergeometric", {"w": 8, "b": 6, "k": 5},
        [("A", "all_white", {"want_label": "red", "other_label": "blue"}),
         ("B", "exactly_split", {"a": 3, "want_label": "red", "other_label": "blue"}),
         ("C", "at_least_white", {"wanted": "b", "want_label": "blue", "other_label": "red"})],
        {"A": "4/143", "B": "60/143", "C": "139/143"}, "P5",
    ),
    (
        "hypergeometric", {"w": 4, "b": 6, "k": 4},
        [("A", "all_white", {"want_label": "girl", "other_label": "boy"}),
         ("B", "all_black", {"want_label": "boy", "other_label": "girl"}),
         ("C", "exactly_split", {"a": 2, "wanted": "b", "want_label": "boy", "other_label": "girl"})],
        {"A": "1/210", "B": "1/14", "C": "3/7"}, "P6",
    ),
]

# (structure, params) — structures with no catalog scenario yet (solver-ready).
PARAM_DIRECT = [
    ("laplace", {"total": 10, "favorable": 3}),
    ("binomial", {"n": 5, "k": 2}),
    ("union", {"pa": "1/2", "pb": "1/3", "pab": "1/6"}),
    ("conditional", {"pab": "1/3", "pb": "2/3"}),
]


def main():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
            print(f"  FAIL {msg}")

    print("== 1. Real BAC II exercises (multi-part, known answers) ==")
    for structure, base, parts, expected, label in REAL_CASES:
        params = multipart_params(structure, base, parts)
        sol = solver.solve("probability", "probability", params)
        part_map = {p["label"]: p for p in sol["parts"]}
        for plabel, want, extra in parts:
            got = str(part_map[plabel]["answer_exact"])
            exp = expected[plabel]
            ok = got == exp
            if not ok:
                failures.append(f"{label} part {plabel}: got {got}, expected {exp}")
            print(f"  {'OK ' if ok else 'FAIL'} {label} {plabel}: {got} (tags={part_map[plabel]['formula_tags']})")

    print("\n== 2. Direct single-part structures (laplace, binomial, union, conditional) ==")
    for struct, params in PARAM_DIRECT:
        sol = solver.solve("probability", "probability", {"structure": struct, **params})
        p = sol["answer_exact"]
        check(p.is_Rational and 0 < p < 1, f"{struct}: P={p} not a probability")
        check(sol["formula_tags"], f"{struct}: no formula_tags")
        g = grader.grade("probability", "probability", {"structure": struct, **params}, str(p))
        check(g["correct"], f"{struct}: exact answer graded wrong")
        print(f"  OK  {struct}: P={p}")

    print("\n== 3. Rolls: every catalog exercise (40 per difficulty) ==")
    rng = random.Random(20260823)
    rolled = 0
    for diff in ("easy", "medium", "hard"):
        ids = scenarios.VARIANT_BY_DIFFICULTY[diff]
        check(ids, f"no scenarios for difficulty {diff}")
        for sid in ids:
            entry = scenarios.by_id(sid)
            labels = [p["label"] for p in entry.get("parts", [])]
            for _ in range(40):
                problem = generate_sync("probability", diff, seed=rng.getrandbits(32),
                                        question_type="probability", variant=sid)
                rolled += 1
                p = problem["params"]
                check(p["scenario_id"] == sid, f"{sid}: generator returned {p.get('scenario_id')}")
                for text in (problem["prompt"], problem["prompt_latex"] or ""):
                    check("{" not in text and "}" not in text, f"{sid}: unfilled slot in text")
                for lab in labels:
                    check(lab in problem["prompt"], f"{sid}: part label {lab} missing from prompt")
                sol = solver.solve("probability", "probability", p)
                parts = sol["parts"]
                check(len(parts) == len(labels), f"{sid}: {len(parts)} parts vs {len(labels)}")
                for pt in parts:
                    ans = pt["answer_exact"]
                    check(ans.is_Rational and 0 < ans < 1, f"{sid}/{pt['label']}: P={ans} not in (0,1)")
                    check(abs(float(pt["answer_decimal"]) - float(ans)) < 1e-9,
                          f"{sid}/{pt['label']}: decimal mismatch")
                target = sol["target_label"]
                check(target == labels[-1], f"{sid}: target {target} != last part {labels[-1]}")
                check(str(sol["answer_exact"]) == str(parts[-1]["answer_exact"]),
                      f"{sid}: question answer != last part answer")
                # grade all correct
                subs = {pt["label"]: str(pt["answer_exact"]) for pt in parts}
                res = grader.grade_multi("probability", "probability", p, subs)
                check(res["correct"] and len(res["parts"]) == len(parts), f"{sid}: all-correct rejected")
                # one wrong
                bad = dict(subs)
                bad[parts[0]["label"]] = "0"
                check(not grader.grade_multi("probability", "probability", p, bad)["correct"],
                      f"{sid}: wrong part accepted")
                # partial (only first part)
                res3 = grader.grade_multi("probability", "probability", p,
                                          {parts[0]["label"]: str(parts[0]["answer_exact"])})
                check(not res3["correct"] and res3["parts"][0]["correct"],
                      f"{sid}: partial should be incorrect with first part correct")
                # decimal answers accepted
                dec = {pt["label"]: f"{float(pt['answer_exact']):.6f}" for pt in parts}
                check(grader.grade_multi("probability", "probability", p, dec)["correct"],
                      f"{sid}: decimals rejected")
                # work-line extraction + line-checking
                extract_lines = []
                for pt in parts:
                    extract_lines.append(f"{pt['label']}: n=1")
                    extract_lines.append(f"{pt['label']}: {pt['answer_exact']}")
                segs = grader.split_work_by_part(extract_lines, labels)
                subs4 = {l: grader.last_value_of_lines(segs[l]) for l in labels if grader.last_value_of_lines(segs[l])}
                check(grader.grade_multi("probability", "probability", p, subs4)["correct"],
                      f"{sid}: work-line answers rejected")
                check_lines = [f"line{i} = {cp['value']}" for i, cp in enumerate(sol["checkpoints"])]
                wk = grader.analyze_work("probability", "probability", p, check_lines)
                check(all(r.get("correct") for r in wk["line_results"] if r.get("checked")),
                      f"{sid}: checkpoint lines did not all match")
                check(any(r.get("matches", "").startswith(lab) for lab in labels for r in wk["line_results"]),
                      f"{sid}: no part-labeled checkpoints matched")
                # progressive per-part grading (grade_part)
                for idx, pt in enumerate(parts):
                    g = grader.grade_part("probability", "probability", p, pt["label"], str(pt["answer_exact"]))
                    check(g["correct"], f"{sid}: grade_part {pt['label']} rejected exact answer")
                    check(g["all_complete"] == (pt["label"] == labels[-1]),
                          f"{sid}: all_complete wrong for {pt['label']}")
                g_bad = grader.grade_part("probability", "probability", p, parts[0]["label"], "0")
                check(not g_bad["correct"], f"{sid}: grade_part accepted a wrong value")
                g_labeled = grader.grade_part("probability", "probability", p, parts[0]["label"],
                                              f"{parts[0]['label']}: {parts[0]['answer_exact']}")
                check(g_labeled["correct"], f"{sid}: grade_part rejected labeled value")
            # any_order work-checking (probability mode): values in any order,
            # a symbolic formula-definition line skipped, a wrong line flagged.
            cp_values = [cp["value"] for cp in sol["checkpoints"]]
            order_lines = [f"line{i} = {v}" for i, v in enumerate(reversed(cp_values))]
            order_lines.append("(n!)/(r!(n-r)!)")
            wk = grader.analyze_work("probability", "probability", p, order_lines)
            greens = [r for r in wk["line_results"] if r.get("checked") and r["correct"]]
            reds = [r for r in wk["line_results"] if r.get("checked") and not r["correct"]]
            sym = [r for r in wk["line_results"] if r.get("reason") == "symbolic"]
            check(len(greens) == len(cp_values), f"{sid}: any_order matched {len(greens)}/{len(cp_values)} (out-of-order)")
            check(not reds, f"{sid}: any_order flagged a correct value as wrong")
            check(len(sym) == 1, f"{sid}: formula-definition line not skipped")
            wk2 = grader.analyze_work("probability", "probability", p, order_lines + ["= 999"])
            check(any(r.get("checked") and r["correct"] is False for r in wk2["line_results"]),
                  f"{sid}: a genuinely wrong line was not flagged")
            print(f"  OK  {sid} ({diff}): {len(labels)} parts, last-answer e.g. {sol['answer_exact']}")

    check(rolled >= 3 * 40, f"too few rolls: {rolled}")

    print("\n== 4. Regression: existing topics still roll + grade ==")
    for topic, qt in (("complex", "modulus"), ("limit", "limit"),
                      ("integral", "definite_integral"), ("integral", "indefinite_integral")):
        for diff in ("easy", "medium", "hard"):
            problem = generate_sync(topic, diff, seed=rng.getrandbits(32), question_type=qt)
            sol = solver.solve(topic, qt, problem["params"])
            g = grader.grade(topic, qt, problem["params"], str(sol["answer_exact"]))
            check(g["correct"], f"regression {topic}/{qt}/{diff}: exact answer graded wrong")

    print("\n" + ("ALL CHECKS PASSED" if not failures else f"{len(failures)} FAILURES"))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()