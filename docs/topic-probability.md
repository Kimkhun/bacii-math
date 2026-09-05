# Topic: Probability (គណិតវិទ្យា — ប្រូបាប៊ីលីតេ) — BUILT

Probability questions are Khmer **word problems**: the math is simple
(combinatorics + fractions), the hard part is the natural-language story. The
implementation separates the two halves: SymPy owns the math, and a
**user-owned scenario catalog** JSON owns the Khmer sentences.

## The text layer decision (strategy experiment, 2026-08-23)

Three strategies were trialed for the Khmer text (see the session notes):

| Strategy | Verdict |
|---|---|
| **A. Slot-filled Khmer frames** (deterministic, user-owned) | **BUILT** — ~0.04 ms/roll, offline, sentence and math consistent *by construction*; Khmer is content the user edits |
| B. LLM-drafted Khmer story + SymPy-validated params | Rejected: still needs Khmer review, param extraction is fragile (Khmer-script numerals, internally inconsistent drafts), burns the 10/min Gemini budget on every roll |
| C. Hybrid (frames + cached LLM paraphrase) | Natural v2: keep frames as source of truth, let the LLM paraphrase only the *text* (params frozen), cache by `scenario_id + params` behind the existing rate limiter |

## The core design: structure-first + scenario catalog

1. **Math structure** (code): `_solve_probability(params)` in
   `backend/engine/solver.py`, dispatched on `params["structure"]`. SymPy
   computes the exact `Rational` answer + checkpoints (`n(Ω)`, `n(A)`, `P(A)`
   fraction lines — line-checked like everything else).
2. **Khmer text** (content): `backend/engine/topics/probability/data/scenarios/probability.json` —
   sentence frames parameterized from **real BAC II exam problems** supplied by
   the user (2026-08-23). Same user-editable pattern as each topic's `data/formulas.json`.
3. **Generator**: picks a scenario → samples valid params (ranges +
   constraints) → fills the Khmer text → the solver computes the math. **The
   LLM is not involved in v1 generation.**

## Structures (solver branches)

| Structure | Wants (event asked about) | Formula tags | Source |
|---|---|---|---|
| `laplace` | single-draw urn/class count | `laplace_rule` | solver-ready, no scenario yet |
| `hypergeometric` | `all_white`, `all_black`, `exactly_split` (a of k), `at_least_white` | `hypergeometric_rule` (+`combination_rule`, `complement_rule`) | real problems 1, 4, 5, 6 |
| `two_box` | `both_white`, `both_black`, `cross`, `exactly_one_white` (one draw from each of two boxes) | `laplace_rule` + `product_rule` (+`union_rule` for the disjoint sum) | real problem 3 |
| `two_bag_numbers` | `all_odd`, `all_even`, `at_least_one_odd` (numbered balls 1..n, k1 from bag 1, k2 from bag 2) | `combination_rule` + `product_rule` (+`complement_rule`) | real problem 2 |
| `binomial` | exactly k heads in n coin flips | `binomial_rule` | solver-ready, no scenario yet (syllabus confirmation pending) |
| `union` | P(A∪B) from given P(A), P(B), P(A∩B) | `union_rule` | solver-ready, no scenario yet |
| `conditional` | P(A\|B) from given P(A∩B), P(B) | `conditional_rule` | solver-ready, no scenario yet |

Every branch **validates its params** (impossible problems raise `ValueError`):
the catalog's constraints prevent them, the solver refuses them. Answers are
SymPy-exact `Rational`s; grading handles `3/10`, `0.3`, and `C(6,2)`-style
combination notation (added to `parse_answer`).

## The scenario catalog (`backend/engine/topics/probability/data/scenarios/probability.json`)

User-owned content: 14 entries whose Khmer frames are parameterizations of the
real exam sentences (bag of white/black balls, banknotes 5000៛/10000៛, red/blue
pens, student groups, two boxes, numbered bags). Each entry:

```json
{
  "structure": "hypergeometric",
  "difficulty": "medium",
  "want": "exactly_split",
  "slots": { "w": {"min": 5, "max": 8}, "b": {"min": 5, "max": 8},
             "k": {"min": 3, "max": 4}, "a": {"min": 2, "max": 3} },
  "derived": { "n": "w + b", "kb": "k - a" },
  "constraints": ["a >= 1", "k - a >= 1", "a <= w", "k - a <= b"],
  "scenarios_km": ["...{w}...{kb}..."],
  "scenarios_en": ["..."]
}
```

- `slots`: `{min, max}` integer ranges or `{values: [...]}` lists (fractions
  allowed as strings — used by the union/conditional params when scenarios
  arrive).
- `derived`: slots computed from other slots, evaluated in order by the same
  safe AST evaluator (`backend/engine/topics/probability/scenarios.py` — whitelisted operators
  only: `+ - * // % **`, comparisons, `and/or/not`; no calls, no attributes).
- `constraints`: expressions that must all hold; the sampler retries (~80
  attempts) then skips to the next scenario. Range sizes are small, so
  valid params always converge.
