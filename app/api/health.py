"""健康检查：DB 探活失败也返回 200，data.db 标记 up/down。"""
from fastapi import APIRouter
from sqlalchemy import text

from app.core.db import engine
from app.core.response import EnvelopeRoute, ok

router = APIRouter(route_class=EnvelopeRoute, tags=["health"])


@router.get("/health")
async def health() -> dict:
    db_status = "up"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"
    return ok({"status": "ok", "db": db_status})
