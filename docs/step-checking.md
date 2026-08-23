# Step-by-step checking: two design options

This note records the design tradeoff for how the app verifies a student's written
work line by line. It applies to `backend/engine/grader.py` (`analyze_work`) and
`backend/engine/solver.py` (the checkpoints each solver emits).

## The two approaches

### 1. Checkpoint matching (what exists today)

Each solver precomputes a list of **expected intermediate values** (checkpoints),
in order. Every student line is compared against those values, sequentially:

> "Does your line equal what we think it should be at step 3?"

- Needs a per-type "answer key" (the checkpoints).
- Forces the student onto the expected path.
- Catches errors even in multi-branch work (modulus-style: a², b², then combine).

### 2. Carry-over checking (line-to-line, not yet built)

Each line is checked against the **previous line** instead of against an answer key:

> "Is line N+1 a valid algebra move on top of line N?"

Checked with `simplify(line N − line N+1) == 0`.

- Needs **no per-type answer key** — just the SymPy final answer.
- **Method-agnostic**: any valid alternative path passes.
- Only works when each line is a transformation of the whole expression
  (limits, integrals, equation-solving). Breaks on modulus-style
  sub-computations.
- Must be paired with the final-answer grade, otherwise a consistently-wrong
  chain (same error carried through every line) passes all lines.

## Real example where carry-over wins: limits

`lim x→2 (x²−5x+6)/(x−2)` — a student solves it correctly:

```
(x²−5x+6)/(x−2) = (x−2)(x−3)/(x−2)      line 1: factor
               = x−3                     line 2: cancel
               = −1                       line 3: substitute
```

- Does line 2 follow from line 1? `(x−2)(x−3)/(x−2) − (x−3) = 0` → yes.
- Does line 3 follow from line 2? `x−3` at `x=2` is `−1` → yes.
- Whole chain holds + final answer −1 = correct → **"correct."**

A student who actually errs:

```
(x²−5x+6)/(x−2) = (x−2)(x−3)/(x−2)
               = x−3
               = 3          ← wrong (should be −1)
```

`3` does not follow from `x−3` (at `x=2`, `x−3 = −1 ≠ 3`) → **line 3 is where it
broke**, with no answer key needed.

A student who factors in a different order, or skips writing the factored line and
goes straight to `= x−3`, still passes — each line validly carries the previous.
That alternative-path case is exactly what breaks the checkpoint approach (see the
known bug below).

## Where carry-over does NOT fit: modulus-style work

```
z = 3+4i
a² = 9
b² = 16       ← does 16 "carry over" from 9? No — but it's correct!
a²+b² = 25
|z| = 5
```

Each line is an **independent sub-computation**, not a transformation of the
previous line. Carry-over checking would flag every line as wrong. This is why
modulus is the one type that has always worked with checkpoints. Different problem
shapes need different checkers.

## The gotcha for per-formula weakness stats

The per-formula stats (`formula_breakdown` / `/stats` `by_formula`) depend on
knowing **which formula each step used**. Carry-over only says *"line 3 broke"* —
it can't say *"they missed cancel_common_factor"* unless you also identify the rule
between line 1 and line 2 (factor? cancel? conjugate? substitute?). That
rule-identification is the genuinely hard part (a "rewrite-rules engine"); the
line-checking itself is trivial.

## Comparison

| | Checkpoint matching | Carry-over (line-to-line) |
|---|---|---|
| Needs per-type answer-key | Yes | No — just the final answer |
| Accepts alternative valid paths | No (false flags) | Yes |
| Finds the first error line | Yes | Yes |
| Handles modulus-style sub-computations | Yes | No |
| Tells you WHICH formula was missed | Yes | Only with added rule-tagging |

## Recommendation: a hybrid

- **Checkpoint matching + formula tags** for the fixed-path types (modulus,
  argument, conjugate, real/imaginary part) — it works there and feeds the
  per-formula stats.
- **Carry-over checking** for the transformational types (limits, definite
  integrals) — method-agnostic, needs no answer key, and scales to new topics
  almost for free.
- Both stay anchored by the SymPy final-answer grade.

---

## Current state / known bug (2026-08)

Reproduced bug: for a removable limit, correct work gets a false "WRONG" verdict.

`lim x→−1 (x²−1)/(x+1)` with correct student work:

```
(x^2-1)/(x+1)           → matched "factored form"    (given line consumed the checkpoint)
= (x-1)(x+1)/(x+1)      → matched "cancelled form"
= x-1                   → ❌ flagged WRONG, first_error_line = 3
= -2                    → matched "substituted value"
```

Causes:

1. `solver.py` — the removable-limit `factored form` checkpoint value
   `factor(num)/factor(den)` auto-cancels to `x-1`, identical to the
   `cancelled form` value → two checkpoints share one value.
2. `grader.py` — the original expression `(x²−1)/(x+1)` is mathematically `x-1`,
   so the restatement of the given consumes the `factored form` checkpoint; the
   real "= x-1" then has nothing left to match but `-2`.
