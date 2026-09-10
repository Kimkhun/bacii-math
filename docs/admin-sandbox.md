# Admin sandbox

The **Sandbox** tab on `/admin` (admin-only, same gate as Templates —
`User.is_admin` via `get_current_admin_user`) lets you run a topic's solver
and grader directly against hand-entered params, without generating a real
`Question` or persisting an `Attempt`. Use it to:

- Check that a template/formula produces a correct, well-formed solution for
  specific numbers (including edge cases the random generator rarely hits).
- Reproduce a student's bug report exactly — enter the same `z`/`a`/`b` (or
  whatever the topic uses) and paste in the same handwritten lines.
- Try a pen-drawn or photographed solution through the real OCR pipeline
  before deciding whether the grader's reaction to it is correct.

It's backed by three admin-gated endpoints (`backend/routers/problems.py`,
`me_router`): `GET /sandbox/sample`, `POST /sandbox/solve`, `POST
/sandbox/grade` — thin wrappers around `engine.core.dispatch.solve()`,
`engine.core.grading.analyze_work()`, and `engine.core.rubric.score_work()`,
the exact same functions the real grading flow uses. Nothing here is a
simulation of the grading pipeline; it *is* the grading pipeline, run
in isolation.

## 1. Pick a template

Choose a **topic** and **question type** from the dropdowns (the same
registry that drives Templates/Overview — `engine/core/shared.py`'s
`QUESTION_TYPES_BY_TOPIC`), then a difficulty, and click **Load sample
params**. This generates one real problem for that template and pre-fills
the params editor with its actual `params` dict — there's no separate
schema to consult, so a live sample is the fastest way to see the exact
keys a topic expects (e.g. `complex`/`modulus` → `{a, b}`; `limit`/`limit` →
`{expr, var, point, formula_name, ...}`; `vectors_space` → `{op, A, B, ...}`
depending on `op`).

## 2. Edit params

Each param renders as one row (`name` + a text field). You can:

- **Edit a value directly** — type over it, or click into the field and use
  the **keypad** on the right (see below).
- **Add a field** the sample didn't include, via the "param name" box at the
  bottom of the card — useful when testing a param combination the
  generator itself never produces.
- **Remove a field** with the `×` button next to it.

Values are sent to the backend as follows (`services._sandbox_coerce`):

- A field that parses as JSON (a plain number, `[1,2,3]`, `{"x0":0,"y0":3}`)
  is sent as that JSON value — this is how you edit vector/list params
  (`vectors_space`) or initial-condition dicts (`differential_equations`).
- Anything else is sent as text and parsed the same way the grader parses
  handwritten answers (`sqrt(2)`, `pi/4`, `x**2 - 1`, `3/4`, ...) — this
  covers `expr`-style params.
- A handful of known name/enum keys (`var`, `operation`, `op`,
  `formula_name`, `kind`, `unknown`, `fn_name`, `ask`, `variant`,
  `structure`, `technique`, `wanted`, `want`, `id`, ...) are never
  parsed as math — they stay literal strings, since e.g. `var = "x"` must
  stay the string `"x"`, not become the SymPy symbol.

If a param is missing or malformed, **Solve** will fail with the raw
Python exception message from `solve()` — that's intentional; it's telling
you exactly what the solver choked on.

### The keypad

Click into any param field or the "Test grading" lines box, then use the
keypad panel to insert tokens at the cursor: trigonometric/log/sqrt/`|x|`/
`e^x` functions, `π`, `e`, `i`, `∞`, parentheses, `^`/`x²` (powers), `/`
(fractions — SymPy reads `a/b` as a fraction), `,` (for vector components),
`x`, `=`, and a numeric pad with `⌫`/arrow keys to move the caret. Typing
directly on the keyboard works exactly the same — the keypad is a
convenience, not the only way in.

## 3. Solve

Click **Solve** to run `solve(topic, question_type, params)` and see:

- The final **answer** (both exact form and its rendered LaTeX).
- Every **checkpoint** the step-checker will look for, in order, with its
  expected value and which formula it exercises.
- The full **step-by-step explanation** the same as a student would see.
- **Params actually used**, after parsing — expand this to confirm your
  text was interpreted the way you intended (e.g. that `pi/3` really
  became the SymPy value `π/3`, not a literal string).

## 4. Test grading

This section checks how the grader reacts to a specific piece of written
work, using the params currently in the editor.

**Get the text three ways:**

- **Type it** directly into the lines box, one asserted fact per line —
  exactly how a student's OCR'd lines would look.
- **Draw it** with the Pen tool on the small canvas (Eraser/Select tools,
  pen width, Undo/Redo/Clear all work the same as the practice canvas).
- **Paste or upload a photo** of a written solution — paste an image
  anywhere on the page (Ctrl/Cmd+V) or use **Upload image**; it's placed
  onto the canvas as a movable/resizable image.

Once you've drawn/pasted something, click **Recognize handwriting → fill
lines below** to run it through the real OCR pipeline (`/vision/detect`,
Gemini vision by default) and fill the lines box with the recognized text —
review/edit it before grading, same as a student could correct a
misread line.

Click **Grade** to run:

- **Line-by-line** (`analyze_work`) — each line marked `✓` correct, `✗`
  wrong (with the expected value), or `–` skipped, with the skip reason
  (`given` = recognized as a restatement, `unparsed`, `label`, `identity`,
  `conclusion`).
- **Rubric score** (`score_work`) — the points breakdown per checkpoint.
  A row without its own matched line but marked *"implied by a later
  line"* means the student's own line skipped ahead and a later checkpoint
  in the same item was actually verified — those points are still
  awarded, since the intermediate value must have been computed to reach
  it (see `engine/core/rubric.py`'s module docstring).

## Tips

- **Reproducing a bug report**: load a sample close to the real question,
  then overwrite the params to match the screenshot's numbers exactly
  (`a`, `b`, `expr`, whatever the topic uses), and either retype the
  student's lines or draw/paste them to go through OCR too if you suspect
  the bug is OCR-shape-dependent rather than purely a grading-logic bug.
- **A param that "won't parse"**: check whether it's one of the
  literal-string keys above — if so, don't wrap it in quotes or expect
  math parsing; if not, remember SymPy syntax (`**` for powers works too,
  alongside `^`; `I` or `i` for the imaginary unit; `oo` for infinity).
- **Solve fails but the real generator never produces this combination**:
  that can be a real edge case worth a guard in the solver (e.g. a
  division by zero for a degenerate `a=0` some templates never sample) —
  or it can be a genuinely invalid input for that question type. The
  exception message plus this repo's `docs/engine-layout.md` "add a topic"
  recipe should tell you which.
