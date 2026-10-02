"""Regression audit for the differential-equation structure registry.

Checks, for every structure in ``engine/topics/differential_equations/structures.py``:
  - ids are unique, the category is a known ODE kind, and every kind has a
    structure,
  - every textbook exercise listed in ``CURATED_INSTANCES`` rebuilds from its
    slot values into an equation whose solution satisfies it,
  - for N seeds, the sampler's params equal the structure instantiated with
    the slot values it returned (so ``template_params`` is a faithful record
    of the question), with no missing or extra slots,
  - the generated question solves; the answer satisfies the equation and the
    initial conditions (checked by substitution, independently of dsolve)
    and isn't just the particular solution (the constants aren't all 0); the
    grader accepts the solver's own answer and rejects a perturbed one.

Run:  cd backend && PYTHONPATH=. python scripts/audit_ode_structures.py [N_SEEDS]
Exits non-zero if anything fails.
"""
import random
import signal
import sys
from collections import Counter

import sympy as sp

from engine.core.dispatch import solve
from engine.core.grading import grade
from engine.core.shared import _calc_locals
from engine.topics.differential_equations.generator import generate_ode_for_structure
from engine.topics.differential_equations.structures import (
    CURATED_INSTANCES,
    ODE_KINDS,
    ODE_STRUCTURES,
    STRUCTURES_BY_ID,
    instantiate,
    particular,
    slot_names,
)

TIMEOUT = 30
_X = sp.Symbol("x")


class _Timeout(Exception):
    pass


def _alarm(*_):
    raise _Timeout()


def _num(text):
    return sp.sympify(text, locals=_calc_locals("x"))


def _satisfies(params, y):
    """Problems with `y` as the solution of the question `params`."""
    problems = []
    if params["kind"].startswith("first"):
        lhs = sp.diff(y, _X) + _num(params["a"]) * y
    else:
        lhs = sp.diff(y, _X, 2) + _num(params["b"]) * sp.diff(y, _X) + _num(params["c"]) * y
    if sp.simplify(lhs - _num(params.get("rhs", "0"))) != 0:
        problems.append("does not solve the equation")
    ics = params["ics"]
    x0 = _num(ics["x0"])
    if sp.simplify(y.subs(_X, x0) - _num(ics["y0"])) != 0:
        problems.append("y(x0) is wrong")
    if "yp0" in ics and sp.simplify(sp.diff(y, _X).subs(_X, x0) - _num(ics["yp0"])) != 0:
        problems.append("y'(x0) is wrong")
    return problems


def _check_registry(failures):
    ids = Counter(s["id"] for s in ODE_STRUCTURES)
    for sid, n in ids.items():
        if n > 1:
            failures.append(f"{sid}: duplicate id ({n}x)")
    for s in ODE_STRUCTURES:
        if s["category"] not in ODE_KINDS:
            failures.append(f"{s['id']}: unknown category {s['category']!r}")
    for kind in ODE_KINDS:
        if not any(s["category"] == kind for s in ODE_STRUCTURES):
            failures.append(f"no structure for {kind}")
    for sid in CURATED_INSTANCES:
        if sid not in STRUCTURES_BY_ID:
            failures.append(f"CURATED_INSTANCES names unknown structure {sid}")


def _check_curated(failures):
    for sid, instances in CURATED_INSTANCES.items():
        struct = STRUCTURES_BY_ID.get(sid)
        if not struct:
            continue
        for label, values in instances.items():
            where = f"{sid} [{label}]"
            signal.alarm(TIMEOUT)
            try:
                params = instantiate(struct, values)
                answer = solve("differential_equations", "solve_ode", params)["answer_exact"]
                failures.extend(f"{where}: {p}" for p in _satisfies(params, answer))
            except _Timeout:
                failures.append(f"{where}: timed out after {TIMEOUT}s")
            except Exception as e:  # noqa: BLE001 - report every failure, keep going
                failures.append(f"{where}: {type(e).__name__}: {e}")
            finally:
                signal.alarm(0)


def _check_structure(struct, seeds, failures):
    names = set(slot_names(struct))
    for seed in range(seeds):
        where = f"{struct['id']} seed={seed}"
        signal.alarm(TIMEOUT)
        try:
            built, values = struct["sampler"](random.Random(seed))
            if set(values) != names:
                failures.append(f"{where}: slots {sorted(values)} != pattern slots {sorted(names)}")
                continue
            if built != instantiate(struct, values):
                failures.append(f"{where}: sampler gave {built}, the structure gives {instantiate(struct, values)}")
                continue
            params = generate_ode_for_structure(random.Random(seed), struct)["params"]
            if params["template_id"] != struct["id"]:
                failures.append(f"{where}: question tagged {params['template_id']}")
            answer = solve("differential_equations", "solve_ode", params)["answer_exact"]
            failures.extend(f"{where}: {p}" for p in _satisfies(params, answer))
            if sp.simplify(answer - particular(struct, values)) == 0:
                failures.append(f"{where}: trivial initial conditions (the answer is the particular solution)")
            if not grade("differential_equations", "solve_ode", params, str(answer))["correct"]:
                failures.append(f"{where}: grader rejected the solver's own answer {answer}")
            if grade("differential_equations", "solve_ode", params, str(answer + 1))["correct"]:
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
    _check_curated(failures)
    for struct in ODE_STRUCTURES:
        _check_structure(struct, seeds, failures)

    origins = Counter(s["origin"] for s in ODE_STRUCTURES)
    n_curated = sum(len(v) for v in CURATED_INSTANCES.values())
    print(f"{len(ODE_STRUCTURES)} structures ({origins['sampler']} sampler, {origins['curated']} lifted from "
          f"textbook exercises; {n_curated} exercises rebuilt), {seeds} seeds each")
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
