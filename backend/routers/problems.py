import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import services
from core.deps import get_current_user, get_db
from models import User
from schemas import ExplainRequest, GenerateRequest, GradeRequest, ReplayRequest, SaveProgressRequest

router = APIRouter(prefix="/problems", tags=["problems"])
me_router = APIRouter(tags=["history"])


@router.post("/generate")
async def generate(
    req: GenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await services.create_question(db, req)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.post("/replay")
async def replay(
    req: ReplayRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.recreate_question(db, user, req.question_id)


@router.post("/grade")
async def grade(
    req: GradeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.grade_question(
        db, user, req.question_id, req.user_answer, req.work_text, req.lines_boxes, req.part, req.hints_used
    )


@router.post("/explain")
async def explain(
    req: ExplainRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.explain_question(db, user, req.question_id, req.user_answer, req.work_text)


@router.post("/progress/save")
async def save_progress(
    req: SaveProgressRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.save_progress(db, user, req)


@router.get("/{question_id}")
async def get_question(
    question_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_question(db, question_id)


@me_router.get("/attempts")
async def attempts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await services.list_attempts(db, user)


@me_router.get("/attempts/{attempt_id}")
async def attempt_detail(
    attempt_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_attempt(db, user, attempt_id)


@me_router.get("/stats")
async def stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await services.get_stats(db, user)


@me_router.get("/progress")
async def progress_list(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await services.list_progress(db, user)


@me_router.get("/progress/{session_id}")
async def progress_detail(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_progress(db, user, session_id)


@me_router.delete("/progress/{session_id}")
async def progress_delete(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.delete_progress(db, user, session_id)


@me_router.get("/formulas")
async def formulas(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await services.get_formulas_catalog()


@me_router.get("/templates")
async def templates(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await services.get_template_inventory()


@me_router.get("/templates/structures")
async def template_structures(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await services.get_template_structures()
