import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import security
from core.deps import get_current_user, get_db
from models import User
from schemas import LoginRequest, RefreshRequest, TokenPair, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair(user_id: uuid.UUID) -> TokenPair:
    return TokenPair(
        access_token=security.create_access_token(user_id),
        refresh_token=security.create_refresh_token(user_id),
    )


@router.post("/signup")
async def signup(body: UserCreate, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    if await db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=email, hashed_password=security.hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"user": UserOut.model_validate(user), **_token_pair(user.id).model_dump()}


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not security.verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return {"user": UserOut.model_validate(user), **_token_pair(user.id).model_dump()}


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    try:
        payload = security.decode_token(body.refresh_token, expected_type="refresh")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    return _token_pair(uuid.UUID(payload["sub"]))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
