# Project documentation index

## Reference docs (how it works)

| Doc | Covers |
|---|---|
| `pipeline.md` | End-to-end flow: generation → SymPy solving → OCR/boxes → grading → step-checking → explanations/caching → canvas feedback → history/stats/admin; the data model; **math notation & rendering (plain text / LaTeX / KaTeX)** |
| `canvas.md` | Canvas internals: strokes model, layered rendering (bg/ink/display), infinite-paper growth, zoom/pan/pinch, export map, OCR box integration, review-mode re-draw |
| `step-checking.md` | Line-by-line checking design: checkpoint matching vs carry-over, the given-restatement fix, tiered trust (grey = "could not verify"), **multiple solution paths + hybrid equivalence** (simplify → fu → numeric sampling), the wrong-answer flow |
| `generator-variants.md` | Reference table of every template/variant, its formula tags, and difficulty pools |
| `exam-data.md` | The limits exam bank + integral extraction sets, verify scripts, container-mount caveats, the formula catalog files |
| `sounds-and-streaks.md` | Web Audio grade sounds, rising-pitch combo, streak persistence, when each sound fires |
| `topic-probability.md` | Probability topic: structure-first solvers + user-owned Khmer scenario catalog (built, from real exam problems) |

## How-to docs (extending)

| Doc | Covers |
|---|---|
| `adding-question-types.md` | The recipe: formula catalog → solver → grader → generator template → web dropdown → verification checklist (with gotchas) |

## Planned feature docs (not yet built)

| Doc | Covers |
|---|---|
| `adaptive-formula-practice.md` | Record missed formulas → teach via forced-variant questions → re-measure |
| `learning-support-formula-sheet-hints.md` | Student-facing formula sheet + progressive hint ladder |

## Still undocumented (candidates)

- Subscription/plan roadmap (`User.plan` is in the DB, gating points designed).
- Deployment & env matrix (partially in CLAUDE.md).
- Exam-bank offline pipeline end-to-end (data → verify → playable).
- LLM prompt contracts (narrate / check_work / vision / propose_problem).