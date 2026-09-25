import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import cache
from core import security
from core.deps import get_current_user, get_db
from engine.concurrency import run_in_thread
from models import User
from schemas import LoginRequest, RefreshRequest, TokenPair, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


async def _throttle(request: Request, email: str) -> None:
    """Fixed-window brute-force guard on the auth endpoints, keyed by client IP
    and by target email so neither an IP nor a single account can be hammered.
    Fails open only if the rate-limit store is down (see cache.auth_rate_limit)."""
    ip = request.client.host if request.client else "unknown"
    if not await cache.auth_rate_limit(f"ip:{ip}") or not await cache.auth_rate_limit(f"email:{email}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Please wait a minute and try again."
        )


def _token_pair(user_id: uuid.UUID, token_version: int = 0) -> TokenPair:
    return TokenPair(
        access_token=security.create_access_token(user_id, token_version),
        refresh_token=security.create_refresh_token(user_id, token_version),
    )


@router.post("/signup")
async def signup(body: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    await _throttle(request, email)
    if await db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    # bcrypt is CPU-bound; hashing on the event loop stalls every other request.
    hashed = await run_in_thread(security.hash_password, body.password)
    user = User(email=email, hashed_password=hashed)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:  # concurrent signup with the same email
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    await db.refresh(user)
    return {"user": UserOut.model_validate(user), **_token_pair(user.id, user.token_version).model_dump()}


@router.post("/login")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    await _throttle(request, email)
    user = await db.scalar(select(User).where(User.email == email))
    ok = user is not None and await run_in_thread(security.verify_password, body.password, user.hashed_password)
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return {"user": UserOut.model_validate(user), **_token_pair(user.id, user.token_version).model_dump()}


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = security.decode_token(body.refresh_token, expected_type="refresh")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    # A revoked (superseded) refresh token must not mint fresh tokens.
    if payload.get("ver", 0) != user.token_version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has been revoked")
    return _token_pair(user_id, user.token_version)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
