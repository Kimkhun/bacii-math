# Migrating a topic to template registries + LLM-planned blueprints

How a topic moves from **replaying fixed curated exercises** to **generating a new exercise every
time from named templates**, each template carrying a **blueprint**: a marking scheme an LLM
planned once, offline, which SymPy re-evaluates on every question's own numbers to drive the
step-by-step checker and the points rubric.

Done so far: **derivatives** (74 templates, the reference implementation) and **differential
equations** (23 templates, the pilot that generalized the core). This guide is the recipe for the
rest (integral, limit, vectors_space, conics, continuity, probability, complex). `functions` and
`past_exam` stay out: `functions` is a multi-part study with its own grader, and `past_exam` replays
a real paper whose marking scheme is already hand-listed in the printed order
(`engine/topics/past_exam/rubric.py`).

---

## 1. Why

Before the migration, a topic typically served half its questions verbatim from
`data/curated/*.json` and half from samplers whose shape was picked at random and never recorded.
That has three problems:

1. **Repeats.** A student sees the same textbook exercise again; the answer can be memorized.
2. **Nothing to key a marking scheme on.** A question didn't say which shape it was, so there was no
   per-shape list of the intermediate results a marker gives points for. Grading saw the final
   answer and whatever few checkpoints the solver happened to compute.
3. **No partial credit for the real method.** Without the intermediate steps (u′ and v′, the roots,
   y_p, C₁ and C₂...), a student with a correct method and a slip at the end scores 0.

After the migration:

- every question is sampled from a named **structure** (template) and records
  `params.template_id` + `params.template_params`;
- every curated exercise survives as an **instance** of some structure (its slot values are
  recorded), so nothing from the textbook is lost, only no longer replayed verbatim;
- every structure has a **blueprint** whose checkpoints become the graded steps, with partial credit,
  alternative methods, and "not shown: …" feedback with the question's own numbers.

The core principle is unchanged: **SymPy is the source of truth.** The LLM only *plans* which steps
to grade and how each relates to the previous ones. It never supplies a value that is trusted.

---

## 2. The end state, file by file

```
engine/core/blueprints.py          topic-neutral: load / evaluate / resolve / validate / same_plan,
                                   relation registry (derivative, outer_derivative, combination,
                                   substitute, solve; register() for more)
engine/core/rubric.py              method_rubric(**policy): score_work + select_method for any topic
engine/core/grading.py             _equivalent_renamed: a step with free constants accepts the
                                   student's own constant names
engine/topics/<topic>/
  structures.py                    the registry: STRUCTURES, STRUCTURES_BY_ID, instantiate,
                                   slot_names, CURATED_INSTANCES (or source_labels)
  generator.py                     samples only from the registry; tags template_id/template_params;
                                   build_<topic>_variant(s) for admin cards
  solver.py                        calls blueprints.resolve(...) and uses the plans' checkpoints
  rubric.py                        score_work, select_method = method_rubric(<policy>)
  blueprint_spec.py                prompt + schema + truth + validation rules for the LLM
  data/blueprints.json             the accepted blueprints (written by the script, never by hand)
scripts/
  generate_blueprints.py           Gemini → SymPy gate → data/blueprints.json (any topic)
  audit_<topic>_structures.py      registry audit (samplers, instances, solve, grade)
  simulate_blueprint_students.py   end-to-end: every method of every template scores full marks
backend/services.py                _registry_topics(): admin cards / regenerate / custom solve / summary
web/src/lib/templateIds.ts         template-id prefix → topic / question type, variant fetching
```

---

## 3. The recipe

Work in this order. Each step has a check, and nothing is deleted until the step that replaces it
passes.

### Step 1: Inventory what the topic serves today

List every source of questions:

- the curated pool (`data/curated/*.json`): count the items and group them by shape;
- every branch of every sampler (each `rng.choice` that changes the *shape*, not just the numbers);
- anything that reads the curated pool elsewhere (`grep -rn _<TOPIC>_CURATED`): typically
  `engine/core/skills.py` (skill catalog), `engine/core/template_shapes.py` (admin cards), and the
  topic's `generator.py`.

The output is a table: *shape → which curated items are instances of it → which sampler branch
produces it*.

