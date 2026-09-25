import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update

from core import security
from core.config import settings
from db import SessionLocal
from models import User
from routers import admin, auth, problems, profile, vision

# SymPy work runs in worker threads (engine/concurrency.py, 2 workers). A shorter GIL
# switch interval lets the event loop take its turn more often. Measured over HTTP with
# 8 concurrent heavy users (health-check worst / heavy users' total time):
#   inline (old)  1978 ms / 13.9 s      5 ms  422 ms / 13.3 s
#   2 ms (chosen)  163 ms / 18.1 s      1 ms   92 ms / 23.2 s
sys.setswitchinterval(0.002)

# Refuse to boot in production with a known dev-default secret.
security.assert_secure()

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
        # Exactly one admin: strip is_admin from anyone else who somehow has it
        # (e.g. ADMIN_EMAIL was rotated to a new address). Without this, the old
        # admin would keep their privileges forever.
        await db.execute(
            update(User).where(User.email != email, User.is_admin.is_(True)).values(is_admin=False)
        )
        await db.commit()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(problems.me_router)
app.include_router(profile.router)
app.include_router(vision.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"app": "BACII Math Engine", "docs": "/docs", "health": "/health"}
