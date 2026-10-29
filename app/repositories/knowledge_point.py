"""knowledge_point 数据访问：树形自引用表的基础 CRUD（无软删除，物理删除）。

约定：本层只 flush 不 commit，事务边界由 service 控制。
"""
from sqlalchemy import exists
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import KnowledgePoint


async def create(session: AsyncSession, **fields) -> KnowledgePoint:
    kp = KnowledgePoint(**fields)
    session.add(kp)
    await session.flush()
    return kp


async def get_by_id(session: AsyncSession, kp_id: int) -> KnowledgePoint | None:
    stmt = select(KnowledgePoint).where(KnowledgePoint.id == kp_id)
    result = await session.exec(stmt)
    return result.first()


async def exists_by_code(session: AsyncSession, code: str) -> bool:
    stmt = select(exists(KnowledgePoint.id).where(KnowledgePoint.code == code))
    result = await session.exec(stmt)
    return bool(result.one())


async def list_children(session: AsyncSession, parent_id: int | None) -> list[KnowledgePoint]:
    """查某层节点：parent_id=None 查根；同层按 order_index 排序（任务 1.6）。"""
    stmt = select(KnowledgePoint)
    if parent_id is None:
        stmt = stmt.where(KnowledgePoint.parent_id.is_(None))
    else:
        stmt = stmt.where(KnowledgePoint.parent_id == parent_id)
    stmt = stmt.order_by(KnowledgePoint.order_index, KnowledgePoint.id)
    result = await session.exec(stmt)
    return list(result.all())


async def list_all(session: AsyncSession) -> list[KnowledgePoint]:
    """全量加载（树接口在内存中组装）。"""
    stmt = select(KnowledgePoint).order_by(KnowledgePoint.id)
    result = await session.exec(stmt)
    return list(result.all())


async def has_children(session: AsyncSession, kp_id: int) -> bool:
    stmt = select(exists(KnowledgePoint.id).where(KnowledgePoint.parent_id == kp_id))
    result = await session.exec(stmt)
    return bool(result.one())


async def update(session: AsyncSession, kp_id: int, fields: dict) -> KnowledgePoint | None:
    kp = await get_by_id(session, kp_id)
    if kp is None:
        return None
    for key, value in fields.items():
        setattr(kp, key, value)
    session.add(kp)
    await session.flush()
    # onupdate 列 UPDATE 后被标记过期，refresh 取回最新值（详见 account repo 注释）
    await session.refresh(kp)
    return kp


async def delete(session: AsyncSession, kp_id: int) -> bool:
    """物理删除；被 problem_knowledge_point 引用时 FK 抛 IntegrityError，由上层转业务提示。"""
    kp = await get_by_id(session, kp_id)
    if kp is None:
        return False
    await session.delete(kp)
    await session.flush()
    return True
