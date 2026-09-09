"""Turning a student's skill estimates into "practise this next".

``mastery`` says *how good* a student is at each leaf skill; this module says
*what to do about it*. It is deliberately rule-based and deterministic — the
same numbers always produce the same advice, and every suggestion can point at
the evidence that produced it. (No LLM: the same principle as grading. An LLM
may later narrate these suggestions, but it must not invent them.)

The rules, in the order they usually win:

1. **Weak skill** — a technique the student has attempted and keeps getting
   wrong. This is the headline case: "limits are fine overall, but sin(x)/x
   isn't". When the parent topic is much stronger than the skill, the
   suggestion carries that contrast, because that gap is the whole reason the
   student can't see the problem themselves.
2. **Weak formula** — finer than a skill: one step inside otherwise-working
   solutions (the quotient rule, the conjugate trick) that the step-checker
   keeps finding missing. Points at whichever exercise variant drills it.
3. **Rusty skill** — was solid, hasn't been touched in weeks, and the evidence
   has decayed. Cheap to fix and easy to lose.
4. **Unproven skill** — started, answered right, but not enough times for the
   bar to have moved. "Finish what you started" beats "start something new".
5. **Unpractised skill** — a technique in a topic the student is already
   working on but has never tried. Fills the coverage gap that is holding the
   topic's progress bar down.
6. **New topic** — everything currently in play is in good shape; time to open
   the next chapter.
7. **First steps** — a brand-new student, no evidence at all: hand them a few
   easy skills to start on rather than an empty page.
"""

#: Ability below which an attempted skill counts as a weakness.
WEAK_ABILITY = 0.60
#: Ability below which a formula counts as a weakness (stricter: a formula miss
#: can be an alternative-path artefact, so demand a clearer signal).
WEAK_FORMULA_ABILITY = 0.55
#: Minimum evidence before a low score is treated as a real weakness rather
#: than an unlucky first attempt.
MIN_EVIDENCE = 2.5
MIN_FORMULA_EVIDENCE = 1.5
#: Recent success rate below which a skill is actually being got wrong. Without
#: this, a skill answered right twice reads as "weak" purely because two
#: attempts aren't enough to lift it off the pessimistic prior — the student
#: would be told to work on something they have never once missed.
WEAK_RATE = 0.75
#: A skill answered correctly but not yet often enough to count: right rate,
#: not enough evidence. Worth finishing rather than starting something new.
UNPROVEN_CONFIDENCE = 0.45
#: Idle days after which a previously-solid skill is called rusty.
RUSTY_DAYS = 21
#: Ability a skill must once have reached to be worth a "review" nudge.
RUSTY_ABILITY = 0.60
#: How far a skill must sit below its own topic before the gap is worth saying
#: out loud ("you're at 78 in Limits but 31 on this technique").
CONTRAST_GAP = 18.0
#: A topic is "in good shape" — no longer worth suggesting over a new one — at
#: this score.
TOPIC_SATISFIED = 60.0

MAX_PER_KIND = {
    "weak_skill": 3, "weak_formula": 2, "rusty_skill": 2,
    "unproven_skill": 2, "new_skill": 2, "new_topic": 1,
}


def is_weak_skill(s):
    """A skill the student has attempted enough times *and* is getting wrong."""
    return (
        s["practice"]
        and s["evidence"] >= MIN_EVIDENCE
        and s["ability"] < WEAK_ABILITY
        and s["rate"] < WEAK_RATE
    )


def is_weak_formula(f):
    return f["evidence"] >= MIN_FORMULA_EVIDENCE and f["ability"] < WEAK_FORMULA_ABILITY


def _pct(x):
    return int(round(100 * x))