### Step 2: Write `structures.py`, the registry

One entry per shape. Copy the field names of `engine/topics/derivatives/structures.py` /
`differential_equations/structures.py`:

| field | meaning |
|---|---|
| `id` | `"<prefix>:<category>:<name>"`, e.g. `deriv:quotient:linear_over_linear`, `ode:second_hom:double_root`. The prefix must be mapped in `web/src/lib/templateIds.ts`. |
| `question_type`, `category` | the solver branch / skill key (derivatives: technique; ODE: `kind`) |
| `difficulty` | the pool it is drawn from |
| `pattern` | the shape with `{slot}` placeholders; **every slot must appear in it** (`slot_names` reads them from it) |
| `pattern_latex` | the admin card header, in the textbook's own notation |
| `sampler(rng) -> (built, slot_values)` | draws clean values; `built` must equal `instantiate(struct, slot_values)` |
| `origin` | `"sampler"` (an old sampler produced it) or `"curated"` (a shape only the textbook had) |
| `source_labels` | the curated exercise ids that are instances of it |
| `narration` | the technique sentence shown in the solution steps |

Design rules learned the hard way:

- **Build from the answer backwards.** Slots should be the *generating* parameters, chosen so that
  everything downstream is clean. ODE slots are the characteristic roots and the particular
  solution's coefficients; the equation's coefficients and right-hand side are *computed* from them
  (`rhs = L[y_p]`), never typed. Then every instance is solvable with integers, and the blueprint can
  name the roots directly.
- **Substitute symbolically, never by pasting text** (`_sub` / `instantiate` replace `{a}` with a
  `Symbol` and `.subs` the value), so a negative or fractional value can't corrupt the expression.
- **`expand`, not `simplify`, for display.** `simplify` folds `2 sin x + 2 cos x` into
  `2√2·sin(x + π/4)`, which no textbook writes.
