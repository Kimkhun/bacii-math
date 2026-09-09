import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(20), nullable=False, server_default="free")
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    topic: Mapped[str] = mapped_column(String(50))
    question_type: Mapped[str] = mapped_column(String(50))
    difficulty: Mapped[str] = mapped_column(String(20))
    spec: Mapped[dict] = mapped_column(JSONB)
    prompt: Mapped[str] = mapped_column(Text)
    prompt_latex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    z_display: Mapped[str] = mapped_column(String(100))
    expected_answer: Mapped[str] = mapped_column(String(255))
    expected_decimal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(20))
    formula_tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text)
    formula: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    user_answer: Mapped[str] = mapped_column(Text)
    parsed_answer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    correct: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(Text)
    work_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    step_check: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    lines_boxes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    formula_breakdown: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    strokes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    strokes_thumb: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Explanation(Base):
    __tablename__ = "explanations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), nullable=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    intervened: Mapped[bool] = mapped_column(Boolean)
    trigger: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SkillState(Base):
    """The hidden per-student tracker behind the profile progress bars.

    One row per (user, kind, skill_key): ``kind="exercise"`` rows track a leaf
    skill from ``engine.core.skills`` (a technique like `sin(x)/x` limits, not
    a whole topic), ``kind="formula"`` rows track one formula/technique id from
    the step-check's ``formula_breakdown``. Both are updated on every graded
    attempt and read back by ``services.get_profile``.

    ``w_total``/``w_correct`` are the recency-weighted EMA weights and
    ``evidence`` the (unbounded, time-decayed) amount of proof — see
    ``engine.core.mastery`` for what they mean and how they roll up. The raw
    ``attempts``/``correct`` counters are kept alongside purely for display,
    since a student reads "12 of 15 right" more easily than an EMA.

    ``tracker_version`` records which revision of the scoring rules wrote the
    row, so a change to those rules replays the attempt history rather than
    silently mixing two scales.
    """

    __tablename__ = "skill_states"
    __table_args__ = (UniqueConstraint("user_id", "kind", "skill_key", name="uq_skill_state_user_kind_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, server_default="exercise")
    skill_key: Mapped[str] = mapped_column(String(120), nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    w_total: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    w_correct: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    evidence: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    correct: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    streak: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    best_streak: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tracker_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StudySession(Base):
    """A student's saved progress through one multi-part exercise: which parts
    are answered/typed, the OCR'd work per part, and the correct flags. One row
    per (user, question) — upserted on every grade (auto-save) and on the
    explicit 'Save progress' button so long exercises can be resumed later."""

    __tablename__ = "study_sessions"
    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_study_session_user_question"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), server_default="in_progress")
    state: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
