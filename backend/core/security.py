import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from core.config import settings

# Values shipped as placeholders in .env.example / docker-compose.yml. If any of
# these is still in effect when ENVIRONMENT=production, the app refuses to boot
# rather than run with a guessable secret.
_INSECURE_DEFAULTS = {
    "jwt_secret": {"dev-secret-change-me", "dev-secret-change-me-0123456789abcdef"},
    "admin_password": {"AdminBacII2026!"},
    "postgres_password": {"postgres"},
}

# bcrypt only hashes the first 72 bytes and newer builds raise on longer input;
# truncate so an over-long password is a normal (wrong-length) mismatch, not a 500.
_BCRYPT_MAX_BYTES = 72


def assert_secure() -> None:
    """Fail fast in production if a known dev-default secret is still in use."""
    if settings.environment.strip().lower() != "production":
        return
    problems = []
    if settings.jwt_secret in _INSECURE_DEFAULTS["jwt_secret"]:
        problems.append("JWT_SECRET is the built-in dev default")
    if settings.admin_password in _INSECURE_DEFAULTS["admin_password"]:
        problems.append("ADMIN_PASSWORD is the built-in dev default")
    if any(f":{p}@" in settings.database_url for p in _INSECURE_DEFAULTS["postgres_password"]):
        problems.append("DATABASE_URL uses the default postgres password")
    if problems:
        raise RuntimeError(
            "Refusing to start in production with insecure defaults: "
            + "; ".join(problems)
            + ". Set strong values in the environment."
        )


def _clip(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_clip(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_clip(password), hashed.encode("utf-8"))
    except ValueError:
        return False


def _create_token(user_id: uuid.UUID, token_type: str, expires_delta: timedelta, token_version: int = 0) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        # Bumping User.token_version invalidates every token issued so far
        # (logout-everywhere / password reset / forced re-auth): a token whose
        # `ver` no longer matches the user's current version is rejected.
        "ver": token_version,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, token_version: int = 0) -> str:
    return _create_token(user_id, "access", timedelta(minutes=settings.access_token_expire_minutes), token_version)


def create_refresh_token(user_id: uuid.UUID, token_version: int = 0) -> str:
    return _create_token(user_id, "refresh", timedelta(days=settings.refresh_token_expire_days), token_version)


def decode_token(token: str, expected_type: str | None = None) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if expected_type is not None and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("unexpected token type")
    return payload
