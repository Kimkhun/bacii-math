# Pipeline: how a question flows through the app

End-to-end walkthrough of the BACII Math pipeline — generation, OCR,
grading, step-checking, explanations, history, and stats. Companion to
`adding-question-types.md` (how to extend it) and `step-checking.md` (why it's
designed this way).

## Request flow

```
Web (3016)                    Backend (8016)
──────────────────            ────────────────────────────────
practice page  ──generate──▶  generator.generate()   (templates or gemini)
                                  │
                                  ▼
                              solver.solve()  ←── SymPy (source of truth)
                                  │  answer_exact, steps, checkpoints,
                                  │  formula_tags, given
                                  ▼
                              Question + Step rows (formula per step)
                                  │
canvas ink ──detect──▶  vision.detect_math()
                              preprocess (crop-to-ink + upscale)
                                  │
                                  ▼
                          OCR: Gemini vision | Ollama qwen2.5vl | fallback
                          → lines, lines_latex, lines_boxes, raw_text
                                  │
answer+work ──grade──▶  grader.grade()        (exact/numeric/angle/indefinite)
                                  │
                                  ▼
                        analyze_work()       (line-by-line vs checkpoints)
                        → step_check (per-line verdicts + formula)
                        → persisted: work_text, step_check, lines_boxes,
                                     formula_breakdown
                                  │
                          if incorrect:
                              explanation: deterministic text →
                                  Gemini/Ollama narration (Redis-cached,
                                  rate-limited 10/min/user)
                              work_check: LLM anchored on step_check
                                  ("could not verify" lines are hints, not law)
```

## 1. Generation

- **Templates** (`generator.py`): parameterized pools per topic/type/difficulty.
  Every template randomizes its coefficients/constants/bounds so no question
  repeats. SymPy re-validates nothing at generation (it IS the computation).
- **Gemini mode** (complex only): the LLM *proposes* a problem; SymPy
  recomputes and validates the answer before acceptance.
- Generated problems carry `params` (JSONB spec), `prompt`/`prompt_latex`,
  `source` (`template` | `gemini`), and after solving, `formula_tags` +
  `formula_difficulty` (sum of formula weights → easy/medium/hard).

## 2. Solving (`engine/solver.py`)

`solve(topic, question_type, params)` dispatches to the per-type solver, which:

1. Computes the answer with SymPy (the only math authority — never the LLM).
2. Builds `steps` (title/detail + a `formula` tag per step).
3. Builds `checkpoints` — the expected value at each step, in order, for
   line-by-line checking (`{"label", "value", "formula"}`, plus
   `constant_ok` for indefinite integrals).
4. Emits `formula_tags` (ordered distinct ids) and `given` (the original
   expression, so restatements are skipped during checking).

## 3. Handwriting detection (`engine/vision.py`)

1. `_preprocess` crops to the ink strokes (with padding) and upscales; returns
   the crop bounds.
2. The OCR prompt asks for, per line: plain-text math (`lines`), display LaTeX
   (`lines_latex`), and a normalized bounding box (`lines_boxes`).
3. Boxes are mapped from the cropped image back to the original image's pixel
   coordinates (the upscale factor cancels; only the crop offset matters).
4. Provider: `VISION_PROVIDER=gemini` (default) | `ollama` | `fallback`.
5. `raw_text` = the final answer; `lines` = work text fed to grading.

## 4. Grading (`engine/grader.py`)

- `parse_answer` normalizes text (π→pi, ×→*, √→sqrt, strips leading
  `lim_{x→a}` notation, Khmer-ready) and parses with SymPy.
- `grade()` verdicts, in order: **exact** (`simplify(user−expected)==0`),
  **indefinite** (difference has no variable → any F+const is right),
  **numeric** (tolerance, `_angle_close` for arguments), else **mismatch**.
- `analyze_work()` matches each student line against the checkpoints
  sequentially: match = verified correct (with the formula name); non-match =
  "could not verify" (NOT "wrong") — the LLM may re-check unverified lines.

## 5. Explanations & work checks (`services.py`, `engine/llm.py`)

- Deterministic `build_text` is always available; Gemini narrates it in
  friendlier language when allowed.
- Explanation cache: Redis key `explain:{topic}:{question_type}:{spec}` —
  identical questions never re-bill Gemini.
