from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from engine import explainer, generator, grader, solver

app = FastAPI(title="BACII Math Engine", version="0.1.0")


class GenerateRequest(BaseModel):
    topic: str = "complex"
    difficulty: str = "medium"
    question_type: Optional[str] = None
    seed: Optional[int] = None
    generation_mode: str = "templates"


class ProblemRef(BaseModel):
    question_type: str
    a: int
    b: int


class GradeRequest(ProblemRef):
    user_answer: str
    tolerance: Optional[float] = None


class ExplainRequest(ProblemRef):
    use_ai: bool = False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/problems/generate")
def generate(req: GenerateRequest):
    return generator.generate(req.difficulty, req.seed, req.question_type, req.generation_mode)


@app.post("/solve")
def solve(req: ProblemRef):
    return solver.serialize(solver.solve(req.question_type, req.a, req.b))


@app.post("/grade")
def grade(req: GradeRequest):
    return grader.grade(req.question_type, req.a, req.b, req.user_answer, req.tolerance)


@app.post("/explain")
def explain(req: ExplainRequest):
    return explainer.explain(req.question_type, req.a, req.b, req.use_ai)
