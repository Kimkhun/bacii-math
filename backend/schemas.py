import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    plan: str = "free"
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class GenerateRequest(BaseModel):
    topic: str = "complex"
    difficulty: str = "medium"
    question_type: str | None = None
    generation_mode: str = "templates"
    seed: int | None = None


class GradeRequest(BaseModel):
    question_id: uuid.UUID
    user_answer: str
    work_text: str | None = None
    lines_boxes: list | None = None
    part: str | None = None


class ExplainRequest(BaseModel):
    question_id: uuid.UUID
    user_answer: str | None = None
    work_text: str | None = None


class ReplayRequest(BaseModel):
    question_id: uuid.UUID
