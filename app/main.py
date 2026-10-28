"""FastAPI 入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.exceptions import register_exception_handlers
from app.core.redis import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()  # 阶段 0~2 容错：Redis 不可用仅告警
    yield
    await close_redis()


app = FastAPI(title="信奥 AI 编程训练平台", version="0.1.0", lifespan=lifespan)

register_exception_handlers(app)
app.include_router(health_router)
