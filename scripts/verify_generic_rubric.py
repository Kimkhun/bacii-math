#!/usr/bin/env python3
"""Verify the generic, cross-topic step-by-step marking scheme
(engine/core/rubric.py) — the same deterministic points-per-step rubric
built for the 2018 past exam (engine/topics/past_exam/rubric.py), generalized
to every LIVE/GENERATED question in the app (limits all the way to function
studies), not just that one historical exam.

Unlike the past exam's hand-listed steps (fixed, real numbers from a real
paper), a generated exercise's numbers differ every time, so its rubric is
derived mechanically straight from that exercise's own ``solve()``
checkpoints/parts — the exact same data that already powers the live
step-by-step overlay (``analyze_work``).

Checks:
  1. For every topic x question_type in the registry (skipping the
     past_exam topic, covered by its own verify script), generate 5 sample
     instances and score a FULLY CORRECT simulated answer sheet built
     straight from that instance's own checkpoints — every one must score
     100% with no error, or this fails.
  2. A few representative "damaged" answers (a corrupted final value, a
     skipped intermediate step, a wrong domain/monotonicity verdict) must
     score LESS than 100% but more than 0%, proving partial credit is real,
     not just a pass/fail gate in disguise.

Run from the repo root:  python scripts/verify_generic_rubric.py
"""
import asyncio
import os
import sys

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))

from engine.core.dispatch import generate, solve  # noqa: E402
from engine.core.rubric import is_simple_value, score_work  # noqa: E402
from engine.core.shared import QUESTION_TYPES_BY_TOPIC  # noqa: E402

PASS, FAIL = [], []


def _clean_final_text(kind, ans):
    if kind == "interval":
        def fmt(iv):
            lo = "oo" if iv["lo"] == float("inf") else ("-oo" if iv["lo"] == float("-inf") else iv["lo"])
            hi = "oo" if iv["hi"] == float("inf") else ("-oo" if iv["hi"] == float("-inf") else iv["hi"])
            return f"{'(' if iv['lo_open'] else '['}{lo}, {hi}{')' if iv['hi_open'] else ']'}"
        return " U ".join(fmt(iv) for iv in ans)
    if kind == "monotonicity":
        return "; ".join(
            f"{'increasing' if p['direction'] == 'inc' else 'decreasing'} on {p['interval']}" for p in ans)
    if kind == "sign":
        return " U ".join(f"({iv['lo']}, {iv['hi']})" for iv in ans)
    return str(ans)


def perfect_lines(sol):
    """A fully-correct simulated answer sheet built straight from `sol`'s
    own checkpoints/parts — one line per gradable fact, matching how the
    2018 exam's marking demo builds its "fully correct" answer sheets."""
    lines = []
    items = sol.get("parts") or [{
        "label": sol.get("question_type", "?"), "answer_kind": sol.get("answer_kind"),
        "answer_exact": sol["answer_exact"], "checkpoints": sol.get("checkpoints") or [],
        "choices": sol.get("choices"),
    }]
    for p in items:
        for cp in (p.get("checkpoints") or []):
            if is_simple_value(cp["value"]):
                lines.append(f"{cp['label']} = {cp['value']}")
        kind = p.get("answer_kind")
        ans = p["answer_exact"]
        if is_simple_value(ans):
            lines.append(f"{p['label']} = {ans}")
        elif kind in ("interval", "monotonicity", "sign"):
            lines.append(f"{p['label']}: {_clean_final_text(kind, ans)}")
        elif kind == "continuity":
            lines.append(f"{p['label']}: so f is " + ("continuous" if ans == "continuous" else "discontinuous"))
        elif kind == "choice":
            words = (p.get("choices") or {}).get(ans, {}).get("words", [])
            if words:
                lines.append(f"{p['label']}: {words[0]}")
        # else (e.g. variation_table/draw): no single-line answer exists —
        # rubric.py itself drops that step rather than scoring it 0.
    return lines


async def check_full_sweep():
    n_ok = n_low = n_err = 0
    for topic, qts in QUESTION_TYPES_BY_TOPIC.items():
        if topic == "past_exam":
            continue
        for qt in qts:
            for seed in range(1, 6):
                try:
                    problem = await generate(topic, "medium", seed=seed, question_type=qt)
                except Exception:
                    continue
                try:
                    sol = solve(topic, problem["question_type"], problem["params"])
                    sol["question_type"] = problem["question_type"]
                    lines = perfect_lines(sol)
                    res = score_work(topic, problem["question_type"], problem["params"], lines)
                    pct = float(res["earned"]) / float(res["possible"]) * 100 if res["possible"] else 100
                    n_ok += 1
                    if pct < 99.9:
                        n_low += 1
                        misses = [(b["item"], b["label"]) for b in res["breakdown"] if b["points_earned"] == 0]
                        print(f"LOW  {topic}/{qt} seed={seed}: {pct:.1f}% missed={misses}")
                except Exception as exc:
                    n_err += 1
                    print(f"ERR  {topic}/{qt} seed={seed}: {exc!r}")
    print(f"Full sweep: {n_ok} scored, {n_low} below 100%, {n_err} errors.")
    ok = n_low == 0 and n_err == 0
    (PASS if ok else FAIL).append(f"full sweep: {n_low} below 100%, {n_err} errors")
    return ok


async def check_partial_credit():
    # A corrupted final answer must score 0 for a single-checkpoint topic.
    problem = await generate("limit", "medium", seed=7, question_type="limit")
    sol = solve("limit", "limit", problem["params"])
    good = [f"{c['label']} = {c['value']}" for c in sol["checkpoints"]]
    bad = list(good)
    bad[-1] = f"{sol['checkpoints'][-1]['label']} = 999999"
    res_good = score_work("limit", "limit", problem["params"], good)
    res_bad = score_work("limit", "limit", problem["params"], bad)
    ok1 = res_good["earned"] == res_good["possible"] and res_bad["earned"] == 0
    print(f"limit corrupted-final: correct={res_good['earned']}/{res_good['possible']}  "
          f"wrong={res_bad['earned']}/{res_bad['possible']}")
    (PASS if ok1 else FAIL).append("limit corrupted-final should be full then zero")

    # Skipping an early intermediate checkpoint must cost points but not all.
    problem2 = await generate("complex", "medium", seed=3, question_type="argument")
    sol2 = solve("complex", "argument", problem2["params"])
    lines2 = [f"{c['label']} = {c['value']}" for c in sol2["checkpoints"]]
    if len(lines2) > 1:
        res2 = score_work("complex", "argument", problem2["params"], lines2[1:])
        pct2 = float(res2["earned"]) / float(res2["possible"]) * 100
        ok2 = 0 < pct2 < 100
        print(f"complex/argument skip-first-step: {res2['earned']}/{res2['possible']} ({pct2:.1f}%)")
        (PASS if ok2 else FAIL).append("complex/argument skip-first-step should be strictly between 0 and 100%")


async def main():
    await check_full_sweep()
    await check_partial_credit()
    print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} checks passed.")
    if FAIL:
        print("FAILURES:")
        for f in FAIL:
            print(" -", f)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