- `scenarios_km` fills with **Arabic digits**, exactly as the real exam
  sentences do. In hypergeometric frames `{w}` is always the category the
  event asks about.
- The `_meta` notes flag the frames that are **not yet backed by a supplied
  exam problem** (laplace single-draw, binomial coins, union, conditional) —
  add frames there once real examples are provided.

The loader (`engine/topics/probability/scenarios.py`) mirrors the formulas loader: JSON is the
content, no built-in fallback, malformed files/entries are skipped, and
`VARIANT_BY_DIFFICULTY` drives the generator pools and the admin `/templates`
inventory rows (1 easy / 3 medium / 2 hard exercises).

## Question format

- `topic: "probability"`, `question_type: "probability"`,
  `params: {structure, variant, scenario_id, target, parts: [{label, want, ...slots}]}`.
- `prompt` = filled Khmer text — the setup line, then every sub-part
  (A/B/C/D or ក/ខ/គ/ឃ) on its own line, exactly like the exam paper.
  **`prompt_latex` is `null`** — `QuestionCard` renders the whole string via
  `katex.renderToString` (display math), which cannot render Khmer; plain-text
  prompt it is. If math-inside-Khmer is ever wanted, `QuestionCard` must switch
  to MathText-style auto-render first.
- Answer = exact fraction **per part**.

## Progressive part-by-part grading

A multi-part exercise is graded **one part at a time** (A → check → B → check
→ ...), so a wrong part A never cascades into a wall of errors on B/C/D:

- `GradeRequest.part` names the part being submitted; `services.grade_question`
  routes it to `grader.grade_part` — an exact/numeric verdict for that part
  only, with `all_complete` true when the last part is correct.
- The web gives **every part its own canvas** with a part-switcher widget on top
  (A | B | C | D, ✓ when done), so a student's part-A writing can never be
  misread as part-B's answer; the answer submitted is always the active part's.
  The result panel shows the per-part ✓/✗ and the remaining parts.
- A wrong part builds an explanation (the narration now receives the student's
  answer + part, so Gemini addresses it) and the student retries that part.
- Explanation cache keys include a hash of the deterministic steps, so stale
  narrations from older solver versions are never served.

## Work-checking modes (per-topic grading logic)

`analyze_work` dispatches on the solution's `work_mode` — each topic owns its
own grading logic; probability does not affect the others:

- **default** (complex, limits, integrals): the original strict sequential
  pointer — unchanged.
- **`any_order`** (probability): a line matches *any* checkpoint value (exact,
  then numeric), so the natural count/ratio order and chains of equivalent
  expansion lines all verify; formula-definition lines (symbolic values like
  `(n!)/(r!(n-r)!)`) and jot lines (non-real values like `7 7 1,3,5,7`) are
  skipped, never marked wrong. Checkpoints are count-based to match the
  textbook method (e.g. `two_bag_numbers`: `n(S)`, `n(A)`, `P(A)`).
- Final-answer judging (`grade`/`grade_part`/`grade_multi`, exact/numeric) is
  universal SymPy — unchanged for every topic.

## What's NOT changing

- SymPy stays the source of truth (answers, grading, checkpoints).
- Canvas/OCR/history/stats work unchanged; the topic dropdown just gained
  "Probability".
- Explanations: deterministic steps (English, `\(...\)` math) → Gemini
  narration → cache; `_problem_desc` handles probability params.

## Verification (all green, 2026-08-23)

- `python backend/../scripts/verify_probability.py`: **19 real BAC II problem
  answers match SymPy exactly** (e.g. P1A 14/99, P6C 3/7, P3d 11/24, P2C
  25/27); 60 rolls per catalog scenario — solver never rejects, `0 < P < 1`,
  decimal matches, no leftover `{slots}`, exact+decimal grade correct, wrong
  answer rejected, checkpoint lines all match; regression rolls for
  complex/limit/integrals.
- `scripts/verify_probability_live.py` (stack running): signup → generate per
  difficulty (authentic Khmer prompts) → grade exact/decimal/wrong + work
  line-check + Gemini explanation + `/formulas` (8 techniques) + `/templates`
  (probability rows).
- tsc clean inside the web container.

## Gotchas learned (add to the recipe)

- **`grader.py` hard-coded `params["var"]`** — probability params have no
  `var`; `grade()` and `analyze_work()` 500'd on probability until changed to
  `params.get("var", "x")`.
- **`QuestionCard` renders `prompt_latex` as one KaTeX display block** — never
  put Khmer text in `prompt_latex` (the original plan's "math inside Khmer
  sentence" needs a MathText-style component first).
- **`explainer._problem_desc` 500s on unknown topics** — every new topic needs
  its branch here (the recipe's gotcha, hit again).
- **The "at least one" family is two formulas in one** — the counting step is
  `combination_rule`, the final step `complement_rule`; both land in
  `formula_tags`, so those problems badge `hard`.

## Next steps

1. Real frames for `laplace`, `binomial`, `union`, `conditional` (from actual
   BAC II paper or user confirmation).
2. Optional v2: LLM paraphrase of filled frames (text only, params frozen,
   cached by `scenario_id + params`), behind `cache.allow_gemini`.