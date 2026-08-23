# Learning support: Formula sheet + Hints (planned)

Two light, content-driven features that build entirely on existing data
(the formula catalog, the solver's steps, and the registry). Adaptive formula
practice is planned separately (`adaptive-formula-practice.md`); hints and
practice are designed to feed each other ("stuck → hint → practice that
formula").

## 1. Formula sheet page (student-facing)

Browse the full formula catalog, grouped by topic — the same data the admin
page shows (`GET /formulas`), but styled for students.

### What it shows
- Per technique: `id`, English name, Khmer name (once filled in the JSON),
  the rule LaTeX (rendered), weight, and the list of specific formulas under it
  (rendered) — exactly what `/formulas` already returns.
- Topic tabs/grouping: Complex numbers / Limits / Integrals.
- Optional per-formula **"Practice"** link once adaptive practice ships
  (`/practice?formula=<id>`).

### Implementation
- New route `web/src/app/formulas/page.tsx` (AuthGuard), reusing the admin
  page's rendering pattern (MathText with `\(...\)` wrapping).
- Navbar link "Formulas" (next to History/Stats/Admin).
- No backend work: `GET /formulas` already returns the full catalog.

## 2. Hints (progressive disclosure of the existing solution)

The solver already produces every step with `title`, `detail` (LaTeX), and a
`formula` tag. A hint is just revealing that content gradually — deterministic,
no LLM, no math work.

### Hint ladder (on the practice page)
1. **Which formula applies?** — `name_en` + rule LaTeX from the registry for the
   question's first `formula_tag`.
2. **The first step** — title + detail.
3. **More steps** — one at a time (step 2, step 3, …).
4. **Full solution** — the existing "Show steps" (unchanged).

### Design decisions
- Button "Hint" on the practice page; disabled until a question is loaded.
- Data source: the question's `formula_tags` (already returned by generate) +
  `GET /problems/{id}` steps (already returned) + `resolve_formula` names via
  the `/formulas` catalog (client-side lookup).
- **Hint usage recording** (recommended): `Attempt.hints_used` int column +
  migration; the web sends `hints_used` with the grade (or a small
  `POST /problems/{id}/hint` counter). Later analytics: "students who used a
  hint on X got the next X question right Y% of the time."
- LLM hints: NOT needed for v1 (deterministic ladder is better and free).
  Optional later: Gemini rewrites hint 1 in friendlier words (cached like
  explanations).
- Premium gate candidate later (alongside formula practice).

### Implementation checklist
- [ ] `schemas.GradeRequest` + `Attempt.hints_used` + migration (nullable int,
      default 0)
- [ ] practice page: Hint button + ladder state (reveal index), uses
      `question.formula_tags` + steps from `api.question(id)`
- [ ] send `hints_used` on grade; `list_attempts`/detail expose it
- [ ] `web/src/app/formulas/page.tsx` + Navbar link
- [ ] api.ts types (FormulaEntry already has what we need; add `hints_used`)
- [ ] verification: hint ladder shows formula name → step 1 → step 2;
      formulas page renders all 26 entries grouped; `tsc` clean; backend
      restart; live API check

## Relationship to the other plans
- `adaptive-formula-practice.md` — uses the same `/formulas` data and the
  `variant` forcing; hints slot into the "stuck" moment before practice.
- `adding-question-types.md` — new formulas automatically appear on the sheet
  (catalog-driven, no code change).
- Later: exam mode, carry-over line-checking, subscription gating (all
  separately documented / candidate plans).

## Verification checklist (at build time)
- Hint ladder: formula name/latex → step 1 → step 2 … on a fresh question.
- `hints_used` persisted on the attempt and visible in history detail.
- Formulas page renders every catalog entry grouped by topic, math rendered
  (no raw `\frac` leaks), Khmer names shown when filled.
- Full generator roll suite + grading unit checks still pass; `tsc` clean.