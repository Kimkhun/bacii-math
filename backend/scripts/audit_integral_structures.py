"""Regression audit for the integral structure registry.

Checks, for every structure in ``engine/topics/integral/structures.py``:
  - ids are unique and prefixed ``integral:``; the bare (legacy) name still
    resolves; every textbook exercise label maps to exactly one structure,
    and the broken ones (SOURCE_EXCLUDED_LABELS) to none,
  - for N seeds, the sampler's params equal the structure instantiated with
    the slot values it returned (so ``template_params`` is a faithful record
    of the question), with exactly the structure's slots (+ bounds),
  - the generated question is tagged with the structure and solves; the
    answer is checked independently of the solver (an indefinite answer
    differentiates back to the integrand; a definite one matches numerical
    integration); the grader accepts the solver's own answer and rejects a
    perturbed one.

Run:  cd backend && PYTHONPATH=. python scripts/audit_integral_structures.py [N_SEEDS]
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
from engine.topics.integral.generator import generate_integral_for_structure
from engine.topics.integral.structures import (
    SOURCE_EXCLUDED_LABELS,
    all_integral_structures,
    instantiate,
    source_label_map,
    structure_by_id,
)

TIMEOUT = 60


class _Timeout(Exception):
    pass


def _alarm(*_):
    raise _Timeout()


def _check_registry(structs, failures):
    for sid, n in Counter(s["id"] for s in structs).items():
        if n > 1:
            failures.append(f"{sid}: duplicate id ({n}x)")
    for s in structs:
        if not s["id"].startswith("integral:"):
            failures.append(f"{s['id']}: id not prefixed integral:")
        if structure_by_id(s["legacy_id"]) is not s:
            failures.append(f"{s['id']}: legacy id {s['legacy_id']} doesn't resolve")
    labels = Counter(label for s in structs for label in s["source_labels"])
    for label, n in labels.items():
        if n > 1:
            failures.append(f"exercise {label} is mapped to {n} structures")
    for label in SOURCE_EXCLUDED_LABELS:
        if label in source_label_map():
            failures.append(f"broken exercise {label} is mapped")
    return len(labels)


def _independent_check(qt, params, answer):
    var = sp.Symbol(params["var"])
    loc = _calc_locals(params["var"])
    integrand = sp.sympify(params["expr"], locals=loc)
    if qt == "indefinite_integral":
        if sp.simplify(sp.diff(answer, var) - integrand) != 0:
            return f"d/d{var} of the answer is not the integrand"
        return None
    lo, hi = sp.sympify(params["lower"], locals=loc), sp.sympify(params["upper"], locals=loc)
    numeric = sp.Integral(integrand, (var, lo, hi)).evalf(15)
    if abs(complex(sp.N(answer, 15)) - complex(numeric)) > 1e-8 * max(1, abs(complex(numeric))):
        return f"answer {sp.N(answer, 10)} != numerical integral {numeric}"
    return None


def _check_structure(struct, seeds, failures):
    expected_keys = set(struct["slots"]) | ({"lower", "upper"} if struct["question_type"] == "definite_integral" else set())
    for seed in range(seeds):
        where = f"{struct['id']} seed={seed}"
        signal.alarm(TIMEOUT)
        try:
            built, values = struct["sampler"](random.Random(seed))
            if set(values) != expected_keys:
                failures.append(f"{where}: slots {sorted(values)} != {sorted(expected_keys)}")
                continue
            if built != instantiate(struct, values):
                failures.append(f"{where}: sampler gave {built}, the structure gives {instantiate(struct, values)}")
                continue
            problem = generate_integral_for_structure(random.Random(seed), struct)
            params, qt = problem["params"], problem["question_type"]
            if params["template_id"] != struct["id"] or qt != struct["question_type"]:
                failures.append(f"{where}: question tagged {params['template_id']} / {qt}")
            answer = solve("integral", qt, params)["answer_exact"]
            problem_text = _independent_check(qt, params, answer)
            if problem_text:
                failures.append(f"{where}: {problem_text}")
            if not grade("integral", qt, params, str(answer))["correct"]:
                failures.append(f"{where}: grader rejected the solver's own answer {answer}")
            perturbed = answer + (sp.Symbol(params["var"]) if qt == "indefinite_integral" else 1)
            if grade("integral", qt, params, str(perturbed))["correct"]:
                failures.append(f"{where}: grader accepted a perturbed answer")
        except _Timeout:
            failures.append(f"{where}: timed out after {TIMEOUT}s")
        except Exception as e:  # noqa: BLE001 - report every failure, keep going
            failures.append(f"{where}: {type(e).__name__}: {e}")
        finally:
            signal.alarm(0)


def main():
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    signal.signal(signal.SIGALRM, _alarm)
    failures = []
    structs = all_integral_structures()
    n_labels = _check_registry(structs, failures)
    for struct in structs:
        _check_structure(struct, seeds, failures)
    by_qt = Counter(s["question_type"] for s in structs)
    print(f"{len(structs)} structures ({by_qt['indefinite_integral']} indefinite, {by_qt['definite_integral']} "
          f"definite; {n_labels} textbook exercises mapped), {seeds} seeds each")
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  - {f[:300]}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