3. `llm.py` — non-matches are labeled "WRONG at this step", and the `check_work`
   prompt calls the line "authoritative — do not second-guess", so Gemini is
   forced to defend a false verdict. Gemini is also never given the expected
   checkpoint **values**, only labels, so it cannot re-check the algebra.

Applied fix (three parts, done):

1. **grader.py + solver.py** — the limit/integral solvers now expose the *given expression*
   (`solver.py`: `"given"` in `_solve_limit` / `_solve_definite_integral`), and
   `analyze_work` skips any line whose parsed value is structurally equal to it, so
   the given stops consuming a checkpoint.
2. **llm.py `_step_check_summary`** — each line now carries the expected value, and
   non-matches are worded "could not verify (expected value: …)" instead of "WRONG".
3. **llm.py `check_work`** — tiered trust: OK lines are certain; "could not verify"
   lines are a hint to re-check against the expected values and accept valid
   alternative steps. The "authoritative — do not second-guess" muzzle is removed.

---

## Multiple solution paths, grey lines, and equivalence checking

Calculus problems can be solved in multiple valid ways that produce
*different-looking but equal* answers — e.g. `∫ sin x cos x dx`:

| Route | Result |
|---|---|
| u-substitution, u = sin x | `½ sin²x + C` |
| u-substitution, u = cos x | `−½ cos²x + C` |
| double-angle identity | `−¼ cos(2x) + C` |

All three are identical up to the constant `+C`. Students also skip steps (tabular
method, mental `e^{ax} → (1/a)e^{ax}` jumps). The engine handles this at two layers.

### Layer 1 — final answer: CAS equivalence, never text

`grade()` compares math, not strings: it simplifies `user − expected`. For
indefinite integrals, the rule is *"the difference contains no variable"* — any
`F(x) + constant` is a valid antiderivative, so `½sin²x`, `−½cos²x`, `−¼cos2x`,
`(1−cos2x)/4`, `F + 5`, and `F` with no `+C` at all all grade correct; a genuinely
wrong `sin²x` is rejected. The exact-value verdicts (numeric tolerance, angle
modulo) are unchanged.

**The hybrid equivalence ladder** (`grader.py` `_equivalent_exact` /
`_equivalent_const`): `simplify(diff)` → if nonzero, `simplify(diff, fu=True)`
(trig-intensified) → if still nonzero, **numeric sampling** at deliberately
non-special points `(0.37, 1.23, 2.71, 3.87, 5.03)`. For exact equivalence the
sampled difference must be ~0 everywhere; for constant equivalence the sampled
values must all be equal. `simplify` is not a decision procedure, so sampling is
the safety net for exotic equivalent forms; two non-equal high-school expressions
agreeing at all five points is effectively impossible.

### Layer 2 — line-by-line: the "grey" tier and the grey-recheck fix

`analyze_work` matches each line against the solver's checkpoints in order. A line
that fails to match any checkpoint is **"could not verify" (grey)** — a hint, never
a wrong verdict. Alternative-path intermediates and skipped steps land here, and
the AI is told to re-check them against the expected values rather than treat them
as authoritative.

**The grey-recheck fix:** antiderivative checkpoints (indefinite **and** definite)
carry `constant_ok`, so an equivalent-form `F` line like `−cos²x/2` against the
expected `sin²x/2` goes **green** instead of grey — the difference (¼) has no x,
and constants cancel in `F(b) − F(a)` anyway. A line like `sin²x/2 + x` still
stays grey (the difference contains x). The fix is one flag on the checkpoint;
the constant-equivalence check reuses the already-computed diff, so it costs
nothing extra.

### What happens on a WRONG answer (the flow)

1. **Final answer** (`grade()`): parse → one `simplify(user − expected)` → not 0,
   not constant-equivalent, not numeric-close → **mismatch**. (If the answer
   parses as a symbolic antiderivative, the indefinite branch decides alone and
   never falls through to the float-based numeric check — that used to crash.)
2. **Explanation pipeline** (only on incorrect): deterministic steps → optional
   Gemini narration (Redis-cached per question, rate-limited) — seconds, and it
   dwarfs every SymPy cost below.
3. **Line-by-line** (`analyze_work`): per line, the diff is computed **once** and
   reused; numeric checkpoints (substituted values, `F(upper)`, `F(lower)`)
   fail via the fast numeric check and **never escalate** — equality is equality
   for numbers; only `constant_ok` (expression) checkpoints may escalate to
   `fu` + sampling. The worst case is a few hundred milliseconds on one
   antiderivative line, at most once per question. Measured: a wrong 3-line
   attempt costs ~40 ms of SymPy.

### Where equivalence does NOT apply

Numeric value checkpoints: `= 6` cannot be "constant-shifted" to match `= 8`.
Only expression-valued antiderivative lines get the constant rule.
