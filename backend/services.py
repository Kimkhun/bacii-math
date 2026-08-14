import uuid

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

import cache
from engine import explainer, generator, grader, llm, solver
from models import Attempt, Explanation, Question, Step, User
from schemas import GenerateRequest


async def create_question(db: AsyncSession, req: GenerateRequest) -> dict:
    problem = await generator.generate(req.difficulty, req.seed, req.question_type, req.generation_mode)
    solution = solver.solve(problem["question_type"], problem["a"], problem["b"])

    question = Question(
        topic=problem["topic"],
        question_type=problem["question_type"],
        difficulty=problem["difficulty"],
        spec={"a": problem["a"], "b": problem["b"]},
        prompt=problem["prompt"],
        z_display=problem["z_display"],
        expected_answer=str(solution["answer_exact"]),
        expected_decimal=solution["answer_decimal"] if isinstance(solution["answer_decimal"], float) else None,
        source=problem["source"],
    )
    db.add(question)
    await db.flush()

    for i, s in enumerate(solution["steps"], 1):
        db.add(Step(question_id=question.id, step_order=i, title=s["title"], detail=s["detail"]))

    await db.commit()
    return {
        "id": question.id,
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "a": problem["a"],
        "b": problem["b"],
        "prompt": question.prompt,
        "z_display": question.z_display,
        "source": question.source,
    }


def _steps_text(question: Question) -> str:
    a = question.spec["a"]
    b = question.spec["b"]
    solution = solver.solve(question.question_type, a, b)
    return explainer.build_text(question.question_type, a, b, solution)


async def _build_explanation(db, user, question, attempt_id, trigger, use_ai, steps_text=None, allow_gemini=None) -> dict:
    steps_text = steps_text or _steps_text(question)
    content = steps_text
    provider = "deterministic"
    intervened = False

    if use_ai:
        key = f"explain:{question.question_type}:{question.spec['a']}:{question.spec['b']}"
        cached = await cache.get_explanation(key)
        if cached:
            content, provider, intervened = cached, "gemini", True
        else:
            if allow_gemini is None:
                allow_gemini = await cache.allow_gemini(str(user.id))
            text, got_provider = await llm.narrate(steps_text, allow_gemini=allow_gemini)
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


async def grade_question(db, user, question_id, user_answer, work_text=None) -> dict:
    question = await db.get(Question, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")

    result = grader.grade(question.question_type, question.spec["a"], question.spec["b"], user_answer)
    attempt = Attempt(
        user_id=user.id,
        question_id=question.id,
        user_answer=user_answer,
        parsed_answer=result.get("given"),
        correct=result["correct"],
        reason=result["reason"],
    )
    db.add(attempt)
    await db.flush()

    resp = {
        "attempt_id": attempt.id,
        "correct": result["correct"],
        "reason": result["reason"],
        "given": result.get("given"),
        "expected": result["expected"],
    }

    if not result["correct"]:
        steps_text = _steps_text(question)
        allowed = await cache.allow_gemini(str(user.id))
        resp["explanation"] = await _build_explanation(
            db, user, question, attempt.id, "incorrect", use_ai=True, steps_text=steps_text, allow_gemini=allowed
        )
        step_check = None
        if work_text:
            step_check = grader.analyze_work(
                question.question_type, question.spec["a"], question.spec["b"], work_text.split("\n")
            )
            resp["step_check"] = step_check
        check, provider = await llm.check_work(
            question.prompt, work_text or user_answer, steps_text, str(question.expected_answer),
            allow_gemini=allowed, step_check=step_check,
        )
        if check:
            resp["work_check"] = {"content": check, "provider": provider}

    await db.commit()
    return resp


async def explain_question(db, user, question_id, user_answer=None, work_text=None) -> dict:
    question = await db.get(Question, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    steps_text = _steps_text(question)
    result = await _build_explanation(db, user, question, None, "manual", use_ai=True, steps_text=steps_text)
    if user_answer:
        allowed = await cache.allow_gemini(str(user.id))
        step_check = None
        if work_text:
            step_check = grader.analyze_work(
                question.question_type, question.spec["a"], question.spec["b"], work_text.split("\n")
            )
            result["step_check"] = step_check
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
    steps = [{"step_order": s.step_order, "title": s.title, "detail": s.detail} for s in rows.scalars()]
    return {
        "id": question.id,
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "prompt": question.prompt,
        "z_display": question.z_display,
        "source": question.source,
        "steps": steps,
    }


async def list_attempts(db, user, limit=50) -> list:
    rows = await db.execute(
        select(Attempt).where(Attempt.user_id == user.id).order_by(Attempt.created_at.desc()).limit(limit)
    )
    return [
        {
            "id": a.id,
            "question_id": a.question_id,
            "user_answer": a.user_answer,
            "correct": a.correct,
            "reason": a.reason,
            "created_at": a.created_at,
        }
        for a in rows.scalars()
    ]


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

    return {
        "total_attempts": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "by_topic": by_topic,
    }
