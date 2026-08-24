# Exam data & extraction sets (data + verify scripts)

Everything about the offline question data: what exists, how it was produced,
and how to re-run the verification.

All exam/bank data now lives under `backend/data/` (previously split between a
root-level `data/` and `backend/data/`; consolidated into one tree so
everything is mounted into the backend container and there's a single source
of truth).

## 1. Limits exam bank (`backend/data/bacii-exam/limits/`)

- 11 JSON files (2014–2025, 2020 absent), **37 real BAC II questions**, each
  with `prompt_latex`, `answer_latex`, `technique`, `formula_latex`.
- **Verify:** `python scripts/verify_limits.py` — parses each LaTeX question,
  recomputes the limit with SymPy, compares to the recorded answer, and checks
  the stated formula identities. Result: 36/37 answers pass, 1 legit skip
  (2024b parametric "find a").
- **Windows prerequisites:** the script needs UTF-8 file handling (already
  patched) and `pip install antlr4-python3-runtime==4.11.1` — SymPy 1.14's
  LaTeX parser hard-requires exactly 4.11.x (`startswith("4.11")` check).
- **Sorted by technique** into `backend/data/limits/{formula_name}.json` (13
  categories, e.g. `factoring_0_0`, `sinc_standard_limit`, `conjugate_infinity`
  — see below) — this is what the generator's curated limit pool actually
  reads.

## 2. Integral exercise extraction (`scripts/integrals_part1.py`,
   `scripts/integrals_part2.py`, `scripts/verify_integrals.py`)

- **109 exercises transcribed from 4 photos** (indefinite basics + u-sub/linear
  argument, definite S1–S4 incl. integration by parts), as SymPy strings.
- **Verify:** `python scripts/verify_integrals.py` — integrates everything,
  prints a report, writes `backend/data/bacii-exam/integrals/answers.json`
  ({label: {var, expr, bounds, answer}}) for reference. All 109 computed.
- **Known source-material flaws (deliberately not generated):** III-30 gives a
  complex answer (`2−2i`, negative radicand inside the interval); III-34 is
  `nan` (`5/(x−1)` has a singularity at x=1 inside [0,2]); III-J won't simplify
  as a definite integral.
- The 15 Part-I exercises that had written answers became the parameterized
  indefinite "curated" templates (generator `_INDEFINITE_TEMPLATES`).

## 3. How the data becomes playable

- All of `backend/data/` is mounted into the backend container (`./backend:/app`).
- **Limits:** `backend/data/limits/{formula_name}.json` (37 real exercises,
  sorted by technique) is loaded at import by
  `engine/structures._LIMIT_CURATED_TEMPLATES`, parsed into SymPy expr/point
  pairs, and mixed into the live limit generator (50% curated / 50%
  procedural per request) — see `generator-variants.md`. The exam-authored
  `technique` text narrates the solution steps; SymPy still computes/grades
  the answer independently.
- **Integrals:** the 15 curated Part-I indefinite shapes are parameterized
  into `_INDEFINITE_TEMPLATES`; the raw `bacii-exam/integrals/` bank JSON
  itself is reference/audit data, not read live by the generator.
- Wired bank play (`source="exam"`, playing an exercise verbatim rather than
  through a template) is a documented future item (exam mode / exam-bank
  pipeline).

## 4. Formula catalog (content data, mounted)

`backend/data/formulas/*.json` — merged over the built-in registry by
`engine/formulas.py` at import; malformed entries skipped; built-ins are the
fallback. See `adding-question-types.md` for the entry format.