- **Slot names:** avoid `e` (Euler's number), `i`/`I` (imaginary unit), `x`, `y`, `t`, and the
  topic's own symbols (`C1`, `C2`, `A`, `B`...). LLMs and people both misread them.
- **One blueprint must fit every instance.** If two instances need a different *solution form*
  (distinct roots → `C1 e^{r1 x} + C2 e^{r2 x}`, a double root → `(C1 + C2 x) e^{rx}`), they are
  different structures. A form that degrades gracefully (`e^{αx}(C1 cos βx + C2 sin βx)` with α = 0)
  can stay one structure.
- **Sampler constraints belong in the sampler** (re-roll until valid): no resonance, no zero root
  under a constant right-hand side, initial conditions that don't zero every constant, and so on.
- **Record every curated exercise as an instance.** ODE keeps
  `CURATED_INSTANCES = {struct_id: {curated_id: slot_values}}`, and the audit rebuilds each one.
  Before deleting the curated file, check that each instance rebuilds the *exact* original question
  (coefficients, right-hand side and initial conditions equal under SymPy). The pilot did this for
  all 30 ODE exercises.

### Step 3: Rewrite `generator.py`

- Sample only from the registry. Keep the topic's public entry point and its `variant` semantics
  (old variants such as a kind/technique still work); also accept a structure id as `variant`.
- Tag every question:
  ```python
  params = {**instantiate(struct, values), "template_id": struct["id"],
            "template_params": dict(values), ...}
  ```
  `template_params` is **nested**, never spread into `params`: the grader treats a top-level param
  name as a given, so a student line like `a = 2` would be skipped as a restatement.
- Keep any field the rest of the app keys on (ODE keeps `kind`: skills, lessons and the practice
  page all read it).
- Add `build_<topic>_variant(struct, seed, template_params=None)` and `build_<topic>_variants` for
  the admin cards (copy the derivatives ones).

### Step 4: Audit the registry

Copy `scripts/audit_ode_structures.py`. It must check: unique ids, known categories, sampler output
equals `instantiate` with no missing or extra slots, every curated instance rebuilds and solves, and
for N seeds the question solves, **the answer satisfies the problem independently** (ODE: substitute
it into the equation and the initial conditions), the grader accepts the solver's own answer and
rejects a perturbed one. Run it with 10 seeds before going further.

### Step 5: Plumbing (admin, practice, skills)

- `engine/core/template_shapes.py`: `<topic>_card = _registry_card(struct, build_<topic>_variants)`,
  and the topic's shape builder returns one card per structure.
- `engine/core/skills.py`: build the topic's skill list from the registry's categories instead of
  the curated pool.
- `backend/services.py`: add one line to `_registry_topics()`. That gives regenerate, custom-param
  solve and the summary counts.
- `web/src/lib/templateIds.ts`: map the id prefix to the topic (`PREFIX_TOPIC`) and the topic to
  its question type (`TOPIC_QUESTION_TYPE`); add the prefix to `hasStructureVariants`.
- Delete the curated JSON (`git rm`). It is no longer served, and every item is recorded as an
  instance.

### Step 6: Write `blueprint_spec.py`, what the LLM writes and what SymPy checks

The module `scripts/generate_blueprints.py` imports. Required names:

| name | purpose |
|---|---|
| `TOPIC`, `FORMULA` | topic id, the formula tag the checkpoints carry |
| `structures()` | the registry |
| `instantiate` | re-exported from `structures.py` |
| `truth(struct, built, x)` | **the final answer from the topic's own solver**, never the blueprint's |
| `validate(bp, struct, samples, seed)` | calls `blueprints.validate(...)` with the topic's options |
| `template_brief(struct)` | how one template is shown to the LLM (the problem in slot terms, the slots, notes on them) |
| `PROMPT`, `RESPONSE_SCHEMA` | the instructions (with worked examples) and the JSON schema |
| `ALTERNATIVES_PROMPT`, `ALTERNATIVES_SCHEMA`, `alternative_brief` | for `--alternatives` |

Optional, for a topic whose question isn't one function `y` of `x`:

| name | purpose |
|---|---|
| `given_env(struct, built)` | the named givens (`{}` for ODE; `{"A": ..., "B": ...}` for vectors) |
| `SYMBOLS` | extra symbols expressions may use (ODE: `C, C1, C2` arbitrary constants; `A, B, D` undetermined coefficients) |
| `required(struct, bp, values, x, built, final)` | **the topic's semantic checks**; see below |

**The checks are the most important part.** `blueprints.validate` already rejects, on 6 random
instances: unknown names, an LLM-written value (`expr`) that disagrees with SymPy's value of the
relation, a step equal to the givens / the final answer / an earlier step on most instances (not
gradable by value), and a step that is always 0. But `expr` is the LLM checking itself: if it
writes the same wrong thing in both the relation and `expr`, only `required` catches it. So give
every checkpoint a **role** and verify the role's meaning. The ODE spec is the model:

| role | verified on every sample |
|---|---|
| `root` | `P(value) = 0` for the characteristic polynomial |
| `discriminant` | `value = b² − 4c` |
| `alpha` / `beta` | real part / \|imaginary part\| of a complex root |
| `particular_solution` | `L[value] = rhs`, no arbitrary constants |
| `homogeneous_solution` / `general_solution` | solves `L[y] = 0` / `L[y] = rhs`, with exactly *order* constants |
| `constant` | substituting all of them into the general solution gives the final answer |
| `coefficient` | a solved number, and the particular solution it builds is graded |
| `derived` | only a derivative/substitution of earlier steps (no free-form `combination`) |

…plus structural rules: no unsolved coefficients in a graded value, no constants-only expression
(`C1 + C2` from `y(0)`, a student never writes it as a value), the steps a marker always wants are
present (the roots, y_p, every constant the initial conditions fix), and `expr` may be left empty
for long formulas (`expr_optional=True`) because the roles carry the real check.

Then **test the checks before spending money**:

1. Every worked example in your `PROMPT` must itself pass `validate` (a script extracts and
   validates them). The ODE pilot's three did.
2. Mutation-test the checks: break the examples the way an LLM would (wrong sign in y_p, wrong
   exponent in y_h, `y(1)` instead of `y(0)`, a missing constant, an unsolved trial form, the final
   answer as a step, ...). Every mutation must be **CAUGHT**. The ODE pilot caught all 12.

Prompt tips that cut rejections:

- Spell out the syntax: `*` everywhere, `exp/log/sqrt`, `I`, `diff(E, x)`, `E.subs(x, 0)`.
- State the rules the checks enforce *in the prompt*: no final answer as a step, distinct values,
  nothing that is always 0 (the discriminant of a double root, α for `y'' + ω²y`), no
  constants-only steps.
- Give 3 worked examples covering the topic's main forms, with Khmer labels.

### Step 7: Wire the solver

```python
plans = blueprints.resolve("<topic>", params.get("template_id"), params.get("template_params"),
                           given=<expr or {} or named dict>, final=answer, x=x,
                           formula="<formula>", symbols=SYMBOLS)
if plans:
    checkpoints = plans[0]["checkpoints"]          # the standard method
    aux_checkpoints = plans[0]["aux_checkpoints"]  # steps right wherever they appear
return {..., "checkpoints": checkpoints, "aux_checkpoints": aux_checkpoints, "methods": plans}
```

`resolve` returns `[]` for a template with no accepted blueprint (keep the solver's old checkpoints
then), and silently skips a method that fails on an instance: **a bad blueprint never breaks
grading.** The last checkpoint of every plan is always the solver's own answer.

Watch for solver fields that pre-empt a checkpoint. ODE's `given_expressions` (a restated general
solution is skipped as "given") had to drop any expression a blueprint step now grades, or that step
could never score.

