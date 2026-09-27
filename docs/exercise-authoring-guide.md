# 📖 BAC II Exercise Authoring & Engine Architecture Guide

This document is the definitive, battle-tested reference for creating, authoring, and maintaining exercises, templates, solvers, and grading rules across the BAC II Math platform.

It captures the real-world lessons, edge cases, and architectural rules discovered across production development.

---

## 1. 🏛️ Core Architectural Principles

1. **SymPy is the Sole Mathematical Authority**:
   - Generative AI (LLMs) must **never** compute arithmetic, limits, derivatives, integrals, or verdicts.
   - All solutions, steps, and intermediate checkpoints are computed deterministically using SymPy 1.13.

2. **Fast Check Architecture (No Blocking on AI)**:
   - Line-by-line grading runs in **10 to 50 milliseconds** via SymPy.
   - Google Gemini is strictly reserved for handwriting OCR (`/vision/detect`) and optional background step-by-step narration (`/problems/explain`). The student's pass/fail verdict is never delayed by an AI call.

3. **Pedagogical Step Integrity (3 to 6 Steps)**:
   - Every single exercise template must emit between **3 and 6 authentic pedagogical steps**.
   - Single-step solutions (e.g. going straight from problem to final answer) are strictly prohibited because they break line-by-line checking and partial credit.

4. **Direct Practice Interoperability**:
   - Any template viewed in the Admin catalog or Structure Modal must be instantly runnable on the live student canvas via `/practice?template=<template_id>`.

---

## 2. 🏗️ The 5-Layer Exercise Anatomy

Adding or updating an exercise involves 5 connected layers:

```
┌────────────────────────────────────────────────────────┐
│ 1. Formula Catalog (data/formulas.json)               │
│    - Unique id, English/Khmer name, weight (1-3)      │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ 2. Parameter Generator (generator.py / structures.py)  │
│    - Constraint pools, clean roots, zero-div guards    │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ 3. SymPy Solver (solver.py)                            │
│    - Deterministic solution, 3-6 steps, checkpoints    │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ 4. Transition Rules & Grader (rules.py / grading.py)   │
│    - Line-to-line transition deduction, partial credit │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│ 5. Practice & Canvas UI (admin & practice pages)       │
│    - Dropdowns, StructureModal, direct practice button │
└────────────────────────────────────────────────────────┘
```

---

## 3. ⚠️ Battle-Tested Gotchas & Hard Rules

### Trap 1: The High-Degree Polynomial CPU Blowout (The $x^{2023}$ Trap)
* **The Bug**: Calling `cancel()` on expressions like $\frac{x^{2023} + 1}{x^{2015} + 1}$ yields a quotient with over 2,000 polynomial terms. When `simplify()` attempts to process this quotient, it pins a Python thread at 100% CPU for over 7 minutes, surviving the request timeout and crashing the server.
* **The Solution**:
  1. **Cap Exponent Simplification**: Skip full `simplify(cancel(expr))` if any exponent in the expression exceeds 20 (`_has_huge_power`).
  2. **Use Algebraic Derivative Identities**: For rational limits with degree $> 6$, apply the Bac II power quotient identity:
     $$\lim_{x \to a} \frac{x^p - a^p}{x^q - a^q} = \frac{p \cdot a^{p-1}}{q \cdot a^{q-1}}$$
     This evaluates instantaneously in 2ms without expanding any polynomials.

### Trap 2: Rigid Checkpoints vs. Carry-Over Checking (`rules.py`)
* **The Bug**: Comparing student lines strictly against a fixed list of precomputed checkpoints marks valid alternative methods as incorrect (e.g. factoring numerator first vs. denominator first, or applying a different trig identity).
* **The Solution**:
  - Implement algebraic transition rules in `engine/topics/<topic>/rules.py`.
  - Given the student's previous line $L_n$ and current line $L_{n+1}$, deduce the exact Bac II rule applied:
    * `factoring_0_0`: Factored polynomials revealing vanishing roots.
    * `cancel_common_factor`: Non-trivial common factors cancelled from numerator and denominator.
    * `trig_half_angle`: Used $1 - \cos(kx) = 2\sin^2(kx/2)$.
    * `trig_double_angle`: Used $\cos(2x) = 1 - 2\sin^2(x)$ or $2\cos^2(x) - 1$.
    * `limit_power_identity`: Used derivative quotient identity on high powers.
    * `direct_substitution`: Evaluated the constant limit value.
  - Verify limit preservation: ensure $\lim(L_{n+1}) = \lim(L_n)$.

### Trap 3: False "Section Label" Rejection in OCR
* **The Bug**: When students write intermediate symbolic equations (such as $f(x) - 1 = \cos(x) - 1$ or factored rational expressions), aggressive regex filters in `grading.py` sometimes mistake them for section headers (e.g. "Part 1:") and discard them.
* **The Solution**:
  - Always cross-reference detected lines against intermediate problem checkpoints.
  - If a line's right-hand side matches a valid checkpoint, it is scored as correct regardless of text prefixes.
  - Repeated lines (e.g. restating the problem on line 1) must be marked as `given` context rather than an incorrect answer.

### Trap 4: Khmer Typography vs. KaTeX Segregation
* **The Bug**: Wrapping Khmer sentences inside KaTeX math mode like `\text{រកលីមីត...}` causes missing glyph boxes, broken line wraps, and bracket leakage in browser rendering engines.
* **The Solution**:
  - **Never** place raw Khmer text inside `\text{...}` inside LaTeX math blocks.
  - Use `latexToMixedText`: Khmer text renders in native browser typography, and only isolated mathematical symbols are placed inside dollar signs (`$...$`).

