# Skill progress, the profile bar, and practice suggestions

How the app decides *how good a student is* and *what they should practise next*.
Both answers are computed deterministically from stored attempts — no LLM is
involved, for the same reason it isn't involved in grading.

## What gets measured

A **skill** is the finest grain of exercise a student experiences as "a kind of
problem": not a topic (*limits*) and not one question, but the technique in
between — `sin(x)/x` standard limits, integration by parts, the cross product,
second-order homogeneous ODEs. That's the level advice has to speak at to be
actionable, so it's the level the tracker measures at.

`engine/core/skills.py` holds the taxonomy: **77 leaf skills across 11 topics**,
enumerated from the very registries the generators sample from
(`LIMIT_TECHNIQUES`, the integral variant tables, the probability scenario
catalog, and each curated pool's own discriminator field — `kind`, `op`, `ask`,
`order`, `unknown`). Deriving the catalog instead of hand-listing it is what
keeps it from drifting the moment someone adds a technique.

Key format is `topic/question_type` or `topic/question_type:variant` — the same
`question_type:variant` encoding the practice page's type dropdown already uses,
so a skill key round-trips straight into a "practise this" link.

`skill_key_for(topic, question_type, params)` is the inverse: it recovers the
key from a stored `Question`, including ones answered long before this feature
existed, because every generator already records its discriminator in `params`.
Topics whose only axis of variety *is* the question type (complex numbers,
function studies, past-exam questions) contribute one skill per question type
and no variant.

## The hidden tracker

`SkillState` (one row per user × kind × key) is the per-student tracker behind
every bar. Two kinds:

| kind | key | fed by |
|---|---|---|
| `exercise` | a leaf skill key | every graded attempt |
| `formula` | a formula tag | the step-checker's `formula_breakdown` |

The formula axis is finer than the exercise axis: it tracks individual steps
inside otherwise-working solutions (the quotient rule, the conjugate trick), so
a suggestion can say *which step* is being skipped.

**False-miss rule.** A checkpoint the student reached is evidence they can do
that step. A checkpoint they *missed* only counts against them when the final
answer was also wrong — the step-check runs on correct attempts too, and a
correct answer found by a valid alternative route legitimately skips the
standard path's checkpoints. This is the same rule `get_stats`' `by_formula`
uses.

## The formula (`engine/core/mastery.py`)

Each skill carries two independent numbers:

* **rate `r`** — a recency-weighted success rate. Each attempt contributes a
  quality score `s ∈ [0,1]` into an EMA with decay `LAMBDA = 0.94` (an effective
  window of ~17 attempts), so a student who *used* to fail a technique and now
  nails it reads as strong within a handful of exercises.
* **evidence `n_eff`** — how much we actually know. Unbounded (unlike the EMA
  weights), so a skill drilled 100 times is more certain than one drilled 10,
  and decayed by `exp(-days / TAU_DAYS)` with `TAU_DAYS = 90` so an untouched
  skill quietly loses confidence — the model's version of forgetting.

From those two:

```
ability     p    = (r·n_eff + PRIOR_P0·PRIOR_STRENGTH) / (n_eff + PRIOR_STRENGTH)
confidence  conf = n_eff / (n_eff + CONF_K)
level            = 100 · p · conf
```

with `PRIOR_P0 = 0.25`, `PRIOR_STRENGTH = 1.5`, `CONF_K = 3.0`.

`p` is the recency-weighted rate shrunk toward a **pessimistic** prior (an
unproven skill is assumed weak, not average). Multiplying by `conf` is what
makes the bar fill only once the student has *shown* it repeatedly: three lucky
correct answers cannot fill the bar, and the bar approaches — but never reaches
— 100, so there is always headroom.

Roughly, on a single skill answered correctly every time:

| attempts | 1 | 3 | 5 | 10 | 20 | 30 | 60 |
|---|---|---|---|---|---|---|---|
| level | 14 | 38 | 52 | 69 | 82 | 88 | 94 |

### Why an attempt isn't just 1 or 0

`attempt_score` folds in three things the grader already knows:

* **partial credit** — a wrong answer whose checkpoints were mostly right beats
  a blank page, capped at `WRONG_CAP = 0.6` so a wrong answer never scores like
  a right one.
* **difficulty** — an easy exercise answered correctly can't alone prove mastery
  (capped at 0.85), while failing an easy one is the strongest negative signal
  there is (×0.7) and failing a hard one is forgiven (×1.3).
* **hints** — `HINT_PENALTY = 0.06` per hint revealed.

