"""Student profile: skill level, per-topic progress, and what to practise next.

Thin HTTP layer over `services.get_profile` / `services.rebuild_skill_states`,
following the same shape as the other `me_router` endpoints (unprefixed paths,
current-user scoped).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import services
from core.deps import get_current_user, get_db
from engine.core import skills
from models import User

router = APIRouter(tags=["profile"])


@router.get("/profile")
async def profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await services.get_profile(db, user)


@router.post("/profile/rebuild")
async def rebuild_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Recompute this student's trackers from their attempt history. Normally
    unnecessary (reads self-heal), but useful after tuning the scoring rules."""
    replayed = await services.rebuild_skill_states(db, user)
    return {"rebuilt": True, "attempts_replayed": replayed}


@router.get("/skills")
async def skill_catalog(user: User = Depends(get_current_user)):
    """The full skill taxonomy — every practisable exercise type per topic,
    independent of any one student's progress."""
    return {"topics": skills.practice_topics(), "labels": skills.TOPIC_LABELS, "skills": skills.SKILLS}
