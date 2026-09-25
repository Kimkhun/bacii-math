import json
import logging

import redis.asyncio as redis

from core.config import settings

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def get_explanation(key: str) -> str | None:
    try:
        return await _get_client().get(key)
    except Exception as exc:  # a cache outage must never break grading
        logging.getLogger("bacii").warning("explanation cache read failed: %s", exc)
        return None


async def set_explanation(key: str, value: str) -> None:
    try:
        await _get_client().setex(key, settings.explanation_cache_ttl_seconds, value)
    except Exception as exc:
        logging.getLogger("bacii").warning("explanation cache write failed: %s", exc)


async def get_km_solution(key: str) -> dict | None:
    """Cached Gemini-generated Khmer reference solution (structured JSON)."""
    raw = await _get_client().get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


async def set_km_solution(key: str, value: dict) -> None:
    await _get_client().setex(
        key, settings.explanation_cache_ttl_seconds, json.dumps(value, ensure_ascii=False)
    )


async def delete(key: str) -> None:
    await _get_client().delete(key)


async def allow_gemini(user_id: str) -> bool:
    """Per-user Gemini rate limit. INCR and EXPIRE run in one transaction so a
    crash between them can't leave a counter with no TTL (which would lock the
    user out forever). If Redis is down, deny Gemini (callers fall back to the
    deterministic path) rather than failing the whole request."""
    key = f"ratelimit:gemini:{user_id}"
    try:
        pipe = _get_client().pipeline(transaction=True)
        pipe.incr(key)
        pipe.expire(key, 60, nx=True)
        count, _ = await pipe.execute()
    except Exception as exc:
        logging.getLogger("bacii").warning("rate-limit store unavailable: %s", exc)
        return False
    return count <= settings.gemini_rate_limit_per_minute


async def auth_rate_limit(subject: str, limit: int = 10, window_seconds: int = 60) -> bool:
    """Fixed-window limiter for auth endpoints (login/signup), keyed by client
    IP and target email. Returns True while under `limit` attempts per window.
    If Redis is unavailable it fails OPEN (returns True) so a cache outage can't
    lock every user out of signing in — brute-force protection is best-effort,
    not a hard dependency of authentication."""
    key = f"ratelimit:auth:{subject}"
    try:
        pipe = _get_client().pipeline(transaction=True)
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        count, _ = await pipe.execute()
    except Exception as exc:
        logging.getLogger("bacii").warning("auth rate-limit store unavailable: %s", exc)
        return True
    return count <= limit


async def get_system_model_settings() -> dict:
    """Read dynamic model settings from Redis with fallbacks to environment variables."""
    r = _get_client()
    text_model = await r.get("system:model:text") or settings.gemini_model
    vision_model = await r.get("system:model:vision") or settings.gemini_vision_model or settings.gemini_model
    vision_provider = await r.get("system:model:vision_provider") or settings.vision_provider
    return {
        "text_model": text_model,
        "vision_model": vision_model,
        "vision_provider": vision_provider,
    }


async def set_system_model_settings(text_model: str, vision_model: str, vision_provider: str) -> None:
    """Update dynamic model configuration in Redis across all backend workers."""
    r = _get_client()
    await r.set("system:model:text", text_model)
    await r.set("system:model:vision", vision_model)
    await r.set("system:model:vision_provider", vision_provider)
