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
- **antlr4 dependency:** SymPy's LaTeX parser hard-requires
  `antlr4-python3-runtime==4.11` (exact match to the antlr grammar version
  SymPy 1.14's parser was generated against) — this is now pinned in
  `backend/requirements.txt` itself, not just a script prerequisite, because a
  missing/mismatched version makes `parse_latex` raise `ImportError` for
  *every* exercise, which used to be silently swallowed and empty the entire
  curated pool with no visible error (see `structures._load_limit_curated`,
  which now re-raises `ImportError` instead of skipping it like a bad prompt).
- **Sorted by technique** into `backend/engine/topics/limit/data/curated/{formula_name}.json` (13
  categories, e.g. `factoring_0_0`, `sinc_standard_limit`, `conjugate_infinity`
  — see below) — this is what the generator's curated limit pool actually
  reads, and what `structures.LIMIT_TECHNIQUES` (the technique registry) is
  keyed on.

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
- **Limits:** `backend/engine/topics/limit/data/curated/{formula_name}.json` (37 real exercises +
  20 textbook exercises, sorted by technique) is loaded at import by
  `engine/topics/limit/structures._LIMIT_CURATED_TEMPLATES`, parsed into SymPy expr/point
  pairs, and mixed into the live limit generator (50% curated per request,
  50% a random *parameterizable* technique's sampler) — see
  `generator-variants.md` and `structures.LIMIT_TECHNIQUES`. The exam-authored
  `technique` text narrates curated-draw steps; procedurally-sampled draws get
  a generic per-technique narration instead. SymPy still computes/grades the
  answer independently either way. `scripts/verify_limit_structures.py` audits
  that every curated exercise maps to a known technique and that every
  parameterizable technique's sampler produces a gradeable-correct instance.
- **Integrals:** the 15 curated Part-I indefinite shapes are parameterized
  into `_INDEFINITE_TEMPLATES`; the raw `bacii-exam/integrals/` bank JSON
  itself is reference/audit data, not read live by the generator.
- Wired bank play (`source="exam"`, playing an exercise verbatim rather than
  through a template) is a documented future item (exam mode / exam-bank
  pipeline).

## 4. Textbook exercise extraction (`backend/data/textbook/`)

- **179 exercises transcribed from a scanned grade-12 textbook** (5 PDFs,
  107 pages), split into `textbook/complex_numbers/` (164, across 13
  technique files: algebraic form, trig form, De Moivre/roots) and
  `textbook/limits/` (20, across 2 files not already covered by the exam
  bank: `log_limit_zero`, `indeterminate_one_infinity`). Kept as raw
  extraction — no answers, no dedup against the live data folders.
- **How it feeds the live folders:** the same files (or a subset) are copied
  into the existing `backend/engine/topics/limit/data/curated/` and a new top-level
  `backend/engine/topics/complex/data/curated/` folder, checked for `prompt_latex`
  duplicates against the exam-derived data first (none found).
  - **Limits:** both textbook files needed `answer_latex` added (the
    generator's curated-limit loader requires it) — computed directly with
    SymPy's `limit()` (e.g. `log_limit_zero`'s 0/0 log-of-(1+u) forms,
    `indeterminate_one_infinity`'s `1^∞` forms via `lim(1+u)^(1/u)=e`), not
    invented. Both categories added to
    `structures._LIMIT_DIFFICULTY_BY_CATEGORY` as `hard` and are now part of
    the live curated pool (56 total, up from 36).
  - **Complex numbers:** most textbook exercises involve powers, radicals, De
    Moivre, or systems the current a+bi-only solver can't replay, so only the
    literal `z = a+bi` (plain-integer) subset with a recognized question type
    (modulus/argument/conjugate/real_part/imaginary_part) was pulled into a
    new curated pool — 6 exercises, `easy` difficulty
    (`engine/topics/complex/generator._COMPLEX_CURATED_TEMPLATES`, mirroring the limit
    loader's parse-once-at-import + graceful-skip pattern). See
    `generator-variants.md` for how it's mixed into `generate()`.

## 5. Formula catalog (content data, mounted)

each topic's `backend/engine/topics/<topic>/data/formulas.json` — merged over the built-in registry by
`engine/formulas.py` at import; malformed entries skipped; built-ins are the
fallback. See `adding-question-types.md` for the entry format.