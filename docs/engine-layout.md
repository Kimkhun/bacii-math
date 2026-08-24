# Engine layout & "add a topic" recipe

Where the math lives, and how to add a new BAC II topic without breaking anything.

## Layout

The engine is split by **job** (solve / generate / grade), and each job is split
by **topic**. The top-level module is a thin dispatcher that routes by topic;
each topic's file is self-contained.

```
backend/engine/
  solver.py                dispatcher: solve(topic, qt, params) → routes
  solver/                  # "the answer math" — SymPy is the only authority
    shared.py              constants + shared helpers (format_z, inline_latex, ...)
    complex.py             modulus / argument / conjugate / real / imaginary
    limits.py              _solve_limit (procedural + curated branches)
    integrals.py           _solve_indefinite / _solve_definite
    probability.py         7 structures + multi-part assembly

  generator.py             dispatcher: generate(topic, difficulty, ...) → routes
  generator/               # "the problem factory"
    shared.py              problem-dict builder + small formatters
    complex.py             template pools + Gemini proposal
    limits.py              50% curated BAC II / 50% procedural
    integrals.py           definite + indefinite variants, difficulty tables
    probability.py         scenario sampling

  grader.py                dispatcher + generic core (parsing, equivalence, work-check)
  grader/
    probability.py         multi-part grading (grade_multi, parse_multi_answers, ...)

  structures.py            integral structure registry + curated limit pool (unchanged)
  scenarios.py / formulas.py / llm.py / vision.py / explainer.py / notation.py  (unchanged)
```

The dispatchers keep the exact same names and signatures as before, so
`services.py`, the routers, and the verify scripts never noticed the move:
`solver.solve`, `generator.generate`, `grader.grade`, etc. all still resolve.

## Public API (do not rename)

- `solver.solve(topic, question_type, params)` → solution dict
- `solver.serialize(solution)` → JSON-safe dict
- `generator.generate(topic, difficulty, seed=..., question_type=..., generation_mode=..., variant=...)`
- `grader.grade` / `grade_part` / `grade_multi` / `analyze_work`
- `grader.parse_answer` / `parse_multi_answers` / `split_work_by_part` / `last_value_of_lines`
- `generator.TOPICS`, `solver.QUESTION_TYPES_BY_TOPIC`
- `structures.all_integral_structures` / `build_sample` / `build_pattern_latex` / `source_label_map`

Each package's `__init__.py` re-exports these so `from engine import solver`
keeps working.

## Adding a new topic (e.g. differential equations)

1. **solver/<topic>.py** — write `_solve_<topic>(params)` (SymPy computes the
   answer). Register the topic + question types in `solver/shared.py`'s
   `QUESTION_TYPES_BY_TOPIC`, and add a branch to `solve()` in
   `solver/solver.py`.
2. **generator/<topic>.py** — write the generator, add `"<topic>"` to
   `TOPICS` in `generator/generator.py`, and a branch in `generate()`.
3. **grader/<topic>.py** — only if grading differs from the generic rules
   (like probability's multi-part/any-order). Otherwise nothing.
4. Verify: `py_compile`, roll the new topic, then
   `docker compose restart backend`.

## Dependency rules

- **No cycles.** Shared helpers live in the topic-neutral `shared.py` modules;
  a topic module never imports another topic module. `structures.py` may import
  `solver` (it already does); nothing imports `generator` from the solve/grade
  side.
- **`params` are plain dicts** (JSON-safe, stored in Postgres). Each topic
  module's docstring documents its expected keys.
- **Keep import-time data loading at import** (e.g. the curated limit pool in
  `structures.py`); never parse data per-request. Import cost is a one-time
  startup cost, not a per-request one.