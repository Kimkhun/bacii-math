# ADR 001: SymPy as the Sole Source of Mathematical Truth

## Context

BACII Math Practice grades handwritten answers to Cambodian BAC II exam problems and must tell a
student, instantly, whether their answer — and each intermediate step — is mathematically correct.
"Correct" here can't mean "matches this exact string": a modulus, a limit, or an antiderivative has
many equivalent written forms (`sqrt(2)` vs `1.41421...`, `(x-2)(x+2)` vs `x^2-4`, `F(x)+C` for any
constant `C`). At the same time, the product also owes the student a friendly, readable explanation
of *why* the answer is what it is — a different kind of task, closer to writing than to computing.

## Decision

Every answer and every grading verdict is computed by SymPy — a symbolic computer algebra system —
never by an LLM. Each topic (complex numbers, limits, integrals, …) has its own `solver.py` that
builds the exact answer and a checkpoint list of intermediate values with SymPy; the shared grading
core (`engine/core/grading.py`) parses the student's answer with SymPy's expression parser and
judges it against that exact value — first by symbolic simplification, then, only as a safety net,
by numeric sampling at several non-special points. LLMs are confined to two roles: narrating
SymPy's steps in plain language, and, in one generation mode, *proposing* candidate problem
parameters that SymPy still independently recomputes and validates before they're ever shown to a
student.

## Consequences

- Grading is deterministic and reproducible: the same submitted answer always gets the same
  verdict, regardless of which LLM is available that day, what it was asked, or how it was feeling.
- The product can credibly claim "mathematically exact" grading to students, teachers, and
  examiners — the verdict is not an LLM's opinion.
- Accepting many equivalent correct forms (rather than one canonical string) is possible precisely
  because equivalence is checked algebraically, not textually.
- Cost: each new topic/question type requires a hand-written SymPy solver and, sometimes, custom
  judging logic — this is slower to build than "ask an LLM to grade it."
- Some grading decisions still rely on heuristics layered on top of SymPy (a numeric tolerance, a
  handful of sample points standing in for a full equivalence proof) rather than pure symbolic
  proof — these are edge cases, but they exist.
- "Show that" / proof-style sub-questions have no single checkable value and are left as
  self-check-only, not auto-graded.

## Alternatives considered

- **Grade with an LLM directly** ("ask Gemini/GPT if this is correct"): no code path does this
  anywhere in the engine — implicitly rejected, presumably for the trust and reproducibility
  reasons above.
- **Exact string/regex matching** against one canonical answer: evidently judged insufficient — the
  grading core's multi-stage equivalence ladder (`simplify`, then `simplify(fu=True)`, then numeric
  sampling) only exists because equivalent expressions come in many written forms.
- **Human teacher grading**: doesn't scale to instant per-attempt feedback.

## TODO(founder)

- Was an LLM-graded approach ever prototyped and rejected, or was "SymPy only" the decision from
  day one? What specifically drove it?
- Is "provably exact grading" a requirement from an external party (MoEYS, a school partner, an
  examiner), or purely an internal trust/engineering decision?
- What's the plan for topics that are inherently proof/argument-based rather than value-based —
  will they ever be auto-graded, or do they stay self-check permanently?
- Are there known cases where the SymPy verdict has disagreed with what a human teacher would
  accept (e.g., valid alternate methods, partial credit)? How is that risk tracked today?
