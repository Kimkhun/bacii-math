#!/usr/bin/env python3
"""Live API verification for the probability topic (needs the stack running).

Run:  python scripts/verify_probability_live.py   (from repo root)
Covers: signup -> generate (full multi-part exercise in Khmer) -> grade every
part (all correct / one wrong / unanswered), work-text line-checking, wrong
answer builds an explanation, /formulas and /templates expose the entries.
"""
import json
import random
import sys
import urllib.request

BASE = "http://localhost:8016"


def post(path, body, token=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get(path, token):
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    email = f"prob.live.{random.randint(0, 10**6)}@test.dev"
    user = post("/auth/signup", {"email": email, "password": "verifypass123"})
    token = user["access_token"]
    print(f"signup OK -> {email}")

    failures = []

    def check(cond, msg):
        print(("  OK   " if cond else "  FAIL ") + msg)
        if not cond:
            failures.append(msg)

    for diff in ("easy", "medium", "hard"):
        q = post("/problems/generate", {"topic": "probability", "difficulty": diff,
                                        "generation_mode": "templates"}, token)
        parts = q["params"].get("parts") or []
        labels = [str(p.get("label")) for p in parts]
        check(len(parts) >= 2, f"generate {diff}: multi-part (got {len(parts)})")
        check("{" not in q["prompt"] and "}" not in q["prompt"], f"generate {diff}: no unfilled slots")
        check(all(l in q["prompt"] for l in labels), f"generate {diff}: all part labels in prompt")
        print(f"  prompt {diff} ({len(parts)} parts):\n{q['prompt']}")

        # Progressive flow: learn each part's expected via a wrong submission,
        # then grade the exact answer per part, one part at a time.
        last = None
        for i, label in enumerate(labels):
            wrong = post("/problems/grade", {"question_id": q["id"], "user_answer": "0",
                                             "part": label}, token)
            check(wrong["correct"] is False and wrong.get("part") == label,
                  f"grade {diff} part {label}: wrong rejected for the right part")
            exp = (wrong.get("parts") or [{}])[0].get("expected")
            check(exp, f"grade {diff} part {label}: expected answer in response")
            g = post("/problems/grade", {"question_id": q["id"], "user_answer": exp,
                                         "part": label}, token)
            is_last = i == len(labels) - 1
            check(g["correct"] is True and g.get("all_complete") == is_last,
                  f"grade {diff} part {label}: exact accepted, all_complete={g.get('all_complete')}")
            check(g.get("explanation") is None or g.get("explanation"),
                  f"grade {diff} part {label}: response shape ok")
            last = g

        # Wrong final part -> explanation built
        gbad = post("/problems/grade", {"question_id": q["id"], "user_answer": "0",
                                        "part": labels[-1]}, token)
        check(gbad.get("explanation"), f"grade {diff}: wrong part builds explanation")

        # Work line-check: any-order values + a wrong line + symbolic skip
        def part_expected(label):
            w = post("/problems/grade", {"question_id": q["id"], "user_answer": "0",
                                         "part": label}, token)
            return (w.get("parts") or [{}])[0].get("expected")

        exp0 = part_expected(labels[0])
        work_lines = [f"P(A) = {exp0}", "= 999"]
        g_work = post("/problems/grade", {"question_id": q["id"], "user_answer": exp0,
                                          "part": labels[0], "work_text": "\n".join(work_lines)}, token)
        sc = g_work.get("step_check") or {}
        line_res = sc.get("line_results", [])
        check(any(r.get("checked") and r["correct"] for r in line_res),
              f"grade {diff}: correct work line verified (any-order)")
        check(any(r.get("checked") and r["correct"] is False for r in line_res),
              f"grade {diff}: wrong work line flagged")

    fcat = get("/formulas", token)
    prob_group = next((t for t in fcat["topics"] if t["topic"] == "probability"), None)
    check(prob_group is not None, "formulas: probability group present")
    if prob_group:
        print(f"  formulas: probability entries -> {[e['id'] for e in prob_group['entries']]}")

    inv = get("/templates", token)
    prob_topic = next((t for t in inv["topics"] if t["topic"] == "probability"), None)
    check(prob_topic is not None, "templates: probability topic present")
    if prob_topic:
        qt = prob_topic["question_types"][0]
        counts = {d: sum(1 for s in qt["difficulties"] if s["difficulty"] == d)
                  for d in ("easy", "medium", "hard")}
        check(all(v > 0 for v in counts.values()),
              f"templates: probability rows per difficulty {counts}")
        sample = qt["difficulties"][0]
        print(f"  templates: {counts} rows; sample variant={sample['variant']} answer={sample['answer']}")

    print("\n" + ("LIVE CHECKS PASSED" if not failures else f"{len(failures)} FAILURES"))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()