- Gemini rate limit: `allow_gemini` (default 10/min/user).
- Provider chain: Gemini → Ollama → deterministic text (never blocks grading).

## 6. Canvas feedback (web)

- OCR boxes + `step_check` drive the red-pen overlay: ✓/✗, formula labels,
  white halos, collision-free placement (right → left → below the line),
  progressive reveal (1s per line).
- Live ink pops use per-line ink snapshots (grow-and-settle, seamless at
  scale 1); review mode pops the re-drawn text lines.
- Sounds: Web Audio; pitch rises one semitone per consecutive correct mark
  (correct answers ding every line regardless of intermediate verdicts;
  wrong answers: dings for correct lines, one thud for the first error).
- Streak persists in localStorage (`bacii_streak`).

## 7. History, stats, admin

- `/attempts` — enriched list (question context via join).
- `/attempts/{id}` — full detail: work text, step check, lines boxes,
  explanations, question steps. Review mode (`/practice?attempt=<id>`) loads
  this and re-draws the writing at its stored box positions.
- `/stats` — `by_topic` and `by_formula` (aggregated from `formula_breakdown`).
- `/formulas` + `/templates` — admin views over the live catalog and
  generator inventory (deterministic samples, seed per row).

## Math notation & rendering (plain text / LaTeX / KaTeX)

The same math exists in **three representations** in this app — never confuse
them:

1. **SymPy / plain text** — what the engine computes and parses
   (`x**2/2`, `(x-1)*(x+1)`). Feeds `grader.parse_answer`, checkpoints, and the
   OCR `lines`. LaTeX is **never** fed back into SymPy.
2. **LaTeX strings** — display-only text notation (`\frac{a}{b}`,
   `\lim_{x\to 2}`, `\int_0^1 x\,dx`). Produced by:
   - `latex(expr)` — SymPy's built-in converter (`solver.py`): `answer_latex`,
     step `detail`s (wrapped in `\( ... \)` by `inline_latex`),
     `_solve_*` step text.
   - The OCR prompt asking the vision model for `lines_latex` per line
     (`vision.py` keeps it display-only, while plain `lines` go to the grader).
   - The formula catalog `latex` fields and the generator's `prompt_latex`
     (`\text{...}`, `\int_a^b`, `\lim_{x \to a}`).
   - Delimiters: `\( \)` inline, `\[ \]` / `$$ $$` display.
3. **Rendered HTML** — what the user sees, produced by **KaTeX** (a JS math
   renderer):
   - `MathText` (components/MathText.tsx) uses `katex/contrib/auto-render` —
     scans text for the delimiters and renders each chunk, leaves the rest as
     plain text.
   - `QuestionCard` renders `prompt_latex` directly via
     `katex.renderToString` (+ `katex/dist/katex.min.css`).

Chain: **SymPy computes → `latex()` emits a display string → `\(...\)`
delimiters → KaTeX renders in the browser.** Why LaTeX at all: it's the
standard math text notation, SymPy emits it natively, and KaTeX renders it fast
client-side. (This is also why the LLM narration prompt forces `\(...\)`
delimiters — otherwise Gemini outputs raw `lim(x -> 2)` that renders as text.)

## Data model

```
users(id, email, hashed_password, plan='free', created_at)
questions(id, topic, question_type, difficulty, spec JSONB, prompt,
          prompt_latex, z_display, expected_answer, expected_decimal,
          source, formula_tags JSONB, created_at)
steps(id, question_id, step_order, title, detail, formula)
attempts(id, user_id, question_id, user_answer, parsed_answer, correct,
         reason, work_text, step_check JSONB, lines_boxes JSONB,
         formula_breakdown JSONB, created_at)
explanations(id, attempt_id, question_id, provider, content,
             intervened, trigger, created_at)
```

Formula content lives OUTSIDE the DB in each topic's `backend/engine/topics/<topic>/data/formulas.json`
(loaded over the built-in registry at import; edited without touching code).

## Still not documented (candidates for future docs)

- The subscription/plan roadmap (User.plan already in place).
- Deployment & env matrix (partially in CLAUDE.md).
- Exam-bank offline pipeline end-to-end (data → verify script → playable).
- Audio/streak system details (sounds.ts: Web Audio synthesis, streak keys).