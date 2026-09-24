"""Regression audit for every parameterized limit structure.

For each structure, samples N seeds and checks that the question is
answerable and graded correctly:
  - the solver finishes within TIMEOUT seconds,
  - its answer matches SymPy's limit (side-aware),
  - a structure with no `side` has equal, finite left/right limits at a
    finite point (otherwise the two-sided limit does not exist),
  - the grader accepts the solver's answer and rejects a perturbed one.

Run:  cd backend && PYTHONPATH=. python scripts/audit_limit_structures.py [N_SEEDS]
Exits non-zero if any structure fails.
"""
import random
import signal
import sys

import sympy as sp

from engine.core.dispatch import solve
from engine.core.grading import grade
from engine.core.shared import _calc_locals
from engine.topics.limit.structures import all_limit_structures

TIMEOUT = 8


class _Timeout(Exception):
    pass


def _alarm(_s, _f):
    raise _Timeout()


def _check(struct, seed):
    rng = random.Random(seed)
    expr_s, point_s, slots = struct["sampler"](rng)
    side = slots.get("side") or struct.get("side")
    params = {"expr": expr_s, "point": point_s, "var": struct.get("var", "x"),
              "technique": struct["id"], "formula_name": struct.get("shape", struct["id"]), **slots}
    if side:
        params["side"] = side
    x = sp.Symbol(params["var"])
    loc = _calc_locals(params["var"])
    expr, point = sp.sympify(expr_s, locals=loc), sp.sympify(point_s, locals=loc)

    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(TIMEOUT)
    try:
        ans = solve("limit", "limit", params)["answer_exact"]
        ref = sp.limit(expr, x, point, dir=side) if side else sp.limit(expr, x, point)
        if not ans.is_finite and not ref.is_infinite:
            return "solver answer not finite but reference is"
        if ans.is_finite and sp.simplify(ans - ref) != 0:
            return f"solver {ans} != sympy {ref}"
        if not side and point.is_finite:
            left, right = sp.limit(expr, x, point, dir="-"), sp.limit(expr, x, point, dir="+")
            if left != right:
                return f"two-sided limit does not exist ({left} vs {right})"
        if not grade("limit", "limit", params, str(ans))["correct"]:
            return "grader rejected the solver's own answer"
        if ans.is_finite and grade("limit", "limit", params, str(ans + 1))["correct"]:
            return "grader accepted a wrong answer"
    except _Timeout:
        return f"timed out after {TIMEOUT}s"
    finally:
        signal.alarm(0)
    return None


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    failures = {}
    structs = all_limit_structures()
    for st in structs:
        for seed in range(n):
            try:
                err = _check(st, seed)
            except Exception as exc:  # noqa: BLE001
                err = f"crashed: {exc!r}"
            if err:
                failures.setdefault(st["id"], []).append((seed, err))
    for sid, errs in sorted(failures.items()):
        print(f"FAIL {sid}: {len(errs)}/{n} seeds, e.g. seed {errs[0][0]}: {errs[0][1]}")
    print(f"{len(structs) - len(failures)}/{len(structs)} structures clean ({n} seeds each)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
