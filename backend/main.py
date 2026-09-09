from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from core import security
from core.config import settings
from db import SessionLocal
from models import User
from routers import auth, problems, profile, vision

app = FastAPI(title="BACII Math Engine", version="0.2.0")


@app.on_event("startup")
async def seed_admin_user() -> None:
    """Upsert the one admin account from ADMIN_EMAIL/ADMIN_PASSWORD each boot.

    This is the only way an account becomes an admin for now — there's no
    in-app promotion flow. Leaving both env vars blank skips seeding.
    """
    email = settings.admin_email.strip().lower()
    if not email or not settings.admin_password:
        return
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        hashed = security.hash_password(settings.admin_password)
        if user is None:
            db.add(User(email=email, hashed_password=hashed, is_admin=True))
        else:
            user.hashed_password = hashed
            user.is_admin = True
        await db.commit()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3016", "http://127.0.0.1:3016",
        "http://172.20.10.6:3016",  # LAN access (e.g. iPad on the same Wi-Fi)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(problems.me_router)
app.include_router(profile.router)
app.include_router(vision.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"app": "BACII Math Engine", "docs": "/docs", "health": "/health"}