def _weak_skill_suggestions(skills, topics):
    out = []
    for s in skills:
        if not is_weak_skill(s):
            continue
        topic = topics.get(s["topic"]) or {}
        gap = (topic.get("score") or 0.0) - s["level"]
        # Base offset: fixing a known weakness outranks reviewing something
        # already solid or trying something new.
        priority = 25.0 + (WEAK_ABILITY - s["ability"]) * 100.0 * s["confidence"]
        reason = f"{s['correct']} of {s['attempts']} right — mastery estimate {_pct(s['ability'])}%."
        contrast = None
        if gap >= CONTRAST_GAP:
            priority += 15.0
            contrast = (
                f"Your {topic.get('label', s['topic'])} score is {int(round(topic['score']))}, "
                f"but this technique sits at {int(round(s['level']))}."
            )
        # A formula whose name is just the skill's own name adds nothing.
        missed = [m for m in (s.get("weak_formulas") or []) if m["name"] != s["label"]]
        detail = None
        if missed:
            names = ", ".join(m["name"] for m in missed[:2])
            detail = f"The step you skip most often: {names}."
            priority += 5.0
        out.append({
            "kind": "weak_skill",
            "priority": priority,
            "title": f"Work on {s['label']}",
            "reason": reason,
            "contrast": contrast,
            "detail": detail,
            "topic": s["topic"],
            "topic_label": s["topic_label"],
            "skill_key": s["key"],
            "formula": None,
            "level": s["level"],
        })
    return out


def _weak_formula_suggestions(formulas_, skills_by_key):
    out = []
    for f in formulas_:
        if not is_weak_formula(f):
            continue
        if not f.get("skill_key"):
            continue
        skill = skills_by_key.get(f["skill_key"])
        where = f" — it comes up in {skill['label']}." if skill else ""
        out.append({
            "kind": "weak_formula",
            "priority": 12.0 + (WEAK_FORMULA_ABILITY - f["ability"]) * 90.0 * f["confidence"],
            "title": f"Drill the step: {f['name']}",
            "reason": f"You reached this step in only {f['correct']} of {f['attempts']} checked solutions{where}",
            "contrast": None,
            "detail": None,
            "topic": f.get("topic"),
            "topic_label": f.get("topic_label"),
            "skill_key": f["skill_key"],
            "formula": f["formula"],
            "level": f["level"],
        })
    return out


def _rusty_suggestions(skills):
    out = []
    for s in skills:
        if not s["practice"] or s["evidence"] <= 0 or s["days_idle"] < RUSTY_DAYS:
            continue
        if s["ability"] < RUSTY_ABILITY:
            continue  # already covered by the weak-skill rule
        days = int(s["days_idle"])
        out.append({
            "kind": "rusty_skill",
            "priority": 8.0 + min(20.0, days / 4.0),
            "title": f"Review {s['label']}",
            "reason": f"You had this at {_pct(s['ability'])}% but haven't practised it in {days} days.",
            "contrast": None,
            "detail": None,
            "topic": s["topic"],
            "topic_label": s["topic_label"],
            "skill_key": s["key"],
            "formula": None,
            "level": s["level"],
        })
    return out


def _unproven_suggestions(skills):
    """Started and going well, but not yet often enough for the bar to move.
    The honest advice is "finish what you started", and saying so stops a low
    bar from reading as failure."""
    out = []
    for s in skills:
        if not s["practice"] or s["evidence"] <= 0:
            continue
        if s["confidence"] >= UNPROVEN_CONFIDENCE or s["rate"] < WEAK_RATE:
            continue
        out.append({
            "kind": "unproven_skill",
            "priority": 15.0 + s["rate"] * 2.0,
            "title": f"Keep going on {s['label']}",
            "reason": (
                f"{s['correct']} of {s['attempts']} right so far — a few more "
                f"will confirm you've got this one."
            ),
            "contrast": None,
            "detail": None,
            "topic": s["topic"],
            "topic_label": s["topic_label"],
            "skill_key": s["key"],
            "formula": None,
            "level": s["level"],
        })
    return out


