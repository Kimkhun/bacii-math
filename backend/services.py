import asyncio
import hashlib
import json
import os
import random
import uuid
import zlib
from datetime import datetime, timedelta, timezone
from fractions import Fraction

from fastapi import HTTPException, status
from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sympy import latex

import cache
from engine import explainer, formulas, generator, grader, llm, solver
from engine.core import coaching, mastery, skills, template_shapes
from engine.core.rubric import score_work
from engine.topics.past_exam.rubric import mark_full_exam
from engine.topics.functions import graph_grader
from engine.topics.functions.generator import _FUNCTION_CURATED_TEMPLATES
from engine.topics.integral import structures as integral_structures
from engine.topics.integral.generator import (
    _INDEFINITE_VARIANT_BY_DIFFICULTY,
    _INTEGRAL_VARIANT_BY_DIFFICULTY,
)
from engine.topics.limit import structures as limit_structures
from engine.topics.limit.generator import _build_curated_limit, generate_limit_for_technique
from engine.topics.probability import scenarios
from models import Attempt, Explanation, Question, SkillState, Step, StudySession, User
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


def _steps_text(question: Question, lang: str = "en") -> str:
    solution = solver.solve(question.topic, question.question_type, question.spec)
    return explainer.build_text(question.topic, question.question_type, question.spec, solution, lang=lang)


async def _build_explanation(db, user, question, attempt_id, trigger, use_ai, steps_text=None, allow_gemini=None, context=None, lang: str = "en") -> dict:
    steps_text = steps_text or _steps_text(question, lang=lang)
    content = steps_text
    provider = "deterministic"
    intervened = False

    if use_ai:
        spec_key = ":".join(f"{k}={v}" for k, v in sorted(question.spec.items()))
        # Version the cache with the deterministic steps' content: if a solver
        # change alters the steps, stale narrations must never be served for
        # questions with the same params.
        steps_digest = hashlib.sha1(steps_text.encode("utf-8")).hexdigest()[:12]
        key = f"explain:{question.topic}:{question.question_type}:{spec_key}:{lang}:{steps_digest}"
        cached = await cache.get_explanation(key)
        if cached:
            content, provider, intervened = cached, "gemini", True
        else:
            if allow_gemini is None:
                allow_gemini = await cache.allow_gemini(str(user.id))
            text, got_provider = await llm.narrate(steps_text, allow_gemini=allow_gemini, context=context, user_id=user.id, lang=lang)
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


async def grade_question(db, user, question_id, user_answer, work_text=None, lines_boxes=None, part=None, hints_used=0, strokes=None, strokes_thumb=None, lang: str = "en") -> dict:
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
        if work_text:
            segments = grader.split_work_by_part(work_text.split("\n"), labels)
            part_val = grader.last_value_of_lines(segments.get(part, []))
            if part_val:
                user_answer = part_val
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
        strokes=strokes,
        strokes_thumb=strokes_thumb,
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

        if question.topic != "functions":
            try:
                rubric_result = score_work(
                    question.topic, question.question_type, spec, work_text.split("\n"), question_points=10
                )
                resp["rubric_score"] = _fractions_to_float(rubric_result)
            except Exception:
                pass

    if question.topic == "functions" and work_text:
        resp["graph_check"] = grader.grade_graph_check(question.spec, work_text.split("\n"))

    allowed = await cache.allow_gemini(str(user.id))
    sol_km = None
    if question.topic == "functions":
        try:
            km_res = await km_solution_for_question(db, user, question.id)
            if km_res and km_res.get("solution_km"):
                sol_km = km_res["solution_km"]
        except Exception:
            pass

    if not result["correct"]:
        steps_text = _steps_text(question, lang=lang)
        context = {
            "question_text": question.prompt,
            "part": result.get("part") if is_multi else None,
            "user_answer": user_answer,
            "expected": result.get("expected"),
        }
        resp["explanation"] = await _build_explanation(
            db, user, question, attempt.id, "incorrect", use_ai=True, steps_text=steps_text,
            allow_gemini=allowed, context=context, lang=lang,
        )
        if work_text and not _work_usable(step_check):
            unread_msg = "មិនអាចអានជំហានសរសេរដៃរបស់អ្នកបានច្បាស់លាស់។ សូមសាកល្បងសរសេរម្តងទៀត។" if lang == "km" else WORK_UNREADABLE_MSG
            resp["work_check"] = {"content": unread_msg, "provider": "system"}
        else:
            check, provider = await llm.check_work(
                question.prompt, work_text or user_answer, steps_text, str(question.expected_answer),
                allow_gemini=allowed, step_check=step_check, lang=lang, user_id=user.id,
            )
            if check:
                resp["work_check"] = {"content": check, "provider": provider}

    if allowed and sol_km:
        rubric_tip, provider = await llm.check_rubric_feedback(
            question_text=question.prompt,
            user_submission=work_text or user_answer or "",
            correct_solution_km=sol_km,
            is_correct=result["correct"],
            allow_gemini=allowed,
            step_check=step_check,
            user_id=user.id,
            lang=lang,
        )
        if rubric_tip:
            resp["teacher_feedback"] = {"content": rubric_tip, "provider": provider}

    # Update the hidden skill trackers behind the student's profile. Runs on
    # every attempt (right or wrong) — a correct answer is exactly as much
    # evidence of mastery as a wrong one is of need.
    await record_attempt_skills(
        db, user, question,
        correct=result["correct"],
        step_check=step_check,
    )
    return resp


