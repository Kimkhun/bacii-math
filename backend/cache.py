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


async def allow_gemini(user_id: str) -> bool:
    key = f"ratelimit:gemini:{user_id}"
    r = _get_client()
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, 60)
    return count <= settings.gemini_rate_limit_per_minute