def _new_skill_suggestions(skills, topics):
    rank = {"easy": 0, "medium": 1, "hard": 2}
    candidates = [
        s for s in skills
        if s["practice"] and s["evidence"] <= 0 and (topics.get(s["topic"]) or {}).get("engaged")
    ]
    candidates.sort(key=lambda s: (rank.get(s["difficulty"], 1), s["key"]))
    out = []
    for s in candidates:
        topic = topics.get(s["topic"]) or {}
        out.append({
            "kind": "new_skill",
            "priority": 14.0 - rank.get(s["difficulty"], 1) * 2.0,
            "title": f"Try {s['label']}",
            "reason": (
                f"You haven't attempted this one yet — it's part of "
                f"{topic.get('label', s['topic'])}, which you're already working on."
            ),
            "contrast": None,
            "detail": None,
            "topic": s["topic"],
            "topic_label": s["topic_label"],
            "skill_key": s["key"],
            "formula": None,
            "level": 0.0,
        })
    return out


def _new_topic_suggestions(skills, topics):
    # Past-exam replays are tracked but aren't a topic you "finish", so they
    # must not hold back the suggestion to open a new one.
    engaged = [t for t in topics.values() if t.get("engaged") and t.get("practice", True)]
    if not engaged or any(t["score"] < TOPIC_SATISFIED for t in engaged):
        return []
    rank = {"easy": 0, "medium": 1, "hard": 2}
    for s in sorted(skills, key=lambda s: (rank.get(s["difficulty"], 1), s["key"])):
        topic = topics.get(s["topic"]) or {}
        if not s["practice"] or topic.get("engaged"):
            continue
        return [{
            "kind": "new_topic",
            "priority": 10.0,
            "title": f"Start {topic.get('label', s['topic'])}",
            "reason": "Every topic you've started is in good shape — this is the next one to open.",
            "contrast": None,
            "detail": None,
            "topic": s["topic"],
            "topic_label": s["topic_label"],
            "skill_key": s["key"],
            "formula": None,
            "level": 0.0,
        }]
    return []


def _first_steps(skills):
    rank = {"easy": 0, "medium": 1, "hard": 2}
    picks, seen_topics = [], set()
    for s in sorted(skills, key=lambda s: (rank.get(s["difficulty"], 1), s["key"])):
        if not s["practice"] or s["topic"] in seen_topics:
            continue
        seen_topics.add(s["topic"])
        picks.append({
            "kind": "first_steps",
            "priority": 50.0 - len(picks),
            "title": f"Start with {s['label']}",
            "reason": "Answer a few of these and your profile will start filling in.",
            "contrast": None,
            "detail": None,
            "topic": s["topic"],
            "topic_label": s["topic_label"],
            "skill_key": s["key"],
            "formula": None,
            "level": 0.0,
        })
        if len(picks) == 3:
            break
    return picks


def build_suggestions(skills, formula_stats, topics, limit=6):
    """Rank every rule's candidates and return the top ``limit``.

    ``skills`` are per-leaf dicts (see ``services._skill_view``), ``topics`` is
    ``{topic: {label, score, engaged}}``, ``formula_stats`` are the formula-level
    rows with a resolved ``skill_key`` to practise them through.
    """
    if not any(s["evidence"] > 0 for s in skills):
        return _first_steps(skills)[:limit]

    skills_by_key = {s["key"]: s for s in skills}
    candidates = (
        _weak_skill_suggestions(skills, topics)
        + _weak_formula_suggestions(formula_stats, skills_by_key)
        + _rusty_suggestions(skills)
        + _unproven_suggestions(skills)
        + _new_skill_suggestions(skills, topics)
        + _new_topic_suggestions(skills, topics)
    )
    candidates.sort(key=lambda c: -c["priority"])

    chosen, per_kind, used_skills = [], {}, set()
    for c in candidates:
        kind = c["kind"]
        if per_kind.get(kind, 0) >= MAX_PER_KIND.get(kind, 2):
            continue
        # One suggestion per skill: a weak skill and a weak formula inside it
        # are the same advice said twice.
        if c["skill_key"] in used_skills:
            continue
        per_kind[kind] = per_kind.get(kind, 0) + 1
        used_skills.add(c["skill_key"])
        chosen.append(c)
        if len(chosen) >= limit:
            break
    return chosen
