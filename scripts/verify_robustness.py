#!/usr/bin/env python3
"""Regression checks for grading robustness, step text and event-loop safety.

  1. Junk answers ("?!", "3 +", "1: zz; 2: yy" ...) must grade as a clean
     "could not parse" verdict, quickly, for every topic. They used to recurse
     forever in grade(): RecursionError (HTTP 500) or a minutes-long hang.
  2. Every solution step must have non-empty detail text (some limit and
     functions templates used to emit blank steps).
  3. CPU-bound SymPy work must not freeze the event loop, and a runaway job
     must time out with a 504 instead of hanging the request.

Usage (the backend container has the dependencies):
  docker cp scripts/verify_robustness.py bacii-math-backend-1:/tmp/
  docker exec -w /app -e PYTHONPATH=/app bacii-math-backend-1 python /tmp/verify_robustness.py
"""
import asyncio
import os
import signal
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from fastapi import HTTPException  # noqa: E402

from core.offload import run_cpu  # noqa: E402
from engine import generator, grader, solver  # noqa: E402

TOPICS = ["complex", "limit", "integral", "probability", "functions", "continuity",
          "derivatives", "differential_equations", "vectors_space", "conics"]
JUNK = ["?!", "3 +", ") (", "= = =", "x^^2", "2x+", "1: zz; 2: yy", "lim x->", "f(x) =", "a; b; c", "```"]
failures = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail else ""))
    if not ok:
        failures.append(name)


class _Timeout(Exception):
    pass


def _alarm(_s, _f):
    raise _Timeout()


signal.signal(signal.SIGALRM, _alarm)


def gen(topic, difficulty="easy"):
    return asyncio.run(generator.generate(topic=topic, difficulty=difficulty))


def junk_answers():
    bad = []
    for topic in TOPICS:
        p = gen(topic)
        spec, qt = p["params"], p["question_type"]
        parts = spec.get("parts") if isinstance(spec.get("parts"), list) else None
        for junk in JUNK:
            signal.alarm(10)
            t = time.perf_counter()
            try:
                if parts and len(parts) > 1:
                    r = grader.grade_part(topic, qt, spec, parts[0]["label"], junk)
                else:
                    r = grader.grade(topic, qt, spec, junk)
                if r["correct"] or time.perf_counter() - t > 3:
                    bad.append((topic, junk, "wrong verdict or slow"))
            except _Timeout:
                bad.append((topic, junk, "HANG"))
            except RecursionError:
                bad.append((topic, junk, "RecursionError"))
            finally:
                signal.alarm(0)
    check("junk answers grade cleanly and fast for every topic", not bad, bad[:5])


def valid_answers_unchanged():
    for topic in ("limit", "complex", "derivatives"):
        p = gen(topic)
        spec, qt = p["params"], p["question_type"]
        exp = str(solver.solve(topic, qt, spec)["answer_exact"])
        ok = (grader.grade(topic, qt, spec, exp)["correct"]
              and grader.grade(topic, qt, spec, f"ដូចនេះ w = {exp}")["correct"]
              and not grader.grade(topic, qt, spec, "ដូចនេះ w = 424242")["correct"])
        check(f"valid answers still grade right ({topic})", ok)


def no_empty_steps():
    empty = {}
    for topic in TOPICS:
        for i in range(12 if topic == "limit" else 3):
            for diff in (["easy", "medium", "hard"] if topic == "limit" else ["easy"]):
                p = gen(topic, diff)
                sol = solver.solve(topic, p["question_type"], p["params"])
                steps = sol.get("steps") or []
                for part in sol.get("parts", []) or []:
                    steps = steps + (part.get("steps") or [])
                for st in steps:
                    if not (st.get("detail") or "").strip():
                        empty[(topic, st.get("title"))] = empty.get((topic, st.get("title")), 0) + 1
    check("no solution step has empty detail text", not empty, dict(list(empty.items())[:5]))


async def event_loop_and_timeout():
    specs = [(await generator.generate(topic="functions", difficulty="hard"))["params"] for _ in range(4)]
    gaps, stop = [], asyncio.Event()

    async def ticker():
        last = time.perf_counter()
        while not stop.is_set():
            await asyncio.sleep(0.005)
            now = time.perf_counter()
            gaps.append(now - last - 0.005)
            last = now

    task = asyncio.create_task(ticker())
    await asyncio.sleep(0.05)
    sys.setswitchinterval(0.002)  # what main.py sets at startup
    await asyncio.gather(*[run_cpu(solver.solve, "functions", "study", s) for s in specs])
    stop.set()
    await task
    worst = max(gaps) * 1000
    check("event loop stays responsive while SymPy runs (worst stall < 500 ms)", worst < 500, f"{worst:.0f} ms")

    def runaway():
        t = time.perf_counter()
        while time.perf_counter() - t < 3:
            sum(i * i for i in range(1000))

    try:
        await run_cpu(runaway, timeout=0.3)
        check("runaway computation times out with 504", False, "no timeout")
    except HTTPException as e:
        check("runaway computation times out with 504", e.status_code == 504)


junk_answers()
valid_answers_unchanged()
no_empty_steps()
asyncio.run(event_loop_and_timeout())
print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED: {failures}")
sys.exit(1 if failures else 0)
