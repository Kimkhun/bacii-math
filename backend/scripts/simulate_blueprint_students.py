"""Simulated-student check of a topic's blueprints, end to end.

For every template that has a blueprint, on N sampled questions, and for
every method of it: a "student" writes each of that method's graded steps as
"<label> = <value>" (with this question's numbers) and then the answer. The
work must

  - score full marks (``engine.rubric.score_work``),
  - have no line marked wrong by the step checker (``analyze_work``),
  - and, with several methods, be scored against the method it follows (or
    one tying with it at full marks).

Run:  cd backend && PYTHONPATH=. python scripts/simulate_blueprint_students.py --topic <topic> [--seeds 3]
      [--only <template_id> ...]
Exits non-zero on any failure.
"""
import argparse
import asyncio
import importlib
import random
import signal
import sys

from engine.core import blueprints
from engine.core.dispatch import generate, solve
from engine.core.grading import analyze_work
from engine.rubric import score_work

TIMEOUT = 120


class _Timeout(Exception):
    pass


def _alarm(*_):
    raise _Timeout()


def _work(plan, answer, final_label):
    lines = [f"{cp['label']} = {cp['value']}" for cp in plan["checkpoints"][:-1]]
    return lines + [f"{final_label} = {answer}"]


def _question(topic, struct, seed):
    gen = importlib.import_module(f"engine.topics.{topic}.generator")
    for name in ("generate_ode_for_structure", "generate_derivative_for_structure", "generate_for_structure"):
        fn = getattr(gen, name, None)
        if fn:
            return fn(random.Random(seed), struct)
    return asyncio.run(generate(topic, struct.get("difficulty", "medium"), seed=seed, variant=struct["id"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--final-label", default="y")
    args = ap.parse_args()
    signal.signal(signal.SIGALRM, _alarm)

    spec = importlib.import_module(f"engine.topics.{args.topic}.blueprint_spec")
    structs = {s["id"]: s for s in spec.structures()}
    saved = blueprints.load(args.topic, force=True)
    targets = [t for t in (args.only or saved) if t in structs]
    failures, works, misidentified = [], 0, 0
    for tid in targets:
        for seed in range(args.seeds):
            signal.alarm(TIMEOUT)
            try:
                problem = _question(args.topic, structs[tid], seed)
                params, qt = problem["params"], problem["question_type"]
                sol = solve(args.topic, qt, params)
                plans = sol.get("methods") or []
                if not plans:
                    failures.append(f"{tid} seed={seed}: no blueprint plan resolved")
                    continue
                for plan in plans:
                    where = f"{tid} seed={seed} [{plan['method']}]"
                    lines = _work(plan, sol["answer_exact"], args.final_label)
                    works += 1
                    score = score_work(args.topic, qt, params, lines)
                    if score["earned"] != score["possible"]:
                        lost = [f"{b['label']}={b.get('expected_latex', '')}" for b in score["breakdown"]
                                if b["points_earned"] != b["points_possible"]]
                        failures.append(f"{where}: {score['earned']}/{score['possible']}, lost {lost}")
                    checked = analyze_work(args.topic, qt, params, lines)
                    flagged = [r["text"] for r in checked["line_results"] if r.get("checked") and not r.get("correct")]
                    if flagged:
                        failures.append(f"{where}: flagged {flagged}")
                    if len(plans) > 1 and score.get("method") not in (None, plan["method"]):
                        misidentified += 1
            except _Timeout:
                failures.append(f"{tid} seed={seed}: timed out after {TIMEOUT}s")
            except Exception as e:  # noqa: BLE001 - report every failure, keep going
                failures.append(f"{tid} seed={seed}: {type(e).__name__}: {e}")
            finally:
                signal.alarm(0)
    print(f"{args.topic}: {len(targets)} templates with blueprints, {works} simulated works; "
          f"{misidentified} scored against another (tying) method")
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  - {f[:400]}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
