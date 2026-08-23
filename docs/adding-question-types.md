# How to add a new question type / template

The exact steps used to add topics and question types (limits, definite/infinite
integrals, the u-substitution and linear-argument variants, the indefinite
exercises). Follow them in order and run the verification checklist at the end.

## 1. Record the formulas first (content)

Formulas live in `backend/data/formulas/*.json` (merged over the built-in
registry in `engine/formulas.py` — built-ins are the fallback). One entry per
**technique id** (what the solver will tag), not per formula:

```json
{
  "antiderivative_reciprocal": {
    "name_en": "Reciprocal antiderivative",
    "name_km": "",                    // fill in Khmer later
    "latex": "\\int \\frac{1}{x}\\,dx = \\ln|x| + C",
    "weight": 1,                      // difficulty weight (0 = informational)
    "group": "integral",              // topic the formula belongs to
    "formulas": ["\\int \\frac{1}{x}\\,dx = \\ln|x| + C"]
  }
}
```

- The id you choose here is exactly what the solver emits in step tags.
- Difficulty = sum of distinct tags' weights (≤1 easy, 2 medium, ≥3 hard).
- Unknown ids never crash (fallback: raw id, weight 1).

## 2. Add the solver (`backend/engine/solver.py`)

1. Write `_solve_<type>(params)`:
   - Compute the answer with SymPy (the only math authority).
   - `steps`: each step gets `"formula": "<technique id>"`.
   - `checkpoints`: list of `{"label", "value", "formula"}` dicts — the expected
     value at each step, in order, for line-by-line checking. Add
     `"constant_ok": True` when any constant shift is acceptable (indefinite
     integrals).
   - `formula_tags`: derive with `_formula_tags(steps)` (ordered distinct ids).
   - `given`: the original expression (lets `analyze_work` skip restatements).
   - `answer_decimal`: `None` is fine for symbolic answers.
2. Register: add the type to `QUESTION_TYPES_BY_TOPIC[topic]` and a branch in
   `solve()`.

Gotchas learned:
- `e**x` becomes `exp(x)` in SymPy — check `term.has(exp)`, not `has(E)`.
- `_calc_locals` maps `e → E` — without it, `e^(kx)` answers crash
  `float(N(...))` and don't match the grader's `e → E`.
- `explainer._problem_desc` must handle your new type's params (e.g. indefinite
  integrals have no `lower`/`upper` — forgetting this 500s on explanations).

## 3. Extend the grader only if the rule differs (`backend/engine/grader.py`)

- New grading semantics (e.g. indefinite: any `F(x) + const` is correct →
  `not simplify(user - expected).has(var)`).
- `analyze_work` checkpoint matching: honor new checkpoint flags (see
  `constant_ok`).

## 4. Add the generator template (`backend/engine/generator.py`)

1. Write `_generate_<type>(rng, difficulty)`:
   - **Parameterize everything.** Pick coefficients/constants/bounds from pools.
     No template may produce the same question twice (the definite-integral
     `trig` variant was fixed at `0→π/2`, answers always 1 — don't repeat that).
   - Choose bounds so answers stay clean: `0→π/2`, `0→π/(2k)`, `0→1`, special
     angles. SymPy gives exact answers regardless, but clean ones are better for
     students and the grading UX.
   - Return via `_build_expr_problem(...)` (or `_build(...)` for complex),
     including `"variant"` and any metadata in `params`.
2. Wire the dispatch: `_generate_expr_templates` (or `generate()` for complex),
   question-type validation lists, and `_INTEGRAL_VARIANT_BY_DIFFICULTY` /
   `_LIMIT_VARIANT_BY_DIFFICULTY` pools.
3. Curated exercise shapes: keep them as **parameterized templates** with
   `{a}/{b}/...` slots filled from `_COEFF_POOLS` (never verbatim fixed
   integrands) — same shape, different numbers.

## 5. Web dropdown (`web/src/app/practice/page.tsx`)

Add the new type to `TYPE_OPTIONS[topic]` (label shown to students).

## 6. Verify (the checklist)

Backend:
```bash
cd backend
python -m py_compile engine/solver.py engine/grader.py engine/generator.py
# rolls: generate many per difficulty → solve → grade exact answer == correct
# + the type's edge cases (e.g. "+C"/"+5"/wrong for indefinite)
# + confirm formula_tags include the new ids
```
Live:
```bash
docker compose -f ../docker-compose.yml restart backend
# signup → POST /problems/generate (new type) → grade correct + wrong answers,
# wrong answers must also build explanations (no 500)
```
Web:
```bash
cd web
node node_modules/typescript/lib/tsc.js --noEmit   # filter for your files
docker compose up -d --build web
```

The admin page (`/admin`) picks everything up automatically: `/formulas` shows
the new catalog entry, `/templates` shows a live sample of the new template
(seed-per-row, all variants forced for integrals).

## Related patterns

- **Exam bank data** (fixed real questions): `data/bacii-exam/<topic>/*.json` +
  a verify script (`scripts/verify_limits.py`) that SymPy-checks every answer.
  Bank JSON at repo root is NOT mounted into the backend container — playable
  curated questions live in the generator pools instead.
- **Formula sheet**: the catalog JSON (`backend/data/formulas/*.json`) doubles
  as student-facing content (names, translations, the `formulas` list).