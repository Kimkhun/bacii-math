import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import services
from core.deps import get_current_admin_user, get_current_user, get_db
from models import User
from schemas import (
    ExamSubmitRequest, ExplainRequest, GenerateRequest, GradeGraphRequest, GradeRequest, ReplayRequest,
    SandboxGradeRequest, SandboxSolveRequest, SaveProgressRequest,
)

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
        db, user, req.question_id, req.user_answer, req.work_text, req.lines_boxes, req.part, req.hints_used,
        req.strokes, req.strokes_thumb, lang=req.lang
    )


@router.post("/grade-graph")
async def grade_graph(
    req: GradeGraphRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.grade_graph_drawing(db, user, req.question_id, req.strokes_thumb)


@router.get("/exam/{exam_id}")
async def get_exam(exam_id: str, user: User = Depends(get_current_user)):
    return await services.get_exam(exam_id)


@router.post("/exam/{exam_id}/submit")
async def submit_exam(exam_id: str, req: ExamSubmitRequest, user: User = Depends(get_current_user)):
    return await services.submit_exam(exam_id, req.answers)


@router.post("/explain")
async def explain(
    req: ExplainRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.explain_question(db, user, req.question_id, req.user_answer, req.work_text, lang=req.lang)


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


@router.get("/km-solution/{question_id}")
async def km_solution(
    question_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.km_solution_for_question(db, user, question_id)


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
async def templates(user: User = Depends(get_current_admin_user), db: AsyncSession = Depends(get_db)):
    return await services.get_template_inventory()


@me_router.get("/templates/structures")
async def template_structures(
    topic: str | None = None,
    user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_template_structures(topic=topic)


@me_router.get("/templates/summary")
async def template_summary(user: User = Depends(get_current_admin_user), db: AsyncSession = Depends(get_db)):
    return await services.get_template_summary()


@me_router.post("/templates/structures/regenerate")
async def regenerate_template_structure(
    req: dict,
    user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    structure_id = req.get("structure_id")
    if not structure_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "structure_id is required")
    return await services.regenerate_template_structure(structure_id)


@me_router.get("/sandbox/sample")
async def sandbox_sample(
    topic: str,
    question_type: str,
    difficulty: str = "medium",
    user: User = Depends(get_current_admin_user),
):
    return await services.sandbox_param_sample(topic, question_type, difficulty)


@me_router.get("/sandbox/structure-sample")
async def sandbox_structure_sample(
    topic: str,
    question_type: str,
    structure_id: str,
    user: User = Depends(get_current_admin_user),
):
    return await services.sandbox_structure_sample(topic, question_type, structure_id)


@me_router.post("/sandbox/solve")
async def sandbox_solve(
    req: SandboxSolveRequest,
    user: User = Depends(get_current_admin_user),
):
    return services.sandbox_solve(req.topic, req.question_type, req.params)


@me_router.post("/sandbox/grade")
async def sandbox_grade(
    req: SandboxGradeRequest,
    user: User = Depends(get_current_admin_user),
):
    return services.sandbox_grade(req.topic, req.question_type, req.params, req.lines.split("\n"))
