import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import services
from core.deps import get_current_user, get_db
from models import User
from schemas import ExplainRequest, GenerateRequest, GradeRequest

router = APIRouter(prefix="/problems", tags=["problems"])
me_router = APIRouter(tags=["history"])


@router.post("/generate")
async def generate(
    req: GenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.create_question(db, req)


@router.post("/grade")
async def grade(
    req: GradeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.grade_question(db, user, req.question_id, req.user_answer)


@router.post("/explain")
async def explain(
    req: ExplainRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.explain_question(db, user, req.question_id, req.user_answer)


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


@me_router.get("/stats")
async def stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await services.get_stats(db, user)