async def grade_graph_drawing(db, user, question_id, strokes_thumb: str) -> dict:
    """Grade a student's hand-drawn graph against the reference using Gemini vision."""
    question = await db.get(Question, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")

    spec = question.spec or {}
    graph = spec.get("graph")
    if not graph:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This question has no reference graph")

    allowed = await cache.allow_gemini(str(user.id))
    if not allowed:
        return {"error": "rate_limited", "message": "Too many requests. Try again later."}

    result = await graph_grader.grade_student_graph(
        graph=graph,
        function_expr=spec.get("function_expr", ""),
        exercise_text=question.prompt,
        student_thumb=strokes_thumb,
        user_id=user.id,
    )
    if result is None:
        return {"error": "gemini_failed", "message": "Graph grading unavailable. Try again later."}
    return result



async def explain_question(db, user, question_id, user_answer=None, work_text=None, lang: str = "en") -> dict:
    question = await db.get(Question, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    steps_text = _steps_text(question, lang=lang)
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
    result = await _build_explanation(db, user, question, None, "manual", use_ai=True, steps_text=steps_text, context=context, lang=lang)
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
                allow_gemini=allowed, step_check=step_check, lang=lang, user_id=user.id,
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
            "strokes_thumb": a.strokes_thumb,
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
        "strokes": attempt.strokes,
        "strokes_thumb": attempt.strokes_thumb,
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


def _merge_part_state(session, part, correct=None, typed=None, work_text=None, lines_boxes=None, strokes=None, strokes_thumb=None):
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
    if strokes is not None:
        entry["strokes"] = strokes
    if strokes_thumb is not None:
        entry["strokes_thumb"] = strokes_thumb
    if correct is not None:
        entry["correct"] = bool(correct)
    parts[part or ""] = entry
    session.state = {"parts": parts}


async def _upsert_session(db, user, question_id, part=None, correct=None, typed=None, work_text=None, lines_boxes=None, strokes=None, strokes_thumb=None):
    session = await db.scalar(
        select(StudySession).where(StudySession.user_id == user.id, StudySession.question_id == question_id)
    )
    if session is None:
        session = StudySession(user_id=user.id, question_id=question_id, status="in_progress", state={"parts": {}})
        db.add(session)
    _merge_part_state(session, part or "", correct=correct, typed=typed, work_text=work_text, lines_boxes=lines_boxes, strokes=strokes, strokes_thumb=strokes_thumb)
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
        strokes=req.strokes, strokes_thumb=req.strokes_thumb,
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
    # Teaching order first, then anything else the registry has — a topic that
    # grows a formula file must not silently vanish from the formula sheet.
    preferred = ("complex", "limit", "integral", "probability", "functions", "continuity",
                 "derivatives", "differential_equations", "vectors_space", "conics")
    order = [g for g in preferred if g in by_group]
    order += [g for g in by_group if g not in order]
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
                    # One deterministic sample per variant — enough to show the
                    # shape without repeating the same exercise N times for
                    # curated-only topics (e.g. functions, which has no
                    # parameterized sampler). Curated picks are retried until
                    # distinct so the three difficulty rows never show the same
                    # exercise twice.
                    seen_ids: set = set()
                    for i in range(1):
                        problem = None
                        for attempt in range(6):
                            try:
                                cand = await generator.generate(
                                    topic, diff, seed=hash((topic, qt, diff, variant, attempt)) & 0xFFFFFFFF,
                                    question_type=qt, generation_mode="templates", variant=variant,
                                )
                            except Exception:
                                continue
                            pid = (cand.get("params") or {}).get("id")
                            if pid is None or pid not in seen_ids:
                                problem = cand
                                if pid is not None:
                                    seen_ids.add(pid)
                                break
                        if problem is None:
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
    ("continuity", "check_continuity"): r"f(x) = \begin{cases} g(x) & x < a \\ h(x) & x \geq a \end{cases}",
    ("derivatives", "compute_derivative"): r"y' = \frac{d}{dx}\, f(x)",
    ("differential_equations", "solve_ode"): r"a\,y'' + b\,y' + c\,y = 0",
    ("vectors_space", "vector_ops"): r"\overrightarrow{AB},\ \lvert \overrightarrow{AB} \rvert,\ \vec{u} \cdot \vec{v}",
    ("conics", "classify_conic"): r"A x^{2} + B y^{2} + C x + D y + E = 0",
    ("probability", "counting"): r"\binom{n}{k},\ P(n,k),\ n!",
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
    for struct in integral_structures.all_integral_structures():
        by_qt.setdefault(struct["question_type"], []).append(struct)

    question_types = []
    for qt in ("indefinite_integral", "definite_integral"):
        entries = []
        for struct in by_qt.get(qt, []):
            sample = integral_structures.build_sample(
                struct, seed=zlib.crc32(struct["id"].encode()) & 0xFFFFFFFF
            )
            solution = sample["solution"]
            entries.append({
                "id": struct["id"],
                "question_type": qt,
                "difficulty": struct["difficulty"],
                "pattern": struct["pattern"],
                "pattern_latex": integral_structures.build_pattern_latex(struct),
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
    `limit_structures.LIMIT_TECHNIQUES`). Parameterizable techniques additionally get
    a deterministic procedurally-generated sample; curated-only techniques show
    one real BAC II exercise instead. Memoized like the integral payload."""
    global _limit_structure_payload
    if _limit_structure_payload is not None:
        return _limit_structure_payload

    curated_by_technique: dict[str, list] = {}
    for item in limit_structures._LIMIT_CURATED_TEMPLATES:
        curated_by_technique.setdefault(item["formula_name"], []).append(item)

    entries = []
    for technique, meta in limit_structures.LIMIT_TECHNIQUES.items():
        curated = sorted(curated_by_technique.get(technique, []), key=lambda it: it["id"])
        source_labels = [it["id"] for it in curated]
        entry = {
            "id": technique,
            # The technique's plain-language description sits under the template,
            # the way the shape topics show their technique line.
            "technique": meta["description"],
            "question_type": "limit",
            "difficulty": meta["difficulty"],
            "parameterizable": meta["parameterizable"],
            "description": meta["description"],
            # Header shows the symbolic slot-form template — the limit analogue
            # of integral's "\\int a x^2 + b x + c\\,dx" — so the card reads like
            # the integral cards. Falls back to the description text if a
            # technique has no authored template.
            "pattern": meta["description"],
            "pattern_latex": limit_structures.TEMPLATE_LATEX.get(technique),
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
            point = example["point"]
            point_latex = r"+\infty" if str(point) == "oo" else latex(point)
            expr_latex = latex(example["expr"])
            entry.update({
                # Render the concrete curated example as LaTeX (frontend wraps
                # sample_prompt_latex in \\( \\)). Previously this was stuffed
                # into sample_prompt as a raw \\(...\\) string, which the admin
                # card printed verbatim instead of rendering as math.
                "sample_prompt": f"lim(x -> {point}) of {example['expr']}",
                "sample_prompt_latex": rf"\lim_{{x \to {point_latex}}} {expr_latex}",
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


_STRUCTURE_PAYLOAD_CACHE: dict[str, dict] = {}


async def _build_topic_structure_payload(topic: str) -> dict:
    """Full structure cards for one topic, memoized per topic so repeat
    requests (and per-topic admin lazy-loading) never re-solve everything."""
    cached = _STRUCTURE_PAYLOAD_CACHE.get(topic)
    if cached is not None:
        total_structures = sum(len(qt.get("structures", [])) for qt in cached.get("question_types", []))
        if total_structures > 0:
            return cached
    if topic == "integral":
        payload = _build_integral_structure_payload()
    elif topic == "limit":
        payload = _build_limit_structure_payload()
    elif topic in template_shapes.CURATED_SHAPE_TOPICS:
        payload = _build_curated_shape_payload(topic)
    else:
        payload = await _build_generic_topic_payload(topic)
    total_structures = sum(len(qt.get("structures", [])) for qt in payload.get("question_types", []))
    if total_structures > 0:
        _STRUCTURE_PAYLOAD_CACHE[topic] = payload
    return payload


async def _km_solution_for(
    key: str,
    facts: dict | None = None,
    topic: str | None = None,
    question_type: str | None = None,
    variant: str | None = None,
    difficulty: str | None = None,
) -> dict | None:
    """Check cache for a Gemini-generated Khmer solution JSON. If missing and
    we have facts, generate, cache, and return."""
    cached = await cache.get_km_solution(key)
    if cached:
        return cached
    if not facts:
        return None
    km = await llm.narrate_km_solution(facts)
    if km and km.get("parts"):
        await cache.set_km_solution(key, km)
        return km
    return None


def _render_km_solution(km: dict | None) -> str | None:
    """Render structured km JSON into readable text for display in admin."""
    if not km or not km.get("parts"):
        return None
    blocks = []
    for part in km["parts"]:
        lines = [f"**{part['label']}**"]
        for s in part.get("steps", []):
            km_text = s.get("khmer") or ""
            latex_expr = s.get("latex") or ""
            if km_text:
                has_formula = "$" in km_text or "\\(" in km_text or "=" in km_text
                if latex_expr and not has_formula:
                    lines.append(f"{km_text}\n\n$${latex_expr}$$")
                else:
                    lines.append(km_text)
            elif latex_expr:
                lines.append(f"$${latex_expr}$$")
        if part.get("answer_khmer"):
            lines.append(f"ចម្លើយ៖ {part['answer_khmer']}")
        blocks.append("\n\n".join(lines))
    return "\n\n".join(blocks)


def _build_curated_shape_payload(topic: str) -> dict:
    """Template cards for the curated-replay topics (derivatives, continuity,
    conics, vectors_space, differential_equations): one card per exercise shape
    with the coefficients abstracted into slot letters, rather than one card per
    concrete curated exercise. See ``engine/core/template_shapes.py``."""
    by_qt: dict[str, list] = {}
    for shape in template_shapes.shapes_for(topic):
        by_qt.setdefault(shape["question_type"], []).append(shape)
    question_types = [
        {"question_type": qt, "structures": shapes}
        for qt, shapes in by_qt.items()
    ]
    return {"topic": topic, "question_types": question_types}


async def _build_generic_topic_payload(topic: str) -> dict:
    """Structure cards for complex / probability / functions (the topics with
    no dedicated payload builder)."""
    question_types = []
    for qt in solver.QUESTION_TYPES_BY_TOPIC.get(topic, ()):
        entries = []
        if topic == "functions":
            # Parallelize all curated function exercises so they generate simultaneously
            async def _resolve_fn_item(item):
                try:
                    params = {k: v for k, v in item.items()
                              if k not in ("prompt", "prompt_latex", "pattern", "pattern_latex")}
                    solution = solver.solve(topic, "study", params)
                    km_facts = solution.get("km_facts")
                    km = await _km_solution_for(f"fn_km:study:{item.get('id')}", km_facts)
                    sol_km_text = _render_km_solution(km) or solution.get("solution_km")
                except Exception as e:
                    import logging
                    logging.getLogger("bacii").exception("Failed to resolve function item %s: %s", item.get("id"), e)
                    return None
                return {
                    "id": f"functions:study:{item.get('id')}",
                    "question_type": "study",
                    "difficulty": item.get("difficulty", "hard"),
                    "pattern": item.get("pattern") or "function study",
                    "pattern_latex": item.get("pattern_latex"),
                    "sample_prompt": item.get("prompt") or "",
                    "sample_prompt_latex": item.get("prompt_latex"),
                    "sample_answer": solution.get("answer_display") or str(solution["answer_exact"]),
                    "sample_answer_latex": solution.get("answer_latex"),
                    "formula_tags": solution.get("formula_tags", []),
                    "source_labels": [f"BAC II study: {item.get('id')}"],
                    "graph": solution.get("graph"),
                    "parts": [
                        {
                            "label": p["label"],
                            "want": p.get("want"),
                            "answer_kind": p.get("answer_kind"),
                            "question_km": p.get("question_km"),
                            "question_en": p.get("question_en"),
                            "technique": p.get("technique"),
                            "technique_en": p.get("technique_en"),
                            "answer": str(p["answer_exact"]),
                            "answer_latex": p.get("answer_latex"),
                            "answer_display": p.get("answer_display"),
                            "answer_display_en": p.get("answer_display_en"),
                            "variation_table": p.get("variation_table"),
                            "sign_table": p.get("sign_table"),
                            "monotonicity": p.get("answer_exact") if p.get("want") == "monotonicity" else None,
                            "sign": p.get("answer_exact") if p.get("want") == "sign" else None,
                        }
                        for p in solution.get("parts", [])
                    ],
                    "solution_km": sol_km_text,
                    "solution_km_json": km,
                    "solution_en": solution.get("solution_en"),
                }

            results = await asyncio.gather(*[_resolve_fn_item(item) for item in _FUNCTION_CURATED_TEMPLATES])
            entries = [r for r in results if r is not None]
        else:
            for diff in ("easy", "medium", "hard"):
                variants = [None]
                if topic == "probability" and qt == "probability":
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
    return {"topic": topic, "question_types": question_types}


async def get_template_structures(topic: str | None = None) -> dict:
    """One card per unique template structure: the symbolic slot pattern, one
    deterministic filled sample (prompt + answer), formula tags, and the source
    BAC II exercise labels that map to it. Grouped by topic → question type.

    Pass ``topic=`` to build just that topic (memoized per topic), so the admin
    page can lazy-load topics one at a time instead of paying for all of them
    on first paint."""
    if topic is not None:
        if topic not in generator.TOPICS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown topic: {topic}")
        return {"topics": [await _build_topic_structure_payload(topic)]}

    topics = []
    for t in generator.TOPICS:
        topics.append(await _build_topic_structure_payload(t))
    return {"topics": topics}


async def regenerate_template_structure(structure_id: str) -> dict:
    """Flush cache for a specific structure and re-generate with Gemini in real time."""
    parts = structure_id.split(":")
    topic = parts[0] if parts else "functions"
    if topic == "functions" and len(parts) >= 3:
        item_id = parts[2]
        await cache.delete(f"fn_km:study:{item_id}")
    
    # Invalidate topic cache in memory
    _STRUCTURE_PAYLOAD_CACHE.pop(topic, None)

    payload = await get_template_structures(topic=topic)
    for t in payload.get("topics", []):
        for qt in t.get("question_types", []):
            for st in qt.get("structures", []):
                if st.get("id") == structure_id:
                    return {"structure": st}
    return {"structure": None}


def _topic_structure_summary(topic: str) -> dict:
    """Cheap per-topic rollup (no SymPy solving): question-type counts,
    difficulties, and curated-exercise counts — matches what
    ``_build_topic_structure_payload`` emits. Feeds the admin Overview tab."""
    if topic == "integral":
        qts: dict[str, int] = {}
        diffs: set = set()
        curated = 0
        for s in integral_structures.all_integral_structures():
            qts[s["question_type"]] = qts.get(s["question_type"], 0) + 1
            diffs.add(s.get("difficulty"))
            if s.get("source_labels"):
                curated += 1
        return {
            "topic": topic,
            "question_types": [{"question_type": qt, "count": n} for qt, n in qts.items()],
            "structure_count": sum(qts.values()),
            "difficulties": sorted(diffs),
            "curated": curated,
        }

    if topic == "limit":
        curated_techniques = {
            item["formula_name"] for item in limit_structures._LIMIT_CURATED_TEMPLATES
        }
        diffs = {meta["difficulty"] for meta in limit_structures.LIMIT_TECHNIQUES.values()}
        return {
            "topic": topic,
            "question_types": [{"question_type": "limit", "count": len(limit_structures.LIMIT_TECHNIQUES)}],
            "structure_count": len(limit_structures.LIMIT_TECHNIQUES),
            "difficulties": sorted(diffs),
            "curated": len(curated_techniques),
        }

    if topic == "probability":
        # probability: one card per scenario variant; counting: one per difficulty
        # (mirrors _build_generic_topic_payload, which only fans probability out
        # across scenario variants — counting stays one card per difficulty).
        prob_count = sum(len(scenarios.VARIANT_BY_DIFFICULTY.get(d, ())) for d in ("easy", "medium", "hard"))
        counting_count = len(("easy", "medium", "hard"))
        return {
            "topic": topic,
            "question_types": [
                {"question_type": "probability", "count": prob_count},
                {"question_type": "counting", "count": counting_count},
            ],
            "structure_count": prob_count + counting_count,
            "difficulties": ["easy", "medium", "hard"],
            "curated": 0,
        }

    if topic == "functions":
        items = _FUNCTION_CURATED_TEMPLATES
        diffs = {item.get("difficulty", "hard") for item in items}
        return {
            "topic": topic,
            "question_types": [{"question_type": "study", "count": len(items)}],
            "structure_count": len(items),
            "difficulties": sorted(diffs),
            "curated": len(items),
        }

    if topic in template_shapes.CURATED_SHAPE_TOPICS:
        shapes = template_shapes.shapes_for(topic)
        by_qt: dict[str, int] = {}
        diffs: set = set()
        for s in shapes:
            by_qt[s["question_type"]] = by_qt.get(s["question_type"], 0) + 1
            diffs.add(s.get("difficulty"))
        return {
            "topic": topic,
            "question_types": [{"question_type": qt, "count": n} for qt, n in by_qt.items()],
            "structure_count": len(shapes),
            "difficulties": sorted(d for d in diffs if d),
            "curated": len(shapes),
        }

    # complex: one card per (question type, difficulty), curated labels empty.
    qts = solver.QUESTION_TYPES_BY_TOPIC.get(topic, ())
    return {
        "topic": topic,
        "question_types": [{"question_type": qt, "count": 3} for qt in qts],
        "structure_count": 3 * len(qts),
        "difficulties": ["easy", "medium", "hard"],
        "curated": 0,
    }


async def get_template_summary() -> dict:
    """Admin Overview rollup: per-topic counts computed from the static
    registries (no expensive per-structure SymPy solving)."""
    return {"topics": [_topic_structure_summary(t) for t in generator.TOPICS]}


_EXAM_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "past_exams")

# Fixed params for the two exam questions whose rubric needs numeric inputs
# (q1's box composition, q6's ODE coefficients + initial conditions) — the
# exam's numbers never change, so these mirror engine/topics/past_exam's own
# curated data rather than being derived from student input.
_EXAM_PARAMS = {
    "2018": {
        1: {"white": 2, "red": 4, "blue": 4, "draw": 3},
        3: {"z1_re": "3", "z1_im": "3*sqrt(3)", "z2_re": "sqrt(3)", "z2_im": "1"},
        5: {
            "A": [1, 2, 3], "B": [3, 0, 1], "C": [-1, 0, 1], "D": [2, 1, 2],
            "n": [0, 1, -1], "conic_expr": "(2*x+3*y)**2 - 12*(x*y+3)",
        },
        6: {"b": 4, "c": -5, "ics": {"x0": 0, "y0": 3, "yp0": -3}},
        7: {"expr": "-x+4+log((x+1)/(x-1))", "domain_lo": "1", "tangent_slope": "-5/3"},
    },
}


def _load_exam(exam_id: str) -> dict:
    path = os.path.join(_EXAM_DATA_DIR, f"{exam_id}.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown exam: {exam_id}")
    exams = data.get("exams") or []
    if not exams:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown exam: {exam_id}")
    return exams[0]


# Sub-question labels with no auto-gradable final value (sketches, "show
# that" steps not covered by GRADED_STEPS) — flagged so the frontend can mark
# them self-check-only instead of claiming they count toward the score.
_UNGRADABLE_LABELS = {"ng"}


async def get_exam(exam_id: str) -> dict:
    exam = _load_exam(exam_id)
    sections = []
    for section in exam["sections"]:
        questions = [
            {**q, "gradable": q.get("label") not in _UNGRADABLE_LABELS}
            for q in section.get("questions", section.get("questions_a", []) + section.get("questions_b", []))
        ]
        sections.append({
            "id": section["id"],
            "title_en": section.get("title_en"),
            "title_km": section.get("title_km"),
            "given_en": section.get("given_en"),
            "given_km": section.get("given_km"),
            "given_latex": section.get("given_latex") or section.get("given_latex_b"),
            "questions": questions,
        })
    return {
        "exam_id": exam_id,
        "exam_date": exam.get("exam_date"),
        "duration_minutes": exam.get("duration_minutes"),
        "total_points": exam.get("total_points"),
        "sections": sections,
    }


def _fractions_to_float(obj):
    if isinstance(obj, Fraction):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _fractions_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fractions_to_float(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Admin sandbox: run solve()/analyze_work()/score_work() directly against
# hand-entered params, for debugging a topic/template/formula without going
# through question generation or persisting a Question/Attempt row.
# ---------------------------------------------------------------------------

# Keys that are names/enums, never a math expression — coercing these through
# `parse_answer` would either mangle them (a var name like "x" parses fine
# but "e" would silently become Euler's number) or just fail after wasting a
# parse attempt, so they're passed through untouched.
_SANDBOX_STRING_KEYS = {
    "var", "operation", "op", "formula_name", "kind", "unknown", "fn_name",
    "ask", "variant", "structure", "technique", "curated_technique", "wanted",
    "want", "id", "source_id",
}


def _sandbox_coerce(value, key: str | None = None):
    """Turn one admin-entered sandbox param value into what a solver expects:
    numbers/expressions typed as text (from the calculator keypad) become
    SymPy objects via the same tolerant parser the grader uses on student
    handwriting; known enum/name keys and already-structured values
    (numbers, lists, dicts) pass through as-is."""
    if isinstance(value, str):
        if key in _SANDBOX_STRING_KEYS:
            return value
        try:
            return grader.parse_answer(value)
        except Exception:
            return value
    if isinstance(value, dict):
        return {k: _sandbox_coerce(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_sandbox_coerce(v, key) for v in value]
    return value


def _sandbox_coerce_params(params: dict) -> dict:
    return {k: _sandbox_coerce(v, k) for k, v in (params or {}).items()}


async def sandbox_param_sample(topic: str, question_type: str, difficulty: str = "medium") -> dict:
    """A real generated problem's params for this topic/question_type, as a
    starting point the admin can edit rather than guessing the expected
    shape from scratch — there's no separate param schema anywhere in the
    engine, so a live sample is the only accurate source."""
    if topic not in generator.TOPICS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown topic: {topic}")
    if question_type not in solver.QUESTION_TYPES_BY_TOPIC.get(topic, ()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown question_type: {question_type}")
    try:
        problem = await generator.generate(
            topic, difficulty, seed=random.randint(0, 0xFFFFFFFF),
            question_type=question_type, generation_mode="templates",
        )
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"couldn't generate a sample: {e}")
    return {
        "params": _fractions_to_float(_stringify_sympy(problem.get("params") or {})),
        "prompt": problem.get("prompt"),
        "prompt_latex": problem.get("prompt_latex"),
    }


async def sandbox_structure_sample(topic: str, question_type: str, structure_id: str) -> dict:
    """A fresh, solvable params sample for one *specific* template — chosen
    by the admin from the same structure catalog the Templates tab shows
    (`get_template_structures`), rather than letting the generator pick a
    random technique/variant. Reseeded randomly on every call, so calling it
    again for the same `structure_id` rerolls new coefficients for that same
    template instead of switching templates."""
    if topic not in generator.TOPICS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown topic: {topic}")
    if question_type not in solver.QUESTION_TYPES_BY_TOPIC.get(topic, ()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown question_type: {question_type}")

    seed = random.randint(0, 0xFFFFFFFF)
    try:
        if topic == "limit":
            meta = limit_structures.LIMIT_TECHNIQUES.get(structure_id)
            if meta is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown structure_id: {structure_id}")
            if meta["parameterizable"]:
                problem = generate_limit_for_technique(random.Random(seed), structure_id)
            else:
                pool = [t for t in limit_structures._LIMIT_CURATED_TEMPLATES
                        if t["formula_name"] == structure_id]
                if not pool:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST, f"no curated exercises for technique: {structure_id}"
                    )
                item = random.Random(seed).choice(pool)
                problem = _build_curated_limit(item, meta["difficulty"])
            params, prompt, prompt_latex = problem["params"], problem["prompt"], problem.get("prompt_latex")
        elif topic == "integral":
            struct = integral_structures.structure_by_id(structure_id)
            if struct is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown structure_id: {structure_id}")
            sample = integral_structures.build_sample(struct, seed=seed)
            params, prompt, prompt_latex = sample["params"], sample["prompt"], sample.get("prompt_latex")
        elif topic == "functions":
            item_id = structure_id.split(":", 2)[-1]
            item = next((it for it in _FUNCTION_CURATED_TEMPLATES if it.get("id") == item_id), None)
            if item is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown structure_id: {structure_id}")
            params = {k: v for k, v in item.items()
                      if k not in ("prompt", "prompt_latex", "pattern", "pattern_latex")}
            prompt, prompt_latex = item.get("prompt"), item.get("prompt_latex")
        else:
            parts = structure_id.split(":")
            if len(parts) < 3:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unrecognized structure_id: {structure_id}")
            diff = parts[2]
            variant = parts[3] if len(parts) > 3 else None
            problem = await generator.generate(
                topic, diff, seed=seed, question_type=question_type,
                generation_mode="templates", variant=variant,
            )
            params, prompt, prompt_latex = problem["params"], problem["prompt"], problem.get("prompt_latex")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"couldn't build a sample for {structure_id}: {e}")

    return {
        "params": _fractions_to_float(_stringify_sympy(params or {})),
        "prompt": prompt,
        "prompt_latex": prompt_latex,
    }


def _stringify_sympy(obj):
    """JSON-safe mirror of an admin-sample params dict — SymPy objects (a
    generated `expr`, coefficients that came back as `Rational`, ...) become
    plain strings the admin can re-edit in the sandbox form and that
    `_sandbox_coerce` can parse straight back."""
    try:
        from sympy import Basic
    except ImportError:  # pragma: no cover - sympy always available here
        Basic = ()
    if isinstance(obj, Basic):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _stringify_sympy(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_stringify_sympy(v) for v in obj]
    return obj


def sandbox_solve(topic: str, question_type: str, params: dict) -> dict:
    if topic not in generator.TOPICS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown topic: {topic}")
    if question_type not in solver.QUESTION_TYPES_BY_TOPIC.get(topic, ()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown question_type: {question_type}")
    coerced = _sandbox_coerce_params(params)
    try:
        solution = solver.solve(topic, question_type, coerced)
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"solve() failed: {e}")
    out = solver.serialize(solution)
    out["formula_tags"] = solution.get("formula_tags", [])
    out["checkpoints"] = [
        {"label": cp.get("label"), "value": str(cp.get("value")), "formula": cp.get("formula")}
        for cp in (solution.get("checkpoints") or [])
    ]
    if solution.get("parts"):
        out["parts"] = [
            {
                "label": p.get("label"),
                "answer_exact": str(p.get("answer_exact")),
                "answer_latex": p.get("answer_latex"),
                "answer_kind": p.get("answer_kind"),
            }
            for p in solution["parts"]
        ]
    out["params_used"] = _fractions_to_float(_stringify_sympy(coerced))
    return out


def sandbox_grade(topic: str, question_type: str, params: dict, lines: list[str]) -> dict:
    if topic not in generator.TOPICS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown topic: {topic}")
    if question_type not in solver.QUESTION_TYPES_BY_TOPIC.get(topic, ()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown question_type: {question_type}")
    coerced = _sandbox_coerce_params(params)
    work = [ln for ln in lines if ln.strip()]
    try:
        step_check = grader.analyze_work(topic, question_type, coerced, work)
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"analyze_work() failed: {e}")
    result: dict = {"step_check": step_check}
    if topic != "functions":
        try:
            rubric_result = score_work(topic, question_type, coerced, work, question_points=10)
            result["rubric_score"] = _fractions_to_float(rubric_result)
        except Exception as e:
            result["rubric_error"] = str(e)
    else:
        try:
            result["graph_check"] = grader.grade_graph_check(coerced, work)
        except Exception as e:
            result["graph_check_error"] = str(e)
    return result


async def submit_exam(exam_id: str, answers: dict[str, str]) -> dict:
    _load_exam(exam_id)  # 404s on an unknown exam_id before grading
    params_by_question = _EXAM_PARAMS.get(exam_id, {})
    lines_by_question = {
        int(q_no): text.split("\n") for q_no, text in answers.items() if text.strip()
    }
    result = mark_full_exam(exam_id, params_by_question, lines_by_question)
    return _fractions_to_float(result)


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


# ---------------------------------------------------------------------------
# Skill tracking & the student profile
#
# Every graded attempt updates two hidden trackers (`SkillState` rows): one for
# the *exercise type* the question belongs to (a leaf skill from
# engine.core.skills — "sin(x)/x limits", not "limits") and one per *formula*
# the step-checker watched. `get_profile` reads both back as progress bars plus
# a ranked list of what to practise next. `engine.core.mastery` owns the
# scoring formula; `engine.core.coaching` owns the suggestion rules.
# ---------------------------------------------------------------------------


def _difficulty_of(question) -> str:
    return question.difficulty if question.difficulty in ("easy", "medium", "hard") else "medium"


def _formula_events(correct: bool, step_check: dict | None):
    """(formula_tag, score) pairs for one attempt's checkpoint breakdown.

    A checkpoint the student reached is evidence they can execute that step. A
    checkpoint they *missed* only counts against them when the final answer was
    also wrong: the step-check runs on correct attempts too, and a correct
    answer found by a valid alternative route legitimately skips the standard
    path's checkpoints. Counting those as misses would invent weaknesses (the
    same false-miss rule `get_stats`' by_formula uses).
    """
    for item in (step_check or {}).get("formula_breakdown") or []:
        fid = item.get("formula")
        if not fid:
            continue
        if item.get("reached"):
            yield fid, 1.0
        elif not correct:
            yield fid, 0.0


def _days_between(earlier, later) -> float:
    """Days between two timestamps, tolerating a naive one (an older row
    written before the column carried a timezone) by reading it as UTC."""
    if earlier is None or later is None:
        return 0.0
    if (earlier.tzinfo is None) != (later.tzinfo is None):
        earlier = earlier.replace(tzinfo=timezone.utc) if earlier.tzinfo is None else earlier
        later = later.replace(tzinfo=timezone.utc) if later.tzinfo is None else later
    return max(0.0, (later - earlier).total_seconds() / 86400.0)


def _apply_event(state: SkillState, score: float, correct: bool, at) -> None:
    """Fold one scored event into a SkillState row, in place."""
    state.w_total, state.w_correct, state.evidence = mastery.apply_attempt(
        state.w_total, state.w_correct, state.evidence, score,
        days_since_last=_days_between(state.last_seen_at, at),
    )
    state.attempts += 1
    state.correct += 1 if correct else 0
    state.streak = state.streak + 1 if correct else 0
    state.best_streak = max(state.best_streak, state.streak)
    state.last_score = float(score)
    state.last_seen_at = at
    state.tracker_version = mastery.TRACKER_VERSION


async def _skill_states(db, user, keys_by_kind: dict[str, set[str]]) -> dict[tuple[str, str], SkillState]:
    """Load (and create, unflushed) the SkillState rows for the given keys."""
    wanted = {(kind, key) for kind, keys in keys_by_kind.items() for key in keys}
    if not wanted:
        return {}
    def _blank(kind, key):
        topic = skills.resolve(key)["topic"] if kind == "exercise" else formulas.resolve_formula(key).get("group")
        return {
            "user_id": user.id, "kind": kind, "skill_key": key, "topic": topic,
            "w_total": 0.0, "w_correct": 0.0, "evidence": 0.0,
            "attempts": 0, "correct": 0, "streak": 0, "best_streak": 0,
            "tracker_version": mastery.TRACKER_VERSION,
        }

    # Insert-if-missing before reading, rather than adding ORM objects for the
    # keys a SELECT didn't find: two grade requests racing on the same
    # brand-new skill (a double-clicked submit, or two parts of one exercise)
    # would otherwise both create the row and the second commit would fail the
    # unique constraint, losing the attempt with it.
    await db.execute(
        pg_insert(SkillState)
        .values([_blank(kind, key) for kind, key in sorted(wanted)])
        .on_conflict_do_nothing(constraint="uq_skill_state_user_kind_key")
    )
    rows = (
        await db.scalars(
            select(SkillState).where(
                SkillState.user_id == user.id,
                SkillState.kind.in_({k for k, _ in wanted}),
                SkillState.skill_key.in_({k for _, k in wanted}),
            )
        )
    ).all()
    return {(r.kind, r.skill_key): r for r in rows if (r.kind, r.skill_key) in wanted}


async def record_skill_progress(db, user, question, attempt, at=None) -> None:
    """Update the student's hidden trackers from one graded attempt.

    Called from `grade_question` before the commit, so the attempt and the
    progress it produced land in the same transaction. Deliberately total:
    every topic feeds the same two trackers, so a new topic needs no wiring
    here beyond appearing in the skill catalog.
    """
    skill_key = skills.skill_key_for(question.topic, question.question_type, question.spec)
    step_check = attempt.step_check
    score = mastery.attempt_score(
        attempt.correct,
        difficulty=_difficulty_of(question),
        partial=mastery.partial_from_grade(step_check),
        hints_used=attempt.hints_used or 0,
    )
    events = list(_formula_events(attempt.correct, step_check))
    states = await _skill_states(db, user, {
        "exercise": {skill_key},
        "formula": {fid for fid, _ in events},
    })
    at = at or datetime.now(timezone.utc)

    _apply_event(states[("exercise", skill_key)], score, attempt.correct, at)
    for fid, formula_score in events:
        _apply_event(states[("formula", fid)], formula_score, formula_score >= 1.0, at)


async def rebuild_skill_states(db, user) -> int:
    """Recompute every tracker for one student by replaying their attempts.

    Used to backfill students who practised before tracking existed, and to
    migrate rows whenever `mastery.TRACKER_VERSION` changes — the scoring rules
    are a moving target early on, and mixing two scales in one average would be
    worse than recomputing. Because every input (`correct`, difficulty,
    `step_check`, `hints_used`, timestamps) is persisted on the attempt, the
    replay reproduces exactly what live recording would have written.
    """
    await db.execute(delete(SkillState).where(SkillState.user_id == user.id))
    rows = (
        await db.execute(
            select(Attempt, Question)
            .join(Question, Attempt.question_id == Question.id)
            .where(Attempt.user_id == user.id)
            .order_by(Attempt.created_at, Attempt.id)
        )
    ).all()
    states: dict[tuple[str, str], SkillState] = {}

    def _state(kind, key):
        existing = states.get((kind, key))
        if existing is not None:
            return existing
        topic = skills.resolve(key)["topic"] if kind == "exercise" else formulas.resolve_formula(key).get("group")
        created = SkillState(
            user_id=user.id, kind=kind, skill_key=key, topic=topic,
            w_total=0.0, w_correct=0.0, evidence=0.0,
            attempts=0, correct=0, streak=0, best_streak=0,
            tracker_version=mastery.TRACKER_VERSION,
        )
        db.add(created)
        states[(kind, key)] = created
        return created

    for attempt, question in rows:
        at = attempt.created_at or datetime.now(timezone.utc)
        skill_key = skills.skill_key_for(question.topic, question.question_type, question.spec)
        score = mastery.attempt_score(
            attempt.correct,
            difficulty=_difficulty_of(question),
            partial=mastery.partial_from_grade(attempt.step_check),
            hints_used=attempt.hints_used or 0,
        )
        _apply_event(_state("exercise", skill_key), score, attempt.correct, at)
        for fid, formula_score in _formula_events(attempt.correct, attempt.step_check):
            _apply_event(_state("formula", fid), formula_score, formula_score >= 1.0, at)

    await db.commit()
    return len(rows)


async def _ensure_skill_states(db, user) -> None:
    """Backfill or migrate the trackers before reading them.

    Rebuilds when the student has attempts but no tracker rows (they practised
    before this feature shipped) or when any row predates the current scoring
    rules.
    """
    stale = await db.scalar(
        select(func.count()).select_from(SkillState).where(
            SkillState.user_id == user.id,
            SkillState.tracker_version != mastery.TRACKER_VERSION,
        )
    ) or 0
    if stale:
        await rebuild_skill_states(db, user)
        return
    tracked = await db.scalar(
        select(func.count()).select_from(SkillState).where(SkillState.user_id == user.id)
    ) or 0
    if tracked:
        return
    attempted = await db.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.user_id == user.id)
    ) or 0
    if attempted:
        await rebuild_skill_states(db, user)


def _skill_view(meta: dict, row: SkillState | None, now) -> dict:
    """One leaf skill as the profile shows it: the catalog metadata, the raw
    counters a student can check against their own memory, and the estimate."""
    days_idle = _days_between(row.last_seen_at, now) if row else 0.0
    est = mastery.estimate(
        row.w_total if row else 0.0,
        row.w_correct if row else 0.0,
        row.evidence if row else 0.0,
        days_since_last=days_idle,
    )
    return {
        **est,
        "key": meta["key"],
        "topic": meta["topic"],
        "topic_label": meta["topic_label"],
        "question_type": meta["question_type"],
        "variant": meta["variant"],
        "label": meta["label"],
        "difficulty": meta["difficulty"],
        "practice": meta["practice"],
        "forceable": meta["forceable"],
        "attempts": row.attempts if row else 0,
        "correct": row.correct if row else 0,
        "streak": row.streak if row else 0,
        "best_streak": row.best_streak if row else 0,
        "days_idle": round(days_idle, 1),
        "last_seen_at": row.last_seen_at.isoformat() if row and row.last_seen_at else None,
        "status": mastery.status(est),
        "band": mastery.band(est["level"]),
        "weak_formulas": [],
    }


def _formula_view(fid: str, row: SkillState, now) -> dict:
    entry = formulas.resolve_formula(fid)
    days_idle = _days_between(row.last_seen_at, now)
    est = mastery.estimate(row.w_total, row.w_correct, row.evidence, days_since_last=days_idle)
    return {
        **est,
        "formula": fid,
        "name": entry.get("name_en") or fid.replace("_", " "),
        "latex": entry.get("latex"),
        "topic": entry.get("group"),
        "topic_label": skills.TOPIC_LABELS.get(entry.get("group"), entry.get("group")),
        "attempts": row.attempts,
        "correct": row.correct,
        "days_idle": round(days_idle, 1),
        "status": mastery.status(est),
        "skill_key": None,
    }


async def _link_formulas_to_skills(skill_views: list[dict], formula_views: list[dict]) -> None:
    """Attach a practisable skill to each weak formula, and the weak formulas
    to each weak skill, using the generator's formula<->variant indexes.

    Only runs when there is something weak to explain: building those indexes
    samples one question per variant, and an already-strong profile shouldn't
    pay for it.
    """
    weak_skills = [s for s in skill_views if coaching.is_weak_skill(s)]
    weak_formulas = [f for f in formula_views if coaching.is_weak_formula(f)]
    if not weak_skills and not weak_formulas:
        return
    try:
        for f in weak_formulas:
            refs = await generator.variants_for_formula(f["formula"])
            if refs:
                ref = refs[0]
                f["skill_key"] = skills.make_key(ref["topic"], ref["question_type"], ref["variant"])
        by_formula = {f["formula"]: f for f in formula_views}
        for s in weak_skills:
            tags = await generator.formulas_for_skill(s["key"])
            missed = [by_formula[t] for t in tags if t in by_formula and coaching.is_weak_formula(by_formula[t])]
            missed.sort(key=lambda f: f["ability"])
            s["weak_formulas"] = [
                {"formula": f["formula"], "name": f["name"], "level": f["level"]} for f in missed[:3]
            ]
    except Exception:
        # A generator hiccup must never cost the student their profile — the
        # scores are all still valid, only the "why" annotations are missing.
        pass


async def _activity(db, user, days: int = 14) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    rows = await db.execute(
        select(
            func.date(Attempt.created_at).label("day"),
            func.count().label("attempts"),
            func.sum(case((Attempt.correct.is_(True), 1), else_=0)).label("correct"),
        )
        .where(Attempt.user_id == user.id, Attempt.created_at >= since)
        .group_by(func.date(Attempt.created_at))
        .order_by(func.date(Attempt.created_at))
    )
    return [
        {"date": str(day), "attempts": total, "correct": int(ok or 0)}
        for day, total, ok in rows.all()
    ]


async def get_profile(db, user) -> dict:
    """The student's profile: one overall skill level, a bar per topic, every
    leaf skill's estimate, the formula-level weak spots, and a ranked list of
    what to practise next.

    The single headline number is the mean of `ability x confidence` across
    every leaf skill of the topics the student has actually started — so it
    rises both by getting better at what they practise and by covering more of
    each topic, and it can't be filled by repeating one easy exercise. See
    `engine.core.mastery` for the derivation.
    """
    await _ensure_skill_states(db, user)
    now = datetime.now(timezone.utc)

    rows = (await db.scalars(select(SkillState).where(SkillState.user_id == user.id))).all()
    exercise_rows = {r.skill_key: r for r in rows if r.kind == "exercise"}
    formula_rows = {r.skill_key: r for r in rows if r.kind == "formula"}

    catalog_keys = {s["key"] for s in skills.SKILLS}
    skill_views = [_skill_view(s, exercise_rows.get(s["key"]), now) for s in skills.SKILLS]
    # Progress recorded against a skill the catalog has since dropped still
    # belongs to the student — show it rather than silently losing it.
    skill_views += [
        _skill_view(skills.resolve(key), row, now)
        for key, row in exercise_rows.items() if key not in catalog_keys
    ]
    formula_views = sorted(
        (_formula_view(fid, row, now) for fid, row in formula_rows.items()),
        key=lambda f: (f["ability"], -f["attempts"]),
    )
    await _link_formulas_to_skills(skill_views, formula_views)

    topics = {}
    for topic in skills.practice_topics() + [t for t in skills.NON_PRACTICE_TOPICS]:
        views = [s for s in skill_views if s["topic"] == topic]
        if not views:
            continue
        agg = mastery.aggregate(views, total_skills=len(views))
        practised = [s for s in views if s["evidence"] > 0]
        strongest = max(practised, key=lambda s: s["level"], default=None)
        weakest = min(practised, key=lambda s: s["level"], default=None)
        topics[topic] = {
            **agg,
            "topic": topic,
            "label": skills.TOPIC_LABELS.get(topic, topic.replace("_", " ").capitalize()),
            "practice": topic not in skills.NON_PRACTICE_TOPICS,
            "engaged": bool(practised),
            "skills_total": len(views),
            "skills_practised": len(practised),
            "attempts": sum(s["attempts"] for s in views),
            "correct": sum(s["correct"] for s in views),
            "strongest": strongest["key"] if strongest else None,
            "weakest": weakest["key"] if weakest else None,
        }

    engaged = [t for t, v in topics.items() if v["practice"] and v["engaged"]]
    # The headline is measured over the whole practisable syllabus, so
    # `score` (ability on what's been practised) and `syllabus_score`
    # (the same spread over everything) are two views of one number.
    practice_views = [s for s in skill_views if s["practice"]]
    overall = mastery.aggregate(practice_views, total_skills=len(practice_views))

    total_attempts = sum(s["attempts"] for s in skill_views)
    total_correct = sum(s["correct"] for s in skill_views)

    suggestions = coaching.build_suggestions(skill_views, formula_views, topics)
    for s in suggestions:
        s["target"] = skills.practice_target(s["skill_key"]) if s["skill_key"] else None

    return {
        "user": {"id": str(user.id), "email": user.email, "plan": user.plan,
                 "member_since": user.created_at.isoformat() if user.created_at else None},
        "level": {
            **overall,
            "attempts": total_attempts,
            "correct": total_correct,
            "accuracy": round(total_correct / total_attempts, 4) if total_attempts else 0.0,
            "topics_started": len(engaged),
            "topics_total": len(skills.practice_topics()),
        },
        "topics": sorted(topics.values(), key=lambda t: (not t["practice"], -t["score"], t["label"])),
        "skills": skill_views,
        "formulas": formula_views,
        "suggestions": suggestions,
        "activity": await _activity(db, user),
    }
