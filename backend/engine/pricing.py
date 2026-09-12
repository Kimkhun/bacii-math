"""Pricing calculator and asynchronous usage logging for LLM & Vision calls."""
import asyncio
import logging
import uuid
from datetime import datetime

from db import SessionLocal
from models import ApiUsageLog

log = logging.getLogger(__name__)

# Official Google Gemini & Local Inference Pricing per 1M tokens (USD)
# Updated based on Google AI Developer Pricing 2026.
# Format: {"prompt": cost_per_1M, "completion": cost_per_1M}
PRICING_PER_MILLION = {
    # Gemini 3.5 Flash / 2.5 Flash / 2.0 Flash / 1.5 Flash tier
    "gemini-3.5-flash": {"prompt": 0.075, "completion": 0.30},
    "gemini-2.5-flash": {"prompt": 0.075, "completion": 0.30},
    "gemini-2.0-flash": {"prompt": 0.075, "completion": 0.30},
    "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.30},
    "gemini-flash": {"prompt": 0.075, "completion": 0.30},

    # Gemini Pro reasoning tier
    "gemini-1.5-pro": {"prompt": 1.25, "completion": 5.00},
    "gemini-2.5-pro": {"prompt": 1.25, "completion": 5.00},

    # Local Ollama models
    "qwen2.5:3b": {"prompt": 0.0, "completion": 0.0},
    "qwen2.5vl:3b": {"prompt": 0.0, "completion": 0.0},
}

DEFAULT_FLASH_RATES = {"prompt": 0.075, "completion": 0.30}


def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate the estimated USD cost for a given model and token counts."""
    rates = PRICING_PER_MILLION.get(model_name.lower())
    if not rates:
        # Fallback to flash rates for unknown gemini models, 0 for local
        if "gemini" in model_name.lower():
            rates = DEFAULT_FLASH_RATES
        else:
            return 0.0

    prompt_cost = (prompt_tokens / 1_000_000.0) * rates["prompt"]
    completion_cost = (completion_tokens / 1_000_000.0) * rates["completion"]
    return round(prompt_cost + completion_cost, 7)


async def _write_usage_log(
    user_id: uuid.UUID | str | None,
    endpoint: str,
    provider: str,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    success: bool,
    error_message: str | None = None,
) -> None:
    """Internal task that writes a usage row to Postgres without raising."""
    try:
        total_tokens = prompt_tokens + completion_tokens
        cost = calculate_cost(model_name, prompt_tokens, completion_tokens)

        parsed_user_id = None
        if user_id:
            if isinstance(user_id, uuid.UUID):
                parsed_user_id = user_id
            else:
                try:
                    parsed_user_id = uuid.UUID(str(user_id))
                except Exception:
                    pass

        async with SessionLocal() as db:
            log_entry = ApiUsageLog(
                user_id=parsed_user_id,
                endpoint=endpoint,
                provider=provider,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=cost,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
            )
            db.add(log_entry)
            await db.commit()
    except Exception as exc:
        log.warning("Failed to record api usage log: %s", exc)


def record_api_usage(
    user_id: uuid.UUID | str | None,
    endpoint: str,
    provider: str,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    success: bool = True,
    error_message: str | None = None,
) -> None:
    """Non-blocking fire-and-forget hook to log API consumption.

    Guarantees that database writes never block or interrupt the student's canvas grading.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            _write_usage_log(
                user_id=user_id,
                endpoint=endpoint,
                provider=provider,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
            )
        )
    except RuntimeError:
        # If running outside an active event loop (e.g. sync worker thread)
        asyncio.run(
            _write_usage_log(
                user_id=user_id,
                endpoint=endpoint,
                provider=provider,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
            )
        )
