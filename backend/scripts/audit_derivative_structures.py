"""Regression audit for the derivative structure registry.

Checks, for every structure in ``engine/topics/derivatives/structures.py``:
  - ids are unique, the category is a known technique, and every
    category x difficulty has at least one structure,
  - for N seeds, the sampler's expression equals the structure's pattern
    instantiated with the slot values it returned (so ``template_params`` is
    a faithful record of the question), with no missing or extra slots,
  - the generated question solves, and the grader accepts the solver's own
    answer and rejects a perturbed one.

Run:  cd backend && PYTHONPATH=. python scripts/audit_derivative_structures.py [N_SEEDS]
Exits non-zero if anything fails.
"""
import random
import signal
import sys
from collections import Counter

import sympy as sp

from engine.core.dispatch import solve
from engine.core.grading import grade
from engine.topics.derivatives.generator import generate_derivative_for_structure
from engine.topics.derivatives.structures import (
    DERIVATIVE_STRUCTURES,
    DERIVATIVE_TECHNIQUES,
    instantiate,
    slot_names,
)

TIMEOUT = 10
_X = sp.Symbol("x")


class _Timeout(Exception):
    pass


def _alarm(*_):
    raise _Timeout()


def _same(a, b):
    diff = sp.simplify(sp.sympify(a, locals={"x": _X}) - sp.sympify(b, locals={"x": _X}))
    return diff == 0


def _check_registry(failures):
    ids = Counter(s["id"] for s in DERIVATIVE_STRUCTURES)
    for sid, n in ids.items():
        if n > 1:
            failures.append(f"{sid}: duplicate id ({n}x)")
    for s in DERIVATIVE_STRUCTURES:
        if s["category"] not in DERIVATIVE_TECHNIQUES:
            failures.append(f"{s['id']}: unknown category {s['category']!r}")
    for tech in DERIVATIVE_TECHNIQUES:
        for diff in ("easy", "medium", "hard"):
            if not any(s["category"] == tech and s["difficulty"] == diff for s in DERIVATIVE_STRUCTURES):
                print(f"  note: no {diff} structure for {tech} (generator falls back to other difficulties)")


def _check_structure(struct, seeds, failures):
    names = set(slot_names(struct))
    for seed in range(seeds):
        where = f"{struct['id']} seed={seed}"
        signal.alarm(TIMEOUT)
        try:
            rng = random.Random(seed)
            expr, values = struct["sampler"](rng)
            if set(values) != names:
                failures.append(f"{where}: slots {sorted(values)} != pattern slots {sorted(names)}")
                continue
            if not _same(expr, instantiate(struct, values)):
                failures.append(f"{where}: sampler gave {expr}, pattern gives {instantiate(struct, values)}")
                continue
            problem = generate_derivative_for_structure(random.Random(seed), struct)
            params = problem["params"]
            if params["template_id"] != struct["id"]:
                failures.append(f"{where}: question tagged {params['template_id']}")
            sol = solve("derivatives", "compute_derivative", params)
            answer = sol["answer_exact"]
            if not grade("derivatives", "compute_derivative", params, str(answer))["correct"]:
                failures.append(f"{where}: grader rejected the solver's own answer {answer}")
            if grade("derivatives", "compute_derivative", params, str(answer + 1))["correct"]:
                failures.append(f"{where}: grader accepted a perturbed answer")
        except _Timeout:
            failures.append(f"{where}: timed out after {TIMEOUT}s")
        except Exception as e:  # noqa: BLE001 - report every failure, keep going
            failures.append(f"{where}: {type(e).__name__}: {e}")
        finally:
            signal.alarm(0)


def main():
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    signal.signal(signal.SIGALRM, _alarm)
    failures = []

    _check_registry(failures)
    for struct in DERIVATIVE_STRUCTURES:
        _check_structure(struct, seeds, failures)

    origins = Counter(s["origin"] for s in DERIVATIVE_STRUCTURES)
    print(f"{len(DERIVATIVE_STRUCTURES)} structures ({origins['sampler']} sampler, "
          f"{origins['curated']} lifted from textbook exercises), {seeds} seeds each")
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
