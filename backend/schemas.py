import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# A pragmatic email shape check (not full RFC): keeps obvious garbage out
# without pulling in the email-validator dependency.
_EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

# Upper bounds on free-text fields that get persisted. Generous for real work,
# but they stop a single request from writing megabytes into the database.
_MAX_ANSWER = 2_000
_MAX_WORK = 20_000
_MAX_THUMB = 3_000_000  # base64 data-URI of a small canvas thumbnail


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=_EMAIL_RE)
    # bcrypt only uses the first 72 bytes; require a real password, cap the rest.
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    plan: str = "free"
    is_admin: bool = False
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
    # Sub-category within question_type — e.g. a limit technique
    # (factoring_0_0, conjugate_infinity, ...) or a probability scenario id.
    # Ignored by topics/question_types that don't have this extra axis.
    variant: str | None = None
    # No `lang` here: generation is language-neutral (SymPy builds the problem,
    # the web client renders the statement in the student's language). Grading
    # and explanation do take `lang` because those produce prose.


class GradeRequest(BaseModel):
    question_id: uuid.UUID
    user_answer: str = Field(max_length=_MAX_ANSWER)
    work_text: str | None = Field(default=None, max_length=_MAX_WORK)
    lines_boxes: list | None = None
    part: str | None = Field(default=None, max_length=64)
    hints_used: int = Field(default=0, ge=0, le=1000)
    strokes: dict | None = None
    strokes_thumb: str | None = Field(default=None, max_length=_MAX_THUMB)
    lang: str = "en"


class SandboxSolveRequest(BaseModel):
    topic: str
    question_type: str
    params: dict = {}


class SandboxGradeRequest(BaseModel):
    topic: str
    question_type: str
    params: dict = {}
    lines: str = ""


class GradeGraphRequest(BaseModel):
    question_id: uuid.UUID
    strokes_thumb: str = Field(max_length=_MAX_THUMB)


class ExplainRequest(BaseModel):
    question_id: uuid.UUID
    user_answer: str | None = Field(default=None, max_length=_MAX_ANSWER)
    work_text: str | None = Field(default=None, max_length=_MAX_WORK)
    lang: str = "en"
    # Links the stored explanation to a graded attempt (shows up in history).
    attempt_id: uuid.UUID | None = None
    # Sub-part label for multi-part exercises graded progressively.
    part: str | None = None


class HintRequest(BaseModel):
    question_id: uuid.UUID
    part: str | None = Field(default=None, max_length=64)
    user_answer: str | None = Field(default=None, max_length=_MAX_ANSWER)
    work_text: str | None = Field(default=None, max_length=_MAX_WORK)
    lang: str = "km"


class ReplayRequest(BaseModel):
    question_id: uuid.UUID


class ExamSubmitRequest(BaseModel):
    # {question_no (as string, "1".."7"): student's raw work, one asserted
    # fact per line} — a question the student left blank may be omitted.
    answers: dict[str, str] = {}

    @field_validator("answers")
    @classmethod
    def _bounded(cls, v: dict[str, str]) -> dict[str, str]:
        if len(v) > 50 or sum(len(k) + len(val) for k, val in v.items()) > _MAX_WORK:
            raise ValueError("submission too large")
        return v


class SaveProgressRequest(BaseModel):
    question_id: uuid.UUID
    part: str | None = Field(default=None, max_length=64)
    typed: str | None = Field(default=None, max_length=_MAX_ANSWER)
    work_text: str | None = Field(default=None, max_length=_MAX_WORK)
    lines_boxes: list | None = None
    strokes: dict | None = None
    strokes_thumb: str | None = Field(default=None, max_length=_MAX_THUMB)
