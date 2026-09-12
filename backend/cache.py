import json

import redis.asyncio as redis

from core.config import settings

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def get_explanation(key: str) -> str | None:
    return await _get_client().get(key)


async def set_explanation(key: str, value: str) -> None:
    await _get_client().setex(key, settings.explanation_cache_ttl_seconds, value)


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
    key = f"ratelimit:gemini:{user_id}"
    r = _get_client()
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, 60)
    return count <= settings.gemini_rate_limit_per_minute


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
