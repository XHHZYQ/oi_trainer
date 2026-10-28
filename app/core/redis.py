"""Redis 全局单例。阶段 0~2 不依赖 Redis，连接失败仅告警不阻断启动。"""
import logging

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def init_redis() -> None:
    try:
        await redis_client.ping()
        logger.info("Redis 连接成功")
    except Exception as exc:
        logger.warning("Redis 连接失败（阶段 0~2 不依赖 Redis，忽略）: %s", exc)


async def close_redis() -> None:
    await redis_client.aclose()


async def get_redis() -> Redis:
    """FastAPI Depends 用的 Redis 依赖。"""
    return redis_client