Partial credit comes from the step-check's checkpoints, *not* the points rubric,
even though the rubric is finer: the rubric isn't persisted on the attempt, and
the tracker has to be exactly replayable from stored attempts (see below).

## Rolling up

`mastery.aggregate` answers two different questions from the same
`Σ(ability × confidence)`:

* **`score`** — averaged over the skills *with evidence*: "how good are you at
  what you've practised". This is the headline bar, per topic and overall.
* **`syllabus_score`** — the same total spread over *every* skill in the group,
  so untouched material counts as zero: "how much of the course do you have".

`coverage` (= `Σconf / total`) is what separates the two, and `mastery` is the
score with the evidence discount removed. Reporting all four means the UI never
has to imply that "80%" means something it doesn't — the profile shows `score`
as the big number and `coverage` right beside it as "syllabus proven".

Past exams are tracked but excluded from the roll-up
(`skills.NON_PRACTICE_TOPICS`): an exam replay is evidence, but "practise more
2018 question 3" isn't a technique.

## Suggestions (`engine/core/coaching.py`)

Rule-based and deterministic — the same numbers always produce the same advice,
and every suggestion points at the evidence that produced it. Ranked by
priority, capped per kind, one suggestion per skill:

| kind | fires when | priority |
|---|---|---|
| `weak_skill` | evidence ≥ 2.5, ability < 0.60 **and** rate < 0.75 | 25 + gap·conf (+15 contrast, +5 detail) |
| `weak_formula` | a formula's ability < 0.55 with evidence ≥ 1.5 | 12 + gap·conf |
| `rusty_skill` | was ≥ 0.60 ability, idle ≥ 21 days | 8 + days/4 (max 28) |
| `unproven_skill` | right rate, confidence < 0.45 | 15 + rate·2 |
| `new_skill` | untouched, in a topic already in play | 14 − difficulty |
| `new_topic` | every started topic ≥ 60 | 10 |
| `first_steps` | no evidence at all | 50 |

The `rate < 0.75` condition on `weak_skill` matters: without it a skill answered
right twice reads as "weak" purely because two attempts aren't enough to lift it
off the pessimistic prior, and the student would be told to work on something
they have never once missed. That case becomes `unproven_skill` — "keep going"
— instead.

**Contrast** is the highest-value part. When a skill sits `CONTRAST_GAP = 18`
points or more below its own topic, the suggestion says so:

> **Work on Standard limit sin(x)/x**
> 1 of 6 right — mastery estimate 43%.
> *Your Limits score is 52, but this technique sits at 26.*
> The step you skip most often: Quadrant adjustment.

That gap is the whole reason a student can't see the problem themselves.

## Backfill and versioning

`mastery.TRACKER_VERSION` stamps every row. `services._ensure_skill_states`
rebuilds a student's trackers when they have attempts but no rows (they
practised before this shipped) or when any row predates the current rules — so
tuning the constants needs no data migration, and reads self-heal.

Because every input (`correct`, difficulty, `step_check`, `hints_used`,
timestamps) is persisted on the attempt, `rebuild_skill_states` reproduces
exactly what live recording wrote. That's an invariant worth keeping: it's what
makes the scoring auditable.

## API

| Endpoint | Returns |
|---|---|
| `GET /profile` | level, per-topic progress, every leaf skill, formula weak spots, ranked suggestions, 14-day activity |
| `POST /profile/rebuild` | forces a replay (normally unnecessary — reads self-heal) |
| `GET /skills` | the taxonomy itself, independent of any student |

## Web

`/profile` renders the headline bar, the suggestion cards, a collapsible
per-topic skill breakdown, and the formula weak-spot table. Every "Practise
this" button links to `/practice?skill=<key>`, which resolves the skill from
`GET /skills` and forces the generator to that exact exercise type — the same
mechanism as the older `?formula=<id>` flow, one level coarser.

## Forcing a variant

Making every skill practisable meant teaching the curated-pool generators to
filter on their own discriminator: `continuity` (`check_at_point` /
`find_parameter`), `derivatives` (`order_1` / `order_2`),
`differential_equations` (`kind`), `vectors_space` (`op`), `conics` (`ask`) and
probability's `counting` (combination / permutation / factorial / mixed) all now
accept `variant`. Unknown variants are ignored rather than fatal, so a stale
practice link still yields a question.

68 of the 77 skills are directly forceable; the rest are curated-only limit
techniques with no procedural sampler, which fall back to a random question of
the right topic.
