"""数据库引擎与会话（全异步）。"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends 用的会话生成器。"""
    async with _session_factory() as session:
        yield session


def new_session() -> AsyncSession:
    """脚本/后台任务手动管理的会话（配合 async with 使用）。"""
    return _session_factory()
