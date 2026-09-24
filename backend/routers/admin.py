"""Admin observability, cost monitoring, and dynamic model configuration router."""
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cache import get_system_model_settings, set_system_model_settings
from core.deps import get_current_admin_user, get_db
from models import ApiUsageLog, User

router = APIRouter(prefix="/admin", tags=["admin"])


class ModelSettingsRequest(BaseModel):
    text_model: str
    vision_model: str
    vision_provider: str


@router.get("/model-settings")
async def get_models(admin: User = Depends(get_current_admin_user)):
    """Retrieve the current active LLM & Vision model settings."""
    return await get_system_model_settings()


@router.post("/model-settings")
async def update_models(
    req: ModelSettingsRequest,
    admin: User = Depends(get_current_admin_user),
):
    """Dynamically switch active models in Redis across all workers."""
    if req.vision_provider not in ("gemini", "ollama", "fallback"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "vision_provider must be gemini, ollama or fallback")
    await set_system_model_settings(
        text_model=req.text_model,
        vision_model=req.vision_model,
        vision_provider=req.vision_provider,
    )
    return {"status": "ok", "settings": req.model_dump()}


@router.get("/costs/summary")
async def get_costs_summary(
    days: int = Query(30, ge=1, le=365),
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Overall token usage and cost metrics."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    # 1. Total lifetime & timeframe metrics
    q_period = select(
        func.count(ApiUsageLog.id).label("calls"),
        func.coalesce(func.sum(ApiUsageLog.prompt_tokens), 0).label("prompt_tokens"),
        func.coalesce(func.sum(ApiUsageLog.completion_tokens), 0).label("completion_tokens"),
        func.coalesce(func.sum(ApiUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(ApiUsageLog.estimated_cost_usd), 0.0).label("cost_usd"),
        func.coalesce(func.sum(ApiUsageLog.prompt_cost_usd), 0.0).label("prompt_cost_usd"),
        func.coalesce(func.sum(ApiUsageLog.completion_cost_usd), 0.0).label("completion_cost_usd"),
        func.coalesce(func.avg(ApiUsageLog.latency_ms), 0).label("avg_latency_ms"),
    ).where(ApiUsageLog.created_at >= since)
    res_period = (await db.execute(q_period)).first()

    # 2. Today metrics
    q_today = select(
        func.count(ApiUsageLog.id).label("calls"),
        func.coalesce(func.sum(ApiUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(ApiUsageLog.estimated_cost_usd), 0.0).label("cost_usd"),
        func.coalesce(func.sum(ApiUsageLog.prompt_cost_usd), 0.0).label("prompt_cost_usd"),
        func.coalesce(func.sum(ApiUsageLog.completion_cost_usd), 0.0).label("completion_cost_usd"),
    ).where(ApiUsageLog.created_at >= today_start)
    res_today = (await db.execute(q_today)).first()

    # 3. Breakdown by endpoint (ocr, narration, graph_grade, correction, etc.)
    q_endpoints = select(
        ApiUsageLog.endpoint,
        func.count(ApiUsageLog.id).label("calls"),
        func.coalesce(func.sum(ApiUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(ApiUsageLog.estimated_cost_usd), 0.0).label("cost_usd"),
        func.coalesce(func.sum(ApiUsageLog.prompt_cost_usd), 0.0).label("prompt_cost_usd"),
        func.coalesce(func.sum(ApiUsageLog.completion_cost_usd), 0.0).label("completion_cost_usd"),
    ).where(ApiUsageLog.created_at >= since).group_by(ApiUsageLog.endpoint)
    res_endpoints = (await db.execute(q_endpoints)).all()

    # 4. Breakdown by model
    q_models = select(
        ApiUsageLog.model_name,
        func.count(ApiUsageLog.id).label("calls"),
        func.coalesce(func.sum(ApiUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(ApiUsageLog.estimated_cost_usd), 0.0).label("cost_usd"),
        func.coalesce(func.sum(ApiUsageLog.prompt_cost_usd), 0.0).label("prompt_cost_usd"),
        func.coalesce(func.sum(ApiUsageLog.completion_cost_usd), 0.0).label("completion_cost_usd"),
    ).where(ApiUsageLog.created_at >= since).group_by(ApiUsageLog.model_name)
    res_models = (await db.execute(q_models)).all()

    return {
        "timeframe_days": days,
        "today": {
            "calls": res_today.calls,
            "total_tokens": res_today.total_tokens,
            "cost_usd": round(float(res_today.cost_usd), 5),
            "prompt_cost_usd": round(float(res_today.prompt_cost_usd), 5),
            "completion_cost_usd": round(float(res_today.completion_cost_usd), 5),
        },
        "period": {
            "calls": res_period.calls,
            "prompt_tokens": res_period.prompt_tokens,
            "completion_tokens": res_period.completion_tokens,
            "total_tokens": res_period.total_tokens,
            "cost_usd": round(float(res_period.cost_usd), 5),
            "prompt_cost_usd": round(float(res_period.prompt_cost_usd), 5),
            "completion_cost_usd": round(float(res_period.completion_cost_usd), 5),
            "avg_latency_ms": round(float(res_period.avg_latency_ms), 1),
        },
        "by_endpoint": [
            {
                "endpoint": row.endpoint,
                "calls": row.calls,
                "total_tokens": row.total_tokens,
                "cost_usd": round(float(row.cost_usd), 5),
                "prompt_cost_usd": round(float(row.prompt_cost_usd), 5),
                "completion_cost_usd": round(float(row.completion_cost_usd), 5),
            }
            for row in res_endpoints
        ],
        "by_model": [
            {
                "model_name": row.model_name,
                "calls": row.calls,
                "total_tokens": row.total_tokens,
                "cost_usd": round(float(row.cost_usd), 5),
                "prompt_cost_usd": round(float(row.prompt_cost_usd), 5),
                "completion_cost_usd": round(float(row.completion_cost_usd), 5),
            }
            for row in res_models
        ],
    }


@router.get("/costs/users")
async def get_costs_by_user(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    endpoint: Optional[str] = None,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Ranked usage and cost per student user."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = select(
        ApiUsageLog.user_id,
        User.email,
        func.count(ApiUsageLog.id).label("total_calls"),
        func.coalesce(func.sum(ApiUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(ApiUsageLog.estimated_cost_usd), 0.0).label("total_cost_usd"),
        func.max(ApiUsageLog.created_at).label("last_active"),
    ).outerjoin(User, ApiUsageLog.user_id == User.id).where(ApiUsageLog.created_at >= since)

    if endpoint:
        query = query.where(ApiUsageLog.endpoint == endpoint)

    query = query.group_by(ApiUsageLog.user_id, User.email).order_by(desc("total_cost_usd")).limit(limit)

    rows = (await db.execute(query)).all()
    return [
        {
            "user_id": str(row.user_id) if row.user_id else "anonymous",
            "email": row.email or "unauthenticated",
            "total_calls": row.total_calls,
            "total_tokens": row.total_tokens,
            "total_cost_usd": round(float(row.total_cost_usd), 5),
            "last_active": row.last_active.isoformat() if row.last_active else None,
        }
        for row in rows
    ]


@router.get("/costs/logs")
async def get_recent_usage_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    endpoint: Optional[str] = None,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Paginated stream of recent API consumption logs for debugging/auditing."""
    # 1. Total count query
    count_query = select(func.count(ApiUsageLog.id))
    if endpoint:
        count_query = count_query.where(ApiUsageLog.endpoint == endpoint)
    total = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size

    # 2. Paginated rows query
    query = select(
        ApiUsageLog.id,
        ApiUsageLog.user_id,
        User.email,
        ApiUsageLog.endpoint,
        ApiUsageLog.provider,
        ApiUsageLog.model_name,
        ApiUsageLog.prompt_tokens,
        ApiUsageLog.completion_tokens,
        ApiUsageLog.total_tokens,
        ApiUsageLog.estimated_cost_usd,
        ApiUsageLog.prompt_cost_usd,
        ApiUsageLog.completion_cost_usd,
        ApiUsageLog.prompt_text,
        ApiUsageLog.response_text,
        ApiUsageLog.latency_ms,
        ApiUsageLog.success,
        ApiUsageLog.error_message,
        ApiUsageLog.created_at,
    ).outerjoin(User, ApiUsageLog.user_id == User.id)

    if endpoint:
        query = query.where(ApiUsageLog.endpoint == endpoint)

    query = query.order_by(desc(ApiUsageLog.created_at)).offset(offset).limit(page_size)

    rows = (await db.execute(query)).all()
    return {
        "logs": [
            {
                "id": str(r.id),
                "user_id": str(r.user_id) if r.user_id else None,
                "email": r.email or "unauthenticated",
                "endpoint": r.endpoint,
                "provider": r.provider,
                "model_name": r.model_name,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "estimated_cost_usd": round(float(r.estimated_cost_usd), 6),
                "prompt_cost_usd": round(float(r.prompt_cost_usd or 0.0), 6),
                "completion_cost_usd": round(float(r.completion_cost_usd or 0.0), 6),
                "prompt_text": r.prompt_text,
                "response_text": r.response_text,
                "latency_ms": r.latency_ms,
                "success": r.success,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
