# Engine layout & "add a topic" recipe

Where the math lives, and how to add a new BAC II topic without breaking anything.

## Layout

The engine is split **by topic first**: every topic owns one self-contained
folder under `engine/topics/<topic>/` holding its solver, generator, grader,
and curated exercise data. A small topic-neutral kernel under `engine/core/`
holds the generic dispatch routing and the grading logic every topic shares.

```
backend/engine/
  solver.py, generator.py, grader.py   # public facades — do not rename
                                        #   (see "Public API" below)
  core/                                 # topic-neutral kernel
    dispatch.py      solve()/generate()/TOPICS/variants_for_formula() —
                      routes to engine.topics.<topic>
    grading.py        parse_answer/analyze_work/grade/grade_part + every
                       answer-kind judge (_judge_interval, _judge_choice, ...)
    shared.py          QUESTION_TYPES(_BY_TOPIC), format_z/z_latex/inline_latex,
                       _calc_locals, _formula_tags
    slots.py           {a}/{b}/.../{v} slot-template filling, shared by the
                       limit and integral generators
    expr_shared.py      problem-dict builder + small expr formatters, shared
                       by the limit and integral generators
  llm.py, vision.py, notation.py, explainer.py, formulas.py, cache.py
                        # cross-cutting infra, not topic-specific

  topics/
    complex/            modulus, argument, conjugate, real/imaginary parts,
                        arithmetic, power, De Moivre, nth roots — see below
    limit/               solver.py, generator.py, structures.py (curated pool +
                        technique registry), grader.py, data/curated/*.json
    integral/            solver.py, generator.py, structures.py (the 168-shape
                        registry backing the admin /templates page), grader.py
    probability/          solver.py, generator.py (scenario-based), counting.py
                        (combinatorics question_type), scenarios.py, grader.py
                        (multi-part grading), data/scenarios/, data/counting/
    functions/            solver.py, display.py (Khmer/English wording),
                        generator.py, grader.py (+ grade_graph_check),
                        graph_grader.py/graph_renderer.py, data/curated/*.json
    continuity/, derivatives/, differential_equations/, vectors_space/, conics/
                        solver.py, generator.py, grader.py, data/curated/curated.json
```

Each topic folder that has a formula-sheet catalog also carries
`data/formulas.json`, merged by `engine/formulas.py` (see below).

### `topics/complex/` — one module per exercise technique

Further split by technique (mirrors `data/curated/{formula_name}.json`):

```
topics/complex/
  __init__.py       topic overview (this file map)
  solver.py         _solve_complex(question_type, params) — the topic's dispatcher
  modulus.py        |z| = sqrt(a^2+b^2)
  argument.py       arg(z) via atan2
  conjugate.py      z̄ = a - bi
  real_imaginary.py Re(z) / Im(z)
  arithmetic.py     z1 (+|-|*|/) z2
  power.py          z^n, small n, direct algebraic expansion
  de_moivre.py       z^n, large n, via trigonometric form + De Moivre
  nth_roots.py       one n-th root of z (reverse-built from a clean root)
  trig.py           shared "nice special angle" helpers for de_moivre.py/nth_roots.py
  generator.py       template pools + curated-textbook loader + Gemini proposal
  grader.py          no custom rule (re-exports the generic core)
```

`_solve_complex` takes the full `params` dict (not unpacked `a, b`) since
different question types need different shapes (`a1/b1/a2/b2/operation`,
`a/b/n`, `r/k/d/n`, `rho/k0/d0/n`).

## Public API (do not rename)

- `solver.solve(topic, question_type, params)` → solution dict
- `solver.serialize(solution)` → JSON-safe dict
- `generator.generate(topic, difficulty, seed=..., question_type=..., generation_mode=..., variant=...)`
- `grader.grade` / `grade_part` / `grade_multi` / `analyze_work`
- `grader.parse_answer` / `parse_multi_answers` / `split_work_by_part` / `last_value_of_lines`
- `generator.TOPICS`, `solver.QUESTION_TYPES_BY_TOPIC`
- `engine.topics.integral.structures.all_integral_structures` / `build_sample` /
  `build_pattern_latex` / `source_label_map`
- `engine.topics.limit.structures.LIMIT_TECHNIQUES` / `_LIMIT_CURATED_TEMPLATES`

`engine/solver.py`, `engine/generator.py`, `engine/grader.py` are thin facade
modules that re-export these names from `engine.core` + the topic packages —
`services.py`, the routers, and the verify scripts all resolve `from engine
import solver` (etc.) exactly as before.

## Adding a new topic (e.g. differential equations)

1. **`engine/topics/<topic>/solver.py`** — write `_solve_<topic>(params)`
   (SymPy computes the answer). Register the topic + question types in
   `engine/core/shared.py`'s `QUESTION_TYPES_BY_TOPIC`, and add a branch to
   `solve()` in `engine/core/dispatch.py`.
2. **`engine/topics/<topic>/generator.py`** — write the generator, add
   `"<topic>"` to `TOPICS` in `engine/core/dispatch.py`, and a branch in
   `generate()`. Curated exercise data goes in `engine/topics/<topic>/data/curated/`.
3. **`engine/topics/<topic>/grader.py`** — only needs real content if grading
   differs from the generic rules (like probability's multi-part/any-order,
   or functions' graph-check). Otherwise it's a two-line re-export of
   `engine.core.grading` for folder-shape consistency.
4. Verify: `py_compile`, roll the new topic, then
   `docker compose restart backend`.

## Dependency rules

- **No cycles.** Shared helpers live in `engine/core/`; a topic module never
  imports another topic module (complex's generator reaching into its own
  `nth_roots.py`/`trig.py` siblings is fine — that's within the same topic).
  `engine/core/dispatch.py` imports every topic's `solver.py`/`generator.py`;
  nothing in `engine/core/` is imported back by a topic at module load time
  except `engine.core.shared` / `slots` / `expr_shared` / `grading` (a topic's
  `grader.py` may import `engine.core.grading` — that's the one line of
  the dependency graph that runs topic → core, never core → topic, except the
  single lazy, call-time-only import `engine.core.grading.grade_part` uses to
  reach `engine.topics.probability.grader._judge_value`).
- **`params` are plain dicts** (JSON-safe, stored in Postgres). Each topic
  module's docstring documents its expected keys.
- **Keep import-time data loading at import** (e.g. the curated pools in each
  topic's `generator.py`/`structures.py`); never parse data per-request.
  Import cost is a one-time startup cost, not a per-request one.
