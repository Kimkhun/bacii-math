"""Skill-mastery math: how one graded attempt moves a student's estimate of a
skill, and how leaf-skill estimates roll up into the 0-100 progress bar.

Pure functions over plain numbers — no DB, no SymPy, no framework. ``services``
owns the ``SkillState`` rows; this module owns the formula, so the numbers can
be reasoned about (and re-derived by ``rebuild_skill_states``) in one place.

The model
---------
Every leaf skill (see ``engine.core.skills``) carries two independent numbers:

* **rate** ``r`` — a recency-weighted success rate. Each attempt contributes a
  quality score ``s in [0, 1]`` into an exponential moving average with decay
  ``LAMBDA``; older attempts fade with an effective window of ``1/(1-LAMBDA)``
  attempts, so a student who *used* to fail a technique and now nails it reads
  as strong within a handful of exercises.
* **evidence** ``n_eff`` — how much we actually know. Unbounded (unlike the EMA
  weights), so a skill drilled 100 times is more certain than one drilled 10,
  and time-decayed by ``TAU_DAYS`` so an untouched skill quietly loses
  confidence — the model's version of forgetting.

From those two:

    ability   p    = (r * n_eff + PRIOR_P0 * PRIOR_STRENGTH) / (n_eff + PRIOR_STRENGTH)
    certainty conf = n_eff / (n_eff + CONF_K)
    level          = 100 * p * conf

``p`` is the recency-weighted rate shrunk toward a pessimistic prior (an
unproven skill is assumed weak, not average), and multiplying by ``conf`` is
what makes the bar "lean towards fullness" only once the student has *shown*
it repeatedly: three lucky correct answers cannot fill the bar, and the bar
approaches — but never reaches — 100, so there is always headroom.

Why an attempt is not simply 1 or 0
-----------------------------------
``attempt_score`` folds in three things the grader already knows:

* **partial credit** — a wrong final answer whose rubric/checkpoints were
  mostly right is worth more than a blank one, capped at ``WRONG_CAP`` so a
  wrong answer can never score like a right one.
* **difficulty** — an easy exercise answered correctly can't alone prove
  mastery (capped at ``CORRECT_WEIGHT['easy']``), while failing an easy one is
  the strongest negative signal there is and failing a hard one is forgiven.
* **hints** — each hint used shaves ``HINT_PENALTY`` off the score.

Rolling up
----------
A topic's score is the mean of ``p_i * conf_i`` over *every* leaf skill the
topic has, including ones never attempted (which contribute 0). That is
deliberate: "80% of the limits topic" should mean the student is good across
limits, not good at the one technique they keep repeating. The same mean
factors exactly into ``mastery * coverage``, which is what the UI shows when a
student needs to know *which* half is missing.
"""
import math

# --- attempt scoring -------------------------------------------------------

#: A wrong final answer can never score above this, however much work was right.
WRONG_CAP = 0.6
#: Multiplier on a *correct* attempt's score. Easy items cap below 1.0 so that
#: grinding easy exercises plateaus instead of reading as mastery.
CORRECT_WEIGHT = {"easy": 0.85, "medium": 1.0, "hard": 1.0}
#: Multiplier on an *incorrect* attempt's partial credit. Above 1.0 forgives a
#: hard miss, below 1.0 punishes an easy one.
WRONG_WEIGHT = {"easy": 0.7, "medium": 1.0, "hard": 1.3}
#: Subtracted per hint revealed before answering.
HINT_PENALTY = 0.06

# --- estimator -------------------------------------------------------------

#: Per-attempt EMA decay for the success rate (effective window ~17 attempts).
LAMBDA = 0.94
#: Idle-time constant, in days, for the evidence decay (exp(-days / TAU_DAYS)).
TAU_DAYS = 90.0
#: Strength and mean of the pessimistic prior an unproven skill is shrunk to.
PRIOR_STRENGTH = 1.5
PRIOR_P0 = 0.25
#: Evidence needed for the certainty factor to reach 50%.
CONF_K = 3.0

#: Bumped whenever any constant or rule above changes, so stored SkillState
#: rows recorded under older rules are transparently replayed from the
#: attempt history instead of being silently mixed with new ones.
TRACKER_VERSION = 1

#: level -> label, ascending. The first band whose ceiling the level is under.
BANDS = (
    (20, "Beginner"),
    (40, "Developing"),
    (55, "Competent"),
    (70, "Proficient"),
    (85, "Advanced"),
    (101, "Mastered"),
)