### Step 8: Choose the scoring policy (`rubric.py`)

```python
from ...core.rubric import build_rubric, method_rubric
score_work, select_method = method_rubric()                       # default policy (ODE)
score_work, select_method = method_rubric(implied_credit=False,   # derivatives: every step shown
                                          split_chains=True, term_credit=True, prime_credit=True)
```

`method_rubric` scores the work against each blueprint method and keeps the one it follows, and
`analyze_work` marks the lines against that same method, so the ✓/✗ marks and the points always
agree. It also attaches each step's expected value, so a missed step shows as "not shown:
y_p = 2x + 4", and the AI work-check is told which steps are missing.

### Step 9: Generate the blueprints

```bash
cd backend
export GOOGLE_APPLICATION_CREDENTIALS=$PWD/credentials/gemini-service-account.json
PYTHONPATH=. python scripts/generate_blueprints.py --topic <topic>                  # standard methods
PYTHONPATH=. python scripts/generate_blueprints.py --topic <topic> --alternatives   # 0-2 more each
PYTHONPATH=. python scripts/generate_blueprints.py --topic <topic> --validate-only  # re-check the file
```

How it runs: templates go to Gemini in batches (`--batch`). Each answer goes through `spec.validate`;
a rejection is sent back with SymPy's exact reason, up to `--retries` more rounds. Only accepted
blueprints are written (after every batch, so an interrupted run keeps its progress). Re-running
skips templates that already have one (`--force` / `--only <id>` to redo).

Practical notes from the pilot:

- **Expect several rounds.** ODE accepted 13/23 in round 1. The rejections were real plan problems
  (a step that is always 0, a coefficient equal to a root on most instances), and the feedback fixed
  them.
- **A rejection can be your bug, not the LLM's.** Two ODE rejections ("0 solutions for A, B") came
  from the `solve` relation simplifying before matching coefficients. If a reason looks like the
  checker misread a correct plan, reproduce it by hand before re-running. A running process keeps
  the old code; restart it after a fix.
- **Long answers time out.** Big templates (10+ steps) can exceed 120 s. Use `--batch 1
  --timeout 300`, and `--thinking-budget <tokens>` for a template that keeps timing out.
- **Cost** is printed at the end of each run (prompt and output tokens). A 23-template topic with
  retries is well under a dollar on gemini-3.5-flash.

### Step 10: Verify end to end

1. `generate_blueprints.py --topic <topic> --validate-only`: every saved method re-validates.
2. `scripts/simulate_blueprint_students.py --topic <topic> --seeds 3`: for every method of every
   template, a student writing that method's steps plus the answer gets **full marks, no flagged
   line**, and is scored against that method (or one tying at full marks). ODE: 69
   works (23 templates × 3 questions), all full marks with no line flagged.
