import base64

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from engine import vision
from models import User

router = APIRouter(prefix="/vision", tags=["vision"])


# Canvas exports are well under 1 MB; refuse anything absurd before decoding.
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class DetectRequest(BaseModel):
    image_base64: str


@router.post("/detect")
async def detect(
    req: DetectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if len(req.image_base64) > MAX_IMAGE_BYTES * 4 // 3 + 8:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "image too large")
    try:
        data = base64.b64decode(req.image_base64)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid base64 image")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty image")
    try:
        return await vision.detect_math(data, user_id=user.id)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"vision detection failed: {exc}")
