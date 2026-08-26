import hashlib
import random
import uuid
import zlib

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sympy import latex

import cache
from engine import explainer, formulas, generator, grader, llm, scenarios, solver, structures
from engine.generator.integrals import (
    _INDEFINITE_VARIANT_BY_DIFFICULTY,
    _INTEGRAL_VARIANT_BY_DIFFICULTY,
)
from engine.generator.limits import generate_limit_for_technique
from models import Attempt, Explanation, Question, Step, StudySession, User
from schemas import GenerateRequest, SaveProgressRequest

WORK_UNREADABLE_MSG = (
    "Couldn't read your written steps clearly. Try writing larger and more spaced out, "
    "or type your work instead."
)


def _work_usable(step_check: dict | None) -> bool:
    return bool(step_check) and any(r.get("checked") for r in step_check.get("line_results", []))


async def create_question(db: AsyncSession, req: GenerateRequest) -> dict:
    problem = await generator.generate(
        req.topic, req.difficulty, req.seed, req.question_type, req.generation_mode, variant=req.variant
    )
    return await persist_problem(db, problem)


async def persist_problem(db: AsyncSession, problem: dict) -> dict:
    """Store a generated problem + its SymPy solution as a new Question row."""
    solution = solver.solve(problem["topic"], problem["question_type"], problem["params"])

    formula_tags = solution.get("formula_tags") or []
    if not formula_tags or not solution.get("checkpoints"):
        raise RuntimeError(
            f"solver for {problem['topic']}/{problem['question_type']} did not emit formula_tags/checkpoints"
        )
    formula_difficulty = formulas.formula_difficulty(formula_tags)

    question = Question(
        topic=problem["topic"],
        question_type=problem["question_type"],
        difficulty=problem["difficulty"],
        spec=problem["params"],
        prompt=problem["prompt"],
        prompt_latex=problem.get("prompt_latex"),
        z_display=problem["z_display"],
        expected_answer=str(solution["answer_exact"]),
        expected_decimal=solution["answer_decimal"] if isinstance(solution["answer_decimal"], float) else None,
        source=problem["source"],
        formula_tags=formula_tags,
    )
    db.add(question)
    await db.flush()

    for i, s in enumerate(solution["steps"], 1):
        db.add(Step(
            question_id=question.id, step_order=i, title=s["title"], detail=s["detail"],
            formula=s.get("formula"),
        ))

    await db.commit()
    return {
        "id": question.id,
        "topic": question.topic,
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "a": problem["params"].get("a"),
        "b": problem["params"].get("b"),
        "params": problem["params"],
        "prompt": question.prompt,
        "prompt_latex": question.prompt_latex,
        "z_display": question.z_display,
        "source": question.source,
        "formula_tags": formula_tags,
        "formula_difficulty": formula_difficulty,
    }