3. `scripts/audit_<topic>_structures.py 10` again.
4. **Regression on the topics you didn't touch.** If you changed anything in `engine/core/`,
   snapshot `solve` + `score_work` + `analyze_work` for derivatives (and any other migrated topic)
   from a clean checkout of the base commit and from your tree, and diff them. The ODE pilot changed
   `blueprints.py`, `rubric.py` and `grading.py`: 74/74 derivative templates came out identical.
5. Type-check the web if you touched it (`tsc --noEmit`).

### Step 11: Document

Update `docs/engine-layout.md` (the topic's line), the topic's `__init__.py` docstring, and the
status table below.

---

## 4. The blueprint format (reference)

`data/blueprints.json`:

```json
{
  "ode:first_nonhom:linear_rhs": {
    "methods": [
      {
        "method_id": "primary", "name_en": "Standard method",
        "definitions": [{"name": "Y", "expr": "A*x + B"}],
        "compose": "",
        "checkpoints": [
          {"id": "yh", "role": "homogeneous_solution", "relation": "combination",
           "equals": "C*exp(-a*x)", "expr": "C*exp(-a*x)", "label_en": "y_h", "label_km": "..."},
          {"id": "A_v", "role": "coefficient", "relation": "solve", "of": "A",
           "equals": "diff(Y, x) + a*Y = a*p*x + a*q + p", "expr": "p", "label_en": "A", "label_km": "A"},
          ...
        ],
        "model": "gemini-3.5-flash", "generated_at": "2026-10-02"
      }
    ]
  }
}
```

- **definitions**: named helpers, never graded (u, v; a trial solution `Y`). For a topic whose given
  is `y`, `compose` must rebuild y from them.
- **checkpoints**, in the order a student writes them. Each `relation` says how SymPy computes the value:

| relation | fields | value |
|---|---|---|
| `derivative` | `of` | d/dx of `of` |
| `outer_derivative` | `outer` (in `t`), `at` | outer′(t) at t = `at` (chain rule) |
| `combination` | `equals` | the expression |
| `substitute` | `of`, `at` | `of` at x = `at` |
| `solve` | `equals` (`;`-separated equations), `of` (an unknown from `SYMBOLS`) | that unknown, all unknowns solved together; an equation containing x must hold for every x (coefficients matched) |

  A topic needing another kind (an antiderivative, a limit, a cross product) adds it with
  `blueprints.register(name, handler)`; `handler(cp, env, x, symbols)` returns the SymPy value.
- **methods**: alternative valid solution paths, standard first. The grader scores the work against
  each and keeps the best.
- At grading time (`resolve`), a step that is 0 or coincides with the givens / final answer / an
  earlier step *on this instance* is dropped (it can't be graded by value), and a step whose value
  still has arbitrary constants is flagged `free_constants`, so `A e^{2x} + B e^{3x}` matches
  `C1 e^{2x} + C2 e^{3x}` (`grading._equivalent_renamed`).

---

## 5. Status

| topic | registry | curated folded in | blueprints | notes |
|---|---|---|---|---|
| derivatives | 74 structures | 54 → removed | 74/74, 128 methods | reference implementation; strict "every step shown" policy |
| differential_equations | 23 structures | 30 → removed | 23/23 (standard methods; one by gemini-2.5-flash after 3.5-flash kept timing out) | pilot; role-verified spec; default policy |
| limit | 162 structures | removed (PR #26) | 162 *unvalidated* LaTeX-string blueprints (`backend/data/limit_blueprints.json`, the "AI experinet" commit) | **re-do in this format**: relations + SymPy gate (`limit` relation) |
| integral | 168 structures | mapped | none | questions not yet tagged with `template_id`; needs `antiderivative` / bounds relations |
| vectors_space | none (7 samplers) | 27 curated | none | needs named givens (A, B, C) and vector relations |
| conics | none (11 asks) | 29 curated | none | |
| continuity | none (2 samplers) | 24 curated | none | needs `limit` (one-sided) relations |
| probability | 6 scenarios (already templates) | 42 counting | none | multi-part: one plan per part |
| complex | 9 question types | 159 curated, most not replayable | none | locus / equations / trig form need solvers first |