def attempt_score(correct, difficulty="medium", partial=None, hints_used=0):
    """Quality of one graded attempt, in [0, 1].

    ``partial`` is the fraction of the solution the student did reach (rubric
    points earned / possible, or checkpoints reached / total) and is only
    consulted for an incorrect attempt.
    """
    if correct:
        score = CORRECT_WEIGHT.get(difficulty, 1.0)
    else:
        got = 0.0 if partial is None else max(0.0, min(1.0, float(partial)))
        score = min(WRONG_CAP, got) * WRONG_WEIGHT.get(difficulty, 1.0)
    score -= HINT_PENALTY * max(0, int(hints_used or 0))
    return max(0.0, min(1.0, score))


def partial_from_grade(step_check=None):
    """Fraction of the solution the student actually reached, from the
    step-check's formula checkpoints. ``None`` when there is nothing readable
    (typed answer, or unreadable handwriting) — no credit, but no evidence of
    a blank page either.

    The points rubric would be a finer signal, but it isn't persisted on the
    attempt, and the tracker has to be exactly replayable from stored attempts
    (``services.rebuild_skill_states``) — a live score and a rebuilt one must
    agree, so only stored signals are used.
    """
    breakdown = (step_check or {}).get("formula_breakdown") or []
    if breakdown:
        return sum(1 for b in breakdown if b.get("reached")) / len(breakdown)
    return None


# --- state updates ---------------------------------------------------------

def time_decay(days):
    """Evidence retained after ``days`` of not practising a skill."""
    if not days or days <= 0:
        return 1.0
    return math.exp(-float(days) / TAU_DAYS)


def apply_attempt(w_total, w_correct, evidence, score, days_since_last=0.0):
    """Fold one attempt's ``score`` into a skill's stored state.

    Idle time is charged against the *evidence* only: the success rate is a
    ratio, so forgetting shows up as lower certainty (which pulls ``ability``
    back toward the prior), not as a rate that mysteriously drifts.
    """
    decay = time_decay(days_since_last)
    return (
        LAMBDA * w_total + 1.0,
        LAMBDA * w_correct + float(score),
        evidence * decay + 1.0,
    )


def estimate(w_total, w_correct, evidence, days_since_last=0.0):
    """Current ``{rate, evidence, ability, confidence, level}`` for one skill."""
    n_eff = max(0.0, float(evidence)) * time_decay(days_since_last)
    rate = (w_correct / w_total) if w_total > 0 else 0.0
    ability = (rate * n_eff + PRIOR_P0 * PRIOR_STRENGTH) / (n_eff + PRIOR_STRENGTH)
    confidence = n_eff / (n_eff + CONF_K)
    return {
        "rate": round(rate, 4),
        "evidence": round(n_eff, 3),
        "ability": round(ability, 4),
        "confidence": round(confidence, 4),
        "level": round(100.0 * ability * confidence, 1) if n_eff > 0 else 0.0,
    }


def band(level):
    for ceiling, name in BANDS:
        if level < ceiling:
            return name
    return BANDS[-1][1]


def status(est):
    """Coarse per-skill state used for sorting and colouring the UI."""
    if est["evidence"] <= 0:
        return "untouched"
    if est["confidence"] < 0.4:
        return "learning"
    if est["ability"] < 0.55:
        return "shaky"
    if est["level"] >= 75:
        return "mastered"
    return "solid"


# --- roll-up ---------------------------------------------------------------

def aggregate(estimates, total_skills=None):
    """Roll leaf estimates up into one group's numbers.

    Pass every skill in the group (practised or not) plus how many the catalog
    holds. Two different questions get two different answers, both built from
    the same ``sum(ability * confidence)``:

    * ``score`` — *how good are you at what you've practised*, averaged over the
      skills with evidence. This is the headline bar: a student who has drilled
      five limit techniques well reads as strong at limits, and one who has only
      ever repeated a single easy exercise does not (their confidence is low).
    * ``syllabus_score`` — the same total spread over *every* skill in the
      group, so untouched material counts as zero. This is the honest
      "how much of the course do you have" number.

    ``coverage`` is the fraction of the group the student has actually proven,
    and is what separates the two scores; ``mastery`` is the score with the
    evidence discount removed (pure ability). Reporting all four means the UI
    never has to imply that "80%" means something it doesn't.
    """
    total = total_skills if total_skills is not None else len(estimates)
    practised = [e for e in estimates if e["evidence"] > 0]
    conf_sum = sum(e["confidence"] for e in practised)
    effective = sum(e["ability"] * e["confidence"] for e in practised)
    score = round(100.0 * effective / len(practised), 1) if practised else 0.0
    return {
        "score": score,
        "syllabus_score": round(100.0 * effective / total, 1) if total > 0 else 0.0,
        "mastery": round(effective / conf_sum, 4) if conf_sum > 0 else 0.0,
        "coverage": round(min(1.0, conf_sum / total), 4) if total > 0 else 0.0,
        "practised": len(practised),
        "total": total,
        "band": band(score),
    }