async def recreate_question(db: AsyncSession, user, question_id) -> dict:
    """'Do the same exercise again': build a fresh copy of an existing question
    (same topic/type/difficulty/spec/prompt), re-solved by SymPy, so a student
    can redo it with a clean attempt history."""
    existing = await db.get(Question, question_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    problem = {
        "topic": existing.topic,
        "question_type": existing.question_type,
        "difficulty": existing.difficulty,
        "params": existing.spec,
        "prompt": existing.prompt,
        "prompt_latex": existing.prompt_latex,
        "z_display": existing.z_display,
        "source": "template",
    }
    return await persist_problem(db, problem)


def _steps_text(question: Question) -> str:
    solution = solver.solve(question.topic, question.question_type, question.spec)
    return explainer.build_text(question.topic, question.question_type, question.spec, solution)


async def _build_explanation(db, user, question, attempt_id, trigger, use_ai, steps_text=None, allow_gemini=None, context=None) -> dict:
    steps_text = steps_text or _steps_text(question)
    content = steps_text
    provider = "deterministic"
    intervened = False

    if use_ai:
        spec_key = ":".join(f"{k}={v}" for k, v in sorted(question.spec.items()))
        # Version the cache with the deterministic steps' content: if a solver
        # change alters the steps, stale narrations must never be served for
        # questions with the same params.
        steps_digest = hashlib.sha1(steps_text.encode("utf-8")).hexdigest()[:12]
        key = f"explain:{question.topic}:{question.question_type}:{spec_key}:{steps_digest}"
        cached = await cache.get_explanation(key)
        if cached:
            content, provider, intervened = cached, "gemini", True
        else:
            if allow_gemini is None:
                allow_gemini = await cache.allow_gemini(str(user.id))
            text, got_provider = await llm.narrate(steps_text, allow_gemini=allow_gemini, context=context)
            if text:
                content, provider, intervened = text, got_provider, True
                if got_provider == "gemini":
                    await cache.set_explanation(key, text)

    db.add(Explanation(
        attempt_id=attempt_id,
        question_id=question.id,
        provider=provider,
        content=content,
        intervened=intervened,
        trigger=trigger,
    ))
    return {"content": content, "provider": provider, "intervened": intervened, "trigger": trigger}


async def grade_question(db, user, question_id, user_answer, work_text=None, lines_boxes=None, part=None, hints_used=0) -> dict:
    question = await db.get(Question, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")

    spec = question.spec or {}
    is_multi = isinstance(spec.get("parts"), list) and len(spec["parts"]) > 1

    if is_multi and part:
        # Progressive flow: grade only the requested sub-part (A, then B, ...).
        labels = [str(p.get("label")) for p in spec["parts"]]
        if part not in labels:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown part: {part}")
        result = grader.grade_part(question.topic, question.question_type, spec, part, user_answer)
    elif is_multi:
        labels = [str(p.get("label")) for p in spec["parts"]]
        submissions = grader.parse_multi_answers(user_answer, labels)
        if work_text:
            segments = grader.split_work_by_part(work_text.split("\n"), labels)
            for label in labels:
                if label not in submissions:
                    value = grader.last_value_of_lines(segments[label])
                    if value:
                        submissions[label] = value
        result = grader.grade_multi(question.topic, question.question_type, spec, submissions)
    else:
        result = grader.grade(question.topic, question.question_type, spec, user_answer)

    attempt = Attempt(
        user_id=user.id,
        question_id=question.id,
        user_answer=user_answer,
        parsed_answer=result.get("given"),
        correct=result["correct"],
        reason=result["reason"],
        work_text=work_text,
        lines_boxes=lines_boxes,
        hints_used=hints_used,
    )
    db.add(attempt)
    await db.flush()

    resp = {
        "attempt_id": attempt.id,
        "correct": result["correct"],
        "reason": result["reason"],
        "given": result.get("given"),
        "expected": result["expected"],
        "graph": result.get("graph"),
    }
    if is_multi:
        resp["parts"] = result.get("parts")
        if part:
            resp["part"] = result.get("part")
            resp["all_complete"] = result.get("all_complete")

    step_check = None
    if work_text:
        step_check = grader.analyze_work(
            question.topic, question.question_type, question.spec, work_text.split("\n")
        )
        if is_multi:
            step_check = {**step_check, "parts": result.get("parts")}
        attempt.formula_breakdown = step_check.get("formula_breakdown")
        attempt.step_check = step_check
        resp["step_check"] = step_check

    if question.topic == "functions" and work_text:
        resp["graph_check"] = grader.grade_graph_check(question.spec, work_text.split("\n"))

    if not result["correct"]:
        steps_text = _steps_text(question)
        allowed = await cache.allow_gemini(str(user.id))
        context = {
            "question_text": question.prompt,
            "part": result.get("part") if is_multi else None,
            "user_answer": user_answer,
            "expected": result.get("expected"),
        }
        resp["explanation"] = await _build_explanation(
            db, user, question, attempt.id, "incorrect", use_ai=True, steps_text=steps_text,
            allow_gemini=allowed, context=context,
        )
        if work_text and not _work_usable(step_check):
            resp["work_check"] = {"content": WORK_UNREADABLE_MSG, "provider": "system"}
        else:
            check, provider = await llm.check_work(
                question.prompt, work_text or user_answer, steps_text, str(question.expected_answer),
                allow_gemini=allowed, step_check=step_check,
            )
            if check:
                resp["work_check"] = {"content": check, "provider": provider}

    # Auto-save progress: every grade updates the exercise's session so long
    # multi-part exercises can be resumed without an explicit button.
    if is_multi:
        if result.get("part"):
            session = await _upsert_session(
                db, user, question.id, result["part"],
                correct=result["correct"], typed=user_answer,
                work_text=work_text, lines_boxes=lines_boxes,
            )
        else:
            session = await _upsert_session(db, user, question.id)
            for v in result.get("parts") or []:
                _merge_part_state(session, v["label"], correct=v["correct"])
        if result["correct"] and result.get("all_complete"):
            session.status = "completed"

    await db.commit()
    return resp


async def explain_question(db, user, question_id, user_answer=None, work_text=None) -> dict:
    question = await db.get(Question, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    steps_text = _steps_text(question)
    context = {"question_text": question.prompt, "part": None, "user_answer": user_answer, "expected": None}
    if user_answer:
        spec = question.spec or {}
        labels = [str(p.get("label")) for p in spec.get("parts", [])] if isinstance(spec.get("parts"), list) else []
        if labels:
            # The student may have prefixed their answer with a part label.
            import re as _re
            for lab in labels:
                if _re.match(rf"^\s*{_re.escape(lab)}\s*[:=]", user_answer.strip()):
                    context["part"] = lab
                    break
    result = await _build_explanation(db, user, question, None, "manual", use_ai=True, steps_text=steps_text, context=context)
    rows = await db.execute(select(Step).where(Step.question_id == question.id).order_by(Step.step_order))
    result["steps"] = [
        {"step_order": s.step_order, "title": s.title, "detail": s.detail, "formula": s.formula}
        for s in rows.scalars()
    ]
    result["graph"] = solver.solve(question.topic, question.question_type, question.spec).get("graph")
    if user_answer:
        allowed = await cache.allow_gemini(str(user.id))
        step_check = None
        if work_text:
            step_check = grader.analyze_work(
                question.topic, question.question_type, question.spec, work_text.split("\n")
            )
            result["step_check"] = step_check
            if question.topic == "functions":
                result["graph_check"] = grader.grade_graph_check(question.spec, work_text.split("\n"))
        if work_text and not _work_usable(step_check):
            result["work_check"] = {"content": WORK_UNREADABLE_MSG, "provider": "system"}
        else:
            check, provider = await llm.check_work(
                question.prompt, work_text or user_answer, steps_text, str(question.expected_answer),
                allow_gemini=allowed, step_check=step_check,
            )
            if check:
                result["work_check"] = {"content": check, "provider": provider}
    await db.commit()
    return result


async def get_question(db, question_id) -> dict:
    question = await db.get(Question, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    rows = await db.execute(select(Step).where(Step.question_id == question.id).order_by(Step.step_order))
    steps = [
        {"step_order": s.step_order, "title": s.title, "detail": s.detail, "formula": s.formula}
        for s in rows.scalars()
    ]
    return {
        "id": question.id,
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "prompt": question.prompt,
        "prompt_latex": question.prompt_latex,
        "z_display": question.z_display,
        "source": question.source,
        "formula_tags": question.formula_tags or [],
        "formula_difficulty": formulas.formula_difficulty(question.formula_tags or []) if question.formula_tags else None,
        "steps": steps,
        "graph": solver.solve(question.topic, question.question_type, question.spec).get("graph"),
    }


async def list_attempts(db, user, limit=50) -> list:
    rows = await db.execute(
        select(Attempt, Question)
        .join(Question, Question.id == Attempt.question_id)
        .where(Attempt.user_id == user.id)
        .order_by(Attempt.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": a.id,
            "question_id": a.question_id,
            "topic": q.topic,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "prompt": q.prompt,
            "prompt_latex": q.prompt_latex,
            "expected_answer": q.expected_answer,
            "user_answer": a.user_answer,
            "correct": a.correct,
            "reason": a.reason,
            "formula_breakdown": a.formula_breakdown,
            "hints_used": a.hints_used,
            "created_at": a.created_at,
        }
        for a, q in rows.all()
    ]


async def get_attempt(db, user, attempt_id) -> dict:
    attempt = await db.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    question = await db.get(Question, attempt.question_id)

    steps = []
    if question is not None:
        rows = await db.execute(
            select(Step).where(Step.question_id == question.id).order_by(Step.step_order)
        )
        steps = [
            {"step_order": s.step_order, "title": s.title, "detail": s.detail, "formula": s.formula}
            for s in rows.scalars()
        ]

    expl_rows = await db.execute(select(Explanation).where(Explanation.attempt_id == attempt.id))
    explanations = [
        {"provider": e.provider, "content": e.content, "trigger": e.trigger, "created_at": e.created_at}
        for e in expl_rows.scalars()
    ]

    return {
        "id": attempt.id,
        "user_answer": attempt.user_answer,
        "parsed_answer": attempt.parsed_answer,
        "correct": attempt.correct,
        "reason": attempt.reason,
        "work_text": attempt.work_text,
        "step_check": attempt.step_check,
        "lines_boxes": attempt.lines_boxes,
        "formula_breakdown": attempt.formula_breakdown,
        "hints_used": attempt.hints_used,
        "created_at": attempt.created_at,
        "question": {
            "id": question.id,
            "topic": question.topic,
            "question_type": question.question_type,
            "difficulty": question.difficulty,
            "prompt": question.prompt,
            "prompt_latex": question.prompt_latex,
            "expected_answer": question.expected_answer,
            "formula_tags": question.formula_tags or [],
            "steps": steps,
        } if question is not None else None,
        "explanations": explanations,
    }


def _merge_part_state(session, part, correct=None, typed=None, work_text=None, lines_boxes=None):
    """Merge one part's saved state into the session's JSONB state.

    Builds a brand-new nested dict so the JSONB attribute gets a genuinely new
    object — in-place mutation + same-object reassignment would compare equal
    and be silently skipped by SQLAlchemy's change detection (existing rows
    never persisted part updates without this)."""
    parts = dict((session.state or {}).get("parts") or {})
    entry = dict(parts.get(part or "", {}))
    if typed is not None:
        entry["typed"] = typed
    if work_text is not None:
        entry["work_text"] = work_text
    if lines_boxes is not None:
        entry["lines_boxes"] = lines_boxes
    if correct is not None:
        entry["correct"] = bool(correct)
    parts[part or ""] = entry
    session.state = {"parts": parts}


async def _upsert_session(db, user, question_id, part=None, correct=None, typed=None, work_text=None, lines_boxes=None):
    session = await db.scalar(
        select(StudySession).where(StudySession.user_id == user.id, StudySession.question_id == question_id)
    )
    if session is None:
        session = StudySession(user_id=user.id, question_id=question_id, status="in_progress", state={"parts": {}})
        db.add(session)
    _merge_part_state(session, part or "", correct=correct, typed=typed, work_text=work_text, lines_boxes=lines_boxes)
    return session


def _session_summary(session, question=None):
    state = session.state or {}
    parts = state.get("parts") or {}
    total = 0
    if question is not None and isinstance(question.spec.get("parts"), list):
        total = len(question.spec["parts"])
    done = sum(1 for p in parts.values() if p.get("correct"))
    return {
        "id": session.id,
        "question_id": session.question_id,
        "status": session.status,
        "parts_done": done,
        "parts_total": total,
        "updated_at": session.updated_at,
    }


async def save_progress(db: AsyncSession, user, req: SaveProgressRequest) -> dict:
    """Explicit 'Save progress' button: capture the current part's typed/OCR'd
    work so the exercise can be resumed later. Idempotent (one session per user
    + question)."""
    question = await db.get(Question, req.question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    session = await _upsert_session(
        db, user, req.question_id, req.part,
        typed=req.typed, work_text=req.work_text, lines_boxes=req.lines_boxes,
    )
    await db.commit()
    # Refresh in the async context so the server-generated updated_at (and all
    # other columns) are loaded before the sync summary reads them — avoids a
    # lazy-load checkout from a sync context (asyncpg pre_ping -> MissingGreenlet).
    await db.refresh(session)
    return _session_summary(session, question)


async def list_progress(db: AsyncSession, user) -> list:
    """The user's saved exercises (in-progress first, newest first)."""
    rows = await db.execute(
        select(StudySession, Question)
        .join(Question, Question.id == StudySession.question_id)
        .where(StudySession.user_id == user.id)
        .order_by(
            case((StudySession.status == "in_progress", 0), else_=1),
            StudySession.updated_at.desc(),
        )
        .limit(50)
    )
    out = []
    for s, q in rows.all():
        summary = _session_summary(s, q)
        summary["question"] = {
            "id": q.id,
            "topic": q.topic,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "prompt": q.prompt,
            "prompt_latex": q.prompt_latex,
        }
        out.append(summary)
    return out


async def get_progress(db: AsyncSession, user, session_id) -> dict:
    """Full saved state for resuming: the question (with params) plus every
    part's typed answer, OCR'd work, line boxes, and correct flag."""
    session = await db.get(StudySession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saved progress not found")
    question = await db.get(Question, session.question_id)
    parts = (session.state or {}).get("parts") or {}
    labels = []
    if question is not None and isinstance(question.spec.get("parts"), list):
        labels = [str(p.get("label")) for p in question.spec["parts"] if p.get("label")]
    ordered = {lab: parts.get(lab) or {} for lab in labels}
    return {
        "id": session.id,
        "status": session.status,
        "updated_at": session.updated_at,
        "parts": ordered,
        "question": {
            "id": question.id,
            "topic": question.topic,
            "question_type": question.question_type,
            "difficulty": question.difficulty,
            "params": question.spec,
            "prompt": question.prompt,
            "prompt_latex": question.prompt_latex,
            "z_display": question.z_display,
            "source": question.source,
            "formula_tags": question.formula_tags or [],
        } if question is not None else None,
    }


async def delete_progress(db: AsyncSession, user, session_id) -> dict:
    session = await db.get(StudySession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saved progress not found")
    await db.delete(session)
    await db.commit()
    return {"deleted": True}


async def get_formulas_catalog() -> dict:
    """Full formula registry grouped by topic, for the admin view and the
    student-facing formula sheet. Each entry carries `variants`: every
    generator (topic, question_type, variant, difficulty) combo known to
    touch that formula, so a "Practice this" link can force it directly."""
    by_group: dict[str, list] = {}
    for tag, e in formulas.FORMULA_REGISTRY.items():
        g = e.get("group") or "other"
        by_group.setdefault(g, []).append({
            "id": tag,
            "name_en": e.get("name_en"),
            "name_km": e.get("name_km") or "",
            "latex": e.get("latex"),
            "weight": e.get("weight", 1),
            "formulas": e.get("formulas") or [],
            "variants": await generator.variants_for_formula(tag),
        })
    order = [g for g in ("complex", "limit", "integral", "probability", "functions") if g in by_group]
    return {"topics": [{"topic": g, "entries": by_group[g]} for g in order]}


async def get_template_inventory() -> dict:
    """Live template inventory: for every topic/question type/difficulty (and
    every integral variant), a deterministic sample with its generated params,
    answer, and formula tags — so the admin view always reflects what runs."""
    topics = []
    for topic in generator.TOPICS:
        types = []
        for qt in solver.QUESTION_TYPES_BY_TOPIC.get(topic, ()):
            difficulties = []
            for diff in ("easy", "medium", "hard"):
                variants = [None]
                if topic == "integral" and qt == "definite_integral":
                    variants = _INTEGRAL_VARIANT_BY_DIFFICULTY[diff]
                elif topic == "integral" and qt == "indefinite_integral":
                    variants = _INDEFINITE_VARIANT_BY_DIFFICULTY[diff]
                elif topic == "probability":
                    variants = scenarios.VARIANT_BY_DIFFICULTY[diff]
                for variant in variants:
                    # Show several deterministic samples per variant so the
                    # parameterized variety (not just one shape) is visible.
                    samples = 1 if topic == "complex" else 3
                    for i in range(samples):
                        try:
                            problem = await generator.generate(
                                topic, diff, seed=hash((topic, qt, diff, variant, i)) & 0xFFFFFFFF,
                                question_type=qt, generation_mode="templates", variant=variant,
                            )
                        except Exception:
                            continue
                        solution = solver.solve(topic, problem["question_type"], problem["params"])
                        difficulties.append({
                            "difficulty": diff,
                            "variant": problem["params"].get("variant"),
                            "params": problem["params"],
                            "prompt": problem["prompt"],
                            "prompt_latex": problem.get("prompt_latex"),
                            "answer": str(solution["answer_exact"]),
                            "answer_latex": solution.get("answer_latex"),
                            "formula_tags": solution.get("formula_tags", []),
                        })
            types.append({"question_type": qt, "difficulties": difficulties})
        topics.append({"topic": topic, "question_types": types})
    return {"topics": topics}


_STRUCT_PATTERNS = {
    ("complex", "modulus"): r"\lvert z \rvert = \lvert a + bi \rvert",
    ("complex", "argument"): r"\arg(z),\ z = a + bi",
    ("complex", "conjugate"): r"\overline{a + bi}",
    ("complex", "real_part"): r"\operatorname{Re}(a + bi)",
    ("complex", "imaginary_part"): r"\operatorname{Im}(a + bi)",
    ("limit", "limit"): r"\lim_{x \to a} f(x)",
    ("functions", "study"): r"g(x) = \ln\left(\frac{ax+b}{cx+d}\right)",
}

_integral_structure_payload = None


def _build_integral_structure_payload() -> dict:
    """Deterministic per-structure samples for the integral topic (one per
    unique template structure). Memoized — the payload is expensive to compute
    and identical on every call."""
    global _integral_structure_payload
    if _integral_structure_payload is not None:
        return _integral_structure_payload

    by_qt: dict[str, list] = {}
    for struct in structures.all_integral_structures():
        by_qt.setdefault(struct["question_type"], []).append(struct)

    question_types = []
    for qt in ("indefinite_integral", "definite_integral"):
        entries = []
        for struct in by_qt.get(qt, []):
            sample = structures.build_sample(
                struct, seed=zlib.crc32(struct["id"].encode()) & 0xFFFFFFFF
            )
            solution = sample["solution"]
            entries.append({
                "id": struct["id"],
                "question_type": qt,
                "difficulty": struct["difficulty"],
                "pattern": struct["pattern"],
                "pattern_latex": structures.build_pattern_latex(struct),
                "sample_prompt": sample["prompt"],
                "sample_prompt_latex": sample["prompt_latex"],
                "sample_answer": str(solution["answer_exact"]),
                "sample_answer_latex": solution.get("answer_latex"),
                "formula_tags": solution.get("formula_tags", []),
                "source_labels": struct["source_labels"],
            })
        question_types.append({"question_type": qt, "structures": entries})

    _integral_structure_payload = {"topic": "integral", "question_types": question_types}
    return _integral_structure_payload


_limit_structure_payload = None


def _build_limit_structure_payload() -> dict:
    """One card per limit *technique* (not per parameterized shape — most limit
    techniques are tied to a specific identity, not free coefficients; see
    `structures.LIMIT_TECHNIQUES`). Parameterizable techniques additionally get
    a deterministic procedurally-generated sample; curated-only techniques show
    one real BAC II exercise instead. Memoized like the integral payload."""
    global _limit_structure_payload
    if _limit_structure_payload is not None:
        return _limit_structure_payload

    curated_by_technique: dict[str, list] = {}
    for item in structures._LIMIT_CURATED_TEMPLATES:
        curated_by_technique.setdefault(item["formula_name"], []).append(item)

    entries = []
    for technique, meta in structures.LIMIT_TECHNIQUES.items():
        curated = sorted(curated_by_technique.get(technique, []), key=lambda it: it["id"])
        source_labels = [it["id"] for it in curated]
        entry = {
            "id": technique,
            "technique": technique,
            "question_type": "limit",
            "difficulty": meta["difficulty"],
            "parameterizable": meta["parameterizable"],
            "description": meta["description"],
            # Limit techniques don't share one symbolic shape the way e.g.
            # integral's "ax^2+bx+c" family does — a solving-technique
            # description is the closest equivalent to what the pattern box
            # shows for other topics, and (unlike sample_prompt) it's the
            # same for every instance of the technique, not one example.
            "pattern": meta["description"],
            "pattern_latex": None,
            "source_labels": source_labels,
        }
        if meta["parameterizable"]:
            problem = generate_limit_for_technique(
                random.Random(zlib.crc32(technique.encode()) & 0xFFFFFFFF), technique,
            )
            solution = solver.solve("limit", "limit", problem["params"])
            entry.update({
                "sample_prompt": problem["prompt"],
                "sample_prompt_latex": problem.get("prompt_latex"),
                "sample_answer": str(solution["answer_exact"]),
                "sample_answer_latex": solution.get("answer_latex"),
                "formula_tags": solution.get("formula_tags", []),
            })
        elif curated:
            example = curated[0]
            entry.update({
                "sample_prompt": f"\\(\\lim_{{x \\to {latex(example['point'])}}} {latex(example['expr'])}\\)",
                "sample_answer": example["answer_latex"],
                "sample_answer_latex": example["answer_latex"],
                "formula_tags": [technique],
            })
        entries.append(entry)

    _limit_structure_payload = {
        "topic": "limit",
        "question_types": [{"question_type": "limit", "structures": entries}],
    }
    return _limit_structure_payload


async def get_template_structures() -> dict:
    """One card per unique template structure: the symbolic slot pattern, one
    deterministic filled sample (prompt + answer), formula tags, and the source
    BAC II exercise labels that map to it. Grouped by topic → question type."""
    topics = [_build_integral_structure_payload(), _build_limit_structure_payload()]

    for topic in generator.TOPICS:
        if topic in ("integral", "limit"):
            continue
        question_types = []
        for qt in solver.QUESTION_TYPES_BY_TOPIC.get(topic, ()):
            entries = []
            for diff in ("easy", "medium", "hard"):
                variants = [None]
                if topic == "probability":
                    variants = list(scenarios.VARIANT_BY_DIFFICULTY.get(diff, ()))
                for variant in variants:
                    try:
                        problem = await generator.generate(
                            topic, diff,
                            seed=zlib.crc32(f"{topic}:{qt}:{diff}:{variant}".encode()) & 0xFFFFFFFF,
                            question_type=qt, generation_mode="templates", variant=variant,
                        )
                        solution = solver.solve(topic, problem["question_type"], problem["params"])
                    except Exception:
                        continue
                    if variant:
                        pattern = f"scenario {variant}"
                    else:
                        pattern = _STRUCT_PATTERNS.get((topic, qt), f"{topic} {qt}")
                    entries.append({
                        "id": f"{topic}:{qt}:{diff}" + (f":{variant}" if variant else ""),
                        "question_type": qt,
                        "difficulty": diff,
                        "pattern": pattern,
                        "pattern_latex": _STRUCT_PATTERNS.get((topic, qt)) if not variant else None,
                        "sample_prompt": problem["prompt"],
                        "sample_prompt_latex": problem.get("prompt_latex"),
                        "sample_answer": str(solution["answer_exact"]),
                        "sample_answer_latex": solution.get("answer_latex"),
                        "formula_tags": solution.get("formula_tags", []),
                        "source_labels": [],
                    })
            question_types.append({"question_type": qt, "structures": entries})
        topics.append({"topic": topic, "question_types": question_types})

    return {"topics": topics}


async def get_stats(db, user) -> dict:
    total = await db.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user.id)) or 0
    correct = await db.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.user_id == user.id, Attempt.correct.is_(True))
    ) or 0

    rows = await db.execute(
        select(
            Question.question_type,
            func.count().label("total"),
            func.sum(case((Attempt.correct.is_(True), 1), else_=0)).label("correct"),
        )
        .join(Attempt, Attempt.question_id == Question.id)
        .where(Attempt.user_id == user.id)
        .group_by(Question.question_type)
    )
    by_topic = [{"question_type": qt, "attempts": t, "correct": c or 0} for qt, t, c in rows.all()]

    # Restricted to incorrect attempts only: the step-check runs on every
    # attempt (including correct ones solved via a valid alternative path),
    # so counting a correct attempt's non-standard-path checkpoints as
    # "missed" would flag a fake weakness. Only a genuinely wrong final
    # answer means the formula was actually fumbled.
    breakdowns = (
        await db.scalars(
            select(Attempt.formula_breakdown).where(
                Attempt.user_id == user.id, Attempt.correct.is_(False)
            )
        )
    ).all()
    by_formula: dict[str, dict] = {}
    for bd in breakdowns:
        for item in bd or []:
            fid = item.get("formula")
            if not fid:
                continue
            agg = by_formula.setdefault(fid, {"formula": fid, "attempts": 0, "reached": 0, "missed": 0})
            agg["attempts"] += 1
            if item.get("reached"):
                agg["reached"] += 1
            else:
                agg["missed"] += 1
    for agg in by_formula.values():
        agg["name_en"] = formulas.resolve_formula(agg["formula"])["name_en"]

    return {
        "total_attempts": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "by_topic": by_topic,
        "by_formula": sorted(by_formula.values(), key=lambda a: (-a["missed"], a["formula"])),
    }
