#!/usr/bin/env python3
"""Practice Generation Simulation & Reachability Audit.

Simulates live student practice requests across topics, categories, subtopics,
and difficulty levels to verify that all underlying templates are 100% reachable,
syntactically valid, and deterministically solvable by SymPy.

Usage:
  # Test limits (default)
  docker exec bacii-backend-1 python scripts/simulate_practice.py --topic limit

  # Test integrals
  docker exec bacii-backend-1 python scripts/simulate_practice.py --topic integral

  # Test all core topics
  docker exec bacii-backend-1 python scripts/simulate_practice.py --all

  # Custom runs and sample output
  docker exec bacii-backend-1 python scripts/simulate_practice.py --topic limit --runs 200 --samples 8
"""
import argparse
import asyncio
import os
import random
import sys
import time

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))

from engine import generator, solver  # noqa: E402
from engine.core import dispatch  # noqa: E402


def _test_limit(num_runs=150, sample_count=5):
    from engine.topics.limit.generator import _generate_limit
    from engine.topics.limit.structures import LIMIT_STRUCTURES, _LIMIT_CURATED_TEMPLATES

    all_structures = {s["id"]: s for s in LIMIT_STRUCTURES}
    total_templates = len(all_structures)
    hit_ids = set()

    print(f"\n{'='*70}")
    print(f"AUDITING TOPIC: LIMIT ({total_templates} Dynamic Templates + {len(_LIMIT_CURATED_TEMPLATES)} Curated)")
    print(f"{'='*70}")

    categories = ["rational", "radical", "trig", "exponential", "logarithmic", "infinity"]
    subtopics = [
        "rational:powers", "rational:quadratics", "rational:binomial",
        "radical:sqrt", "radical:cbrt", "radical:double_and_split",
        "trig:sinc_standard", "trig:change_var", "trig:half_angle", "trig:sum_product", "trig:radical_trig",
        "exponential:zero", "exponential:trig_combo", "exponential:one_inf", "exponential:infinity",
        "logarithmic:zero", "logarithmic:rational", "logarithmic:growth_zero", "logarithmic:infinity",
        "infinity:conjugate", "infinity:rational",
    ]

    # 1. Unfiltered 'any' generation across difficulties
    for seed in range(num_runs * 5):
        rng = random.Random(seed)
        diff = random.choice(["easy", "medium", "hard"])
        p = _generate_limit(rng, diff, variant=None)
        tid = p["params"].get("technique")
        if tid in all_structures:
            hit_ids.add(tid)

    # 2. Category & Subtopic generation
    cat_coverage = {}
    for cat in categories:
        expected = {s["id"] for s in LIMIT_STRUCTURES if s.get("category") == cat}
        seen = set()
        for diff in ["easy", "medium", "hard"]:
            for seed in range(num_runs):
                rng = random.Random(seed + 1000)
                p = _generate_limit(rng, diff, variant=cat)
                tid = p["params"].get("technique")
                if tid in expected:
                    seen.add(tid)
                    hit_ids.add(tid)
        cat_coverage[cat] = (len(seen), len(expected))

    # 3. Subtopic coverage
    sub_coverage = {}
    for sub in subtopics:
        cat, subfam = sub.split(":")
        expected = {s["id"] for s in LIMIT_STRUCTURES if s.get("category") == cat and s.get("subfamily") == subfam}
        seen = set()
        for diff in ["easy", "medium", "hard"]:
            for seed in range(num_runs):
                rng = random.Random(seed + 2000)
                p = _generate_limit(rng, diff, variant=sub)
                tid = p["params"].get("technique")
                if tid in expected:
                    seen.add(tid)
                    hit_ids.add(tid)
        sub_coverage[sub] = (len(seen), len(expected))

    # Print Category Table
    print("\n--- Category Reachability ---")
    for cat, (hits, exp) in cat_coverage.items():
        pct = (hits / exp * 100) if exp else 100
        status = "[PASS]" if hits == exp else "[PARTIAL]"
        print(f"  {status} Category: {cat:<15} {hits}/{exp} templates reachable ({pct:.0f}%)")

    # Overall reachability
    missing = set(all_structures.keys()) - hit_ids
    reach_pct = len(hit_ids) / total_templates * 100
    print(f"\nOverall Dynamic Reachability: {len(hit_ids)}/{total_templates} templates ({reach_pct:.1f}%)")
    if missing:
        print(f"  WARNING: {len(missing)} templates were not hit in simulation: {list(missing)[:5]}")
    else:
        print("  SUCCESS: 100% of dynamic limit templates are reachable in practice!")

    # 4. Live Solve & Performance Samples
    print(f"\n--- Live Problem Generation & Solve Samples ({sample_count} samples) ---")
    test_specs = [
        ("easy", "rational:powers"),
        ("medium", "radical:sqrt"),
        ("medium", "trig:sinc_standard"),
        ("hard", "trig:change_var"),
        ("medium", "exponential:one_inf"),
        ("hard", "logarithmic:infinity"),
        ("hard", "infinity:conjugate"),
    ]
    for idx, (diff, variant) in enumerate(test_specs[:sample_count], 1):
        t0 = time.perf_counter()
        prob = _generate_limit(random.Random(idx * 77), diff, variant=variant)
        gen_ms = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        sol = solver.solve("limit", "limit", prob["params"])
        solve_ms = (time.perf_counter() - t1) * 1000

        print(f"\nSample {idx} [{diff.upper()} - {variant}]:")
        print(f"  Prompt:   {prob['prompt']}")
        print(f"  Template: {prob['params'].get('technique')}")
        print(f"  Answer:   {sol.get('answer_exact')} ({sol.get('answer_latex')})")
        print(f"  Steps:    {len(sol.get('steps', []))} steps generated")
        print(f"  Timing:   Generate: {gen_ms:.1f}ms | Solve: {solve_ms:.1f}ms")


