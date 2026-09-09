# Adaptive formula practice (planned, not yet built)

Goal: record which formulas a student gets wrong, then teach each missed formula
by generating a practice question that uses the same formula — measure again,
repeat. This plan captures the full design so it can be built as one focused
sprint later.

## What already exists (the foundation — verify, don't rebuild)

- `Attempt.formula_breakdown` (JSONB) — per attempt, per-checkpoint
  `{formula, label, reached, line}`. Stored for every handwritten attempt
  (correct and incorrect) since the step-check runs on all work_text.
- `/stats` → `by_formula` — aggregated reached/missed per formula; rendered as
  the "Formulas to review" table on `/stats`.
- **Variant forcing** — `generator.generate(..., variant=...)` can force a
  specific variant (e.g. `u_substitution`, `by_parts`, `split`). Used by the
  admin `/templates` inventory only; the engine is already capable.
- Formula registry (each topic's `backend/engine/topics/<topic>/data/formulas.json` + built-ins) with
  `name_en`/`name_km`/`latex`/`weight` per technique id.

## The gaps this plan closes

1. The public API can't request "a question using formula X" —
   `GenerateRequest` has no `variant` field.
2. No formula-id → variant(s) mapping exposed to the client.
3. **False-miss problem:** the step-check now runs on correct attempts too, so a
   correct answer solved via an alternative path shows its standard-path
   checkpoints as "missed" — a fake weakness signal. Weakness must count misses
   only from **incorrect** attempts.
4. No "practice this formula" flow in the UI.

## Design decisions (defaults chosen; confirm at build time)

| Decision | Default |
|---|---|
| Trigger | Both: stats-page "Practice" buttons AND a post-grade "Practice: <formula>" prompt on wrong answers |
| Granularity | Variant-level forcing now (a variant emits 1–3 formulas, engine-ready). Template-level forcing (e.g. exactly `u = x²+c` power) later if needed |
| False-miss | `by_formula` aggregates only `Attempt.correct == False` rows |
| Practice log | None for now — forced-variant attempts feed the same attempts/stats stream (getting it right later raises the formula's reached count = "got it now"). A dedicated `formula_practices` table is a later option if week-over-week analytics are wanted |
| API shape | `variant` added to `GenerateRequest` (pass-through, already supported by the generator) |

## Implementation plan

### Backend

1. **`schemas.py`** — add `variant: str | None = None` to `GenerateRequest`.
   Router passes it through `services.create_question` → `generator.generate`
   (already supports it).
2. **`generator.py` — variant index (lazy, memoized)**
   - `variants_for_formula(tag) -> list[{topic, question_type, variant, difficulty}]`
   - Compute by generating + solving each variant once (same technique as the
     admin inventory), map `formula_tags → variant`; cache in a module dict.
   - Self-maintaining: when templates change, the cache refreshes on restart.
   - Note: a formula can appear under several variants — return all, and let the
     client pick the first, or prefer the variant whose difficulty matches the
     student's level later.
3. **`services.py` / `/formulas` response** — each catalog entry gains
   `variants: [...]` from the index, so both the stats page and any client can
   build a "Practice" target for any formula. (No new endpoint needed.)
4. **`get_stats` weakness fix** — `by_formula` query restricted to
   `Attempt.correct.is_(False)`; keep total reached/missed semantics otherwise.
   This is the only behavioral change to existing data.

### Web

5. **`practice/page.tsx` — formula-driven practice**
   - Read `/practice?formula=<id>` (like the existing `?attempt=` review mode).
   - On mount, look up the formula's variants (from `/formulas`), generate a
     question forcing the first variant, show a "Practicing: <name>" banner.
   - Fallback to a normal generate if the formula has no variant.
   - Reuse the existing `variant` plumbing: `api.generate(..., variant)`.
6. **`stats/page.tsx`** — each "Formulas to review" row gets a **Practice**
   button → `/practice?formula=<id>`.
7. **Post-grade prompt (practice page)** — when a handwritten attempt is
   incorrect and `step_check.first_error_line` exists, the wrong line's
   `formula` is the fumbled technique. Show "Practice: <formula name>" next to
   the work-check → navigates to `/practice?formula=<id>`. (This is the
   highest-value moment — the student just failed that exact formula.)
8. **`api.ts`** — `generate` gains `variant`; `FormulaEntry` gains `variants`.

### Docs

9. `docs/pipeline.md` — new section "Adaptive practice: record → suggest →
   force a variant → re-measure", including the false-miss caveat (weakness
   only from incorrect attempts) and the alternative-path limitation (a formula
   checkpoint can be "missed" while the student actually used a valid
   alternative method — the final-answer equivalence grading is the backstop).

## Verification checklist (at build time)

- Unit: `variants_for_formula` returns correct mappings for
  `u_substitution`, `integration_by_parts`, `split_fraction`,
  `linear_argument_rule`, `antiderivative_trig_sec`.
- Live: generate with `variant="by_parts"` via the API → correct variant,
  correct formula_tags.
- Stats: a correct-attempt alternative-path miss no longer counts as a
  weakness; an incorrect attempt's miss does.
- Practice flow: `/practice?formula=u_substitution` loads a u-sub question with
  the banner; post-grade wrong attempt shows the "Practice" prompt for the
  first-error formula.
- Regression: full generator roll suite + existing grading unit checks still
  pass; `tsc` clean.

## Related future work (kept separate)

- **Template-level forcing** (exact template, not just variant) — new param
  later if students need finer targeting.
- **Dedicated practice log** (`formula_practices` table) — only if
  week-over-week practice analytics become a product need.
- **Subscription gating** — "targeted formula practice" is a natural premium
  feature later (`User.plan` already exists).