### Trap 5: SymPy Representation Traps
* **Exponential**: SymPy represents $e^x$ as `exp(x)`, **not** `E**x`. Always check `expr.has(exp)` rather than `expr.has(E)`.
* **Trigonometric Powers**: Students write $\sin^2(x)$, but standard SymPy parsing reads `sin^2(x)` as `(FunctionClass)**2 * x` which errors. Pre-normalize `\sin^n(x)` to `sin(x)**n` before passing to SymPy.
* **Rational Numbers**: Always use `Rational(p, q)` or `S(p)/q` in Python code; writing `p/q` creates Python floating-point numbers which introduce rounding errors into exact CAS proofs.

### Trap 6: Indefinite Integrals Constant Shift
* **The Bug**: In indefinite integrals, any student answer differing by a constant $F(x) + C$ is correct.
* **The Solution**: Checkpoints and answers must specify `"constant_ok": True`, which instructs the grader to check whether the difference `user_answer - expected_answer` has no free variables (`not diff.has(x)`).

---

## 4. 📝 Step-by-Step: Adding a New Exercise Template

### Step 1: Register the Formula
Add the technique to `backend/engine/topics/<topic>/data/formulas.json`:
```json
{
  "limit_power_identity": {
    "name_en": "Power derivative quotient identity",
    "name_km": "រូបមន្តដេរីវេស្វ័យគុណលីមីត",
    "latex": "\\lim_{x \\to a} \\frac{x^p - a^p}{x^q - a^q} = \\frac{p a^{p-1}}{q a^{q-1}}",
    "weight": 2,
    "group": "limit",
    "formulas": [
      "\\lim_{x \\to a} \\frac{x^p - a^p}{x - a} = p a^{p-1}",
      "\\lim_{x \\to a} \\frac{x^p - a^p}{x^q - a^q} = \\frac{p a^{p-1}}{q a^{q-1}}"
    ]
  }
}
```

### Step 2: Define the Generator Template
In `backend/engine/topics/<topic>/rational_structures.py`:
```python
def sample_poly_odd_ratio(rng, difficulty):
    p = rng.choice([2019, 2021, 2023, 2025])
    q = rng.choice([2015, 2017])
    # x -> -1 yields 0/0 form: ((-1)^p + 1) / ((-1)^q + 1) = 0/0
    expr_str = f"(x**{p} + 1)/(x**{q} + 1)"
    return {
        "expr": expr_str,
        "var": "x",
        "point": "-1",
        "p": p,
        "q": q,
        "technique": "limit:rational:poly_odd_ratio",
        "formula_name": "limit_power_identity",
    }
```

### Step 3: Implement the SymPy Solver & Checkpoints
In `backend/engine/topics/<topic>/solver.py`:
```python
# Derive intermediate checkpoints for line-by-line checking
steps = [
    _limit_step("Verify form 0/0", r"Substituting x = -1 yields 0/0.", "setup_limit"),
    _limit_step("Apply power identity", rf"Divide by (x - a) to obtain derivative forms.", "limit_power_identity"),
    _limit_step("Evaluate limits", rf"Evaluate numerator and denominator derivatives.", "limit_power_identity"),
    _limit_step("Compute final quotient", rf"The limit is {latex(result)}.", "limit_power_identity"),
]
checkpoints = [
    {"label": "numerator limit", "value": val_num, "formula": "limit_power_identity"},
    {"label": "denominator limit", "value": val_den, "formula": "limit_power_identity"},
    {"label": "final value", "value": result, "formula": "limit_power_identity"},
]
return steps, checkpoints
```

### Step 4: Register in Transition Rules
In `backend/engine/topics/<topic>/rules.py`:
Add rule detection so if a student evaluates the derivative quotient directly, `deduce_transition_rule(prev, curr)` automatically recognizes `limit_power_identity`.

### Step 5: Wire Web Practice & Admin Navigation
In `web/src/app/admin/page.tsx` and `web/src/components/StructureModal.tsx`:
- Add the pencil Practice button linking to `/practice?template=<template_id>&topic=<topic>&difficulty=<difficulty>`.
- In `web/src/app/practice/page.tsx`:
  * Add the template ID to `TYPE_OPTIONS`.
  * Ensure `searchParams.get("template")` triggers `api.generate("templates", difficulty, topic, question_type, templateId)` and mounts into the canvas.

---

## 5. 🧪 Verification & Health Check Commands

Always verify changes inside Docker before committing:

```bash
# 1. Check all Docker containers are running
docker ps --format "{{.Names}} \t {{.Status}}"

# 2. Test generation, solving, and line-by-line grading inside backend
docker exec bacii-backend-1 python -c "
from engine import grader, solver, generator
import asyncio

async def test():
    q = await generator.generate('limit', 'medium', question_type='limit', variant='limit:euler:cos_zero')
    s = solver.solve('limit', 'limit', q['params'])
    g = grader.grade('limit', 'limit', q['params'], str(s['answer_exact']))
    chk = grader.analyze_work('limit', 'limit', q['params'], ['cos(x)**(1/x**2)', 'f(x) - 1 = cos(x) - 1', str(s['answer_exact'])])
    print('Backend OK! Grade:', g['correct'], 'Checkpoints verified:', len(chk['line_results']))

asyncio.run(test())
"

# 3. Check Web container build and compilation logs
docker exec bacii-web-1 node -e "
const http = require('http');
http.get('http://localhost:3000/practice?template=limit:euler:cos_zero&topic=limit', (res) => {
  console.log('Web route status:', res.statusCode);
});
"
```