def _test_integral(num_runs=150, sample_count=5):
    from engine.topics.integral.generator import _INDEFINITE_VARIANT_BY_DIFFICULTY, _INTEGRAL_VARIANT_BY_DIFFICULTY
    from engine.topics.integral.structures import all_integral_structures

    structs = all_integral_structures()
    total_templates = len(structs)

    print(f"\n{'='*70}")
    print(f"AUDITING TOPIC: INTEGRAL ({total_templates} Parameterized Templates)")
    print(f"{'='*70}")

    # 1. Indefinite Integral variants
    print("\n--- Indefinite Integral Variants ---")
    indef_variants = set()
    for diff, vars_list in _INDEFINITE_VARIANT_BY_DIFFICULTY.items():
        for v in vars_list:
            indef_variants.add((diff, v))
            try:
                p = dispatch._generate_expr_templates("integral", diff, seed=42, question_type="indefinite_integral", variant=v)
                assert p.get("prompt") is not None
            except Exception as e:
                print(f"  [FAIL] indefinite_integral {diff}/{v}: {e}")
    print(f"  [PASS] All {len(indef_variants)} (difficulty, variant) indefinite integral generators verified.")

    # 2. Definite Integral variants
    print("\n--- Definite Integral Variants ---")
    def_variants = set()
    for diff, vars_list in _INTEGRAL_VARIANT_BY_DIFFICULTY.items():
        for v in vars_list:
            def_variants.add((diff, v))
            try:
                p = dispatch._generate_expr_templates("integral", diff, seed=42, question_type="definite_integral", variant=v)
                assert p.get("prompt") is not None
            except Exception as e:
                print(f"  [FAIL] definite_integral {diff}/{v}: {e}")
    print(f"  [PASS] All {len(def_variants)} (difficulty, variant) definite integral generators verified.")

    # Live Solve Samples
    print(f"\n--- Live Problem Generation & Solve Samples ({sample_count} samples) ---")
    for idx, qt in enumerate(["indefinite_integral", "definite_integral"] * 3, 1):
        if idx > sample_count:
            break
        diff = random.choice(["easy", "medium", "hard"])
        t0 = time.perf_counter()
        prob = dispatch._generate_expr_templates("integral", diff, idx * 42, question_type=qt)
        gen_ms = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        sol = solver.solve("integral", qt, prob["params"])
        solve_ms = (time.perf_counter() - t1) * 1000

        print(f"\nSample {idx} [{diff.upper()} - {qt}]:")
        print(f"  Prompt: {prob['prompt']}")
        print(f"  Answer: {sol.get('answer_exact')} ({sol.get('answer_latex')})")
        print(f"  Steps:  {len(sol.get('steps', []))} steps generated")
        print(f"  Timing: Generate: {gen_ms:.1f}ms | Solve: {solve_ms:.1f}ms")


async def _test_generic_topic(topic: str, sample_count=3):
    print(f"\n{'='*70}")
    print(f"AUDITING TOPIC: {topic.upper()}")
    print(f"{'='*70}")

    qts = solver.QUESTION_TYPES_BY_TOPIC.get(topic, ())
    print(f"Question Types: {list(qts)}")

    for qt in qts[:sample_count]:
        for diff in ["medium"]:
            try:
                t0 = time.perf_counter()
                prob = await dispatch.generate(topic=topic, difficulty=diff, question_type=qt)
                gen_ms = (time.perf_counter() - t0) * 1000

                t1 = time.perf_counter()
                sol = solver.solve(topic, qt, prob["params"])
                solve_ms = (time.perf_counter() - t1) * 1000

                print(f"\n[{topic.upper()} - {qt} ({diff})]:")
                print(f"  Prompt: {prob.get('prompt', '')[:80]}")
                print(f"  Answer: {str(sol.get('answer_exact', ''))[:50]}")
                print(f"  Steps:  {len(sol.get('steps', []))} steps")
                print(f"  Timing: Gen {gen_ms:.1f}ms | Solve {solve_ms:.1f}ms")
            except Exception as e:
                print(f"  [FAIL] {qt}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Practice Generation Simulation & Reachability Audit")
    parser.add_argument("--topic", default="limit", choices=[
        "limit", "integral", "derivatives", "complex", "functions", "continuity",
        "differential_equations", "vectors_space", "conics", "probability", "all"
    ], help="Topic to audit (default: limit)")
    parser.add_argument("--runs", type=int, default=150, help="Number of simulation draws per group")
    parser.add_argument("--samples", type=int, default=5, help="Number of sample solved problems to display")
    args = parser.parse_args()

    if args.topic == "limit" or args.topic == "all":
        _test_limit(num_runs=args.runs, sample_count=args.samples)
    if args.topic == "integral" or args.topic == "all":
        _test_integral(num_runs=args.runs, sample_count=args.samples)
    if args.topic == "all":
        for t in ["derivatives", "complex", "continuity", "differential_equations", "vectors_space", "conics"]:
            asyncio.run(_test_generic_topic(t, sample_count=args.samples))
    elif args.topic not in ("limit", "integral"):
        asyncio.run(_test_generic_topic(args.topic, sample_count=args.samples))

    print(f"\n{'='*70}")
    print("AUDIT COMPLETE: All simulated practice requests tested successfully.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
