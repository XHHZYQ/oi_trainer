"""knowledge_point 业务逻辑：父节点校验 + 移动防环 + 删除保护。"""
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exceptions import BusinessException
from app.models import KnowledgePoint
from app.repositories import knowledge_point as kp_repo
from app.schemas.knowledge_point import KnowledgePointCreate, KnowledgePointRead, KnowledgePointUpdate


async def create_knowledge_point(session: AsyncSession, payload: KnowledgePointCreate) -> KnowledgePoint:
    if payload.parent_id is not None and await kp_repo.get_by_id(session, payload.parent_id) is None:
        raise BusinessException("父节点不存在")
    if await kp_repo.exists_by_code(session, payload.code):
        raise BusinessException("知识点编码已存在")
    try:
        kp = await kp_repo.create(session, **payload.model_dump())
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BusinessException("知识点编码已存在") from exc
    return kp


async def get_knowledge_point(session: AsyncSession, kp_id: int) -> KnowledgePoint:
    kp = await kp_repo.get_by_id(session, kp_id)
    if kp is None:
        raise BusinessException("知识点不存在", code=404)
    return kp


async def list_children(session: AsyncSession, parent_id: int | None) -> list[KnowledgePoint]:
    return await kp_repo.list_children(session, parent_id)


async def get_tree(session: AsyncSession) -> list[KnowledgePointRead]:
    """全量加载 + 内存组装嵌套树，每层按 order_index 排序。"""
    nodes = await kp_repo.list_all(session)
    reads = {n.id: KnowledgePointRead.model_validate(n, from_attributes=True) for n in nodes}
    roots: list[KnowledgePointRead] = []
    for n in nodes:
        node = reads[n.id]
        parent_id = n.parent_id
        if parent_id is None or parent_id not in reads:
            roots.append(node)
        else:
            reads[parent_id].children.append(node)
    for node in reads.values():
        node.children.sort(key=lambda c: (c.order_index, c.id))
    roots.sort(key=lambda c: (c.order_index, c.id))
    return roots


async def _assert_not_cycle(session: AsyncSession, node_id: int, new_parent_id: int) -> None:
    """沿新父节点向上走祖先链，若命中自己说明会成环（应用层防环，树小用循环查即可）。"""
    visited = {node_id}
    current_id: int | None = new_parent_id
    while current_id is not None:
        if current_id in visited:
            raise BusinessException("不能把节点挂到自己的子孙下")
        visited.add(current_id)
        parent = await kp_repo.get_by_id(session, current_id)
        current_id = parent.parent_id if parent is not None else None


async def update_knowledge_point(
    session: AsyncSession, kp_id: int, payload: KnowledgePointUpdate
) -> KnowledgePoint:
    kp = await kp_repo.get_by_id(session, kp_id)
    if kp is None:
        raise BusinessException("知识点不存在", code=404)
    fields = payload.model_dump(exclude_unset=True)

    if "parent_id" in fields:
        new_parent = fields["parent_id"]
        if new_parent is not None:
            if new_parent == kp_id:
                raise BusinessException("父节点不能是自己")
            if await kp_repo.get_by_id(session, new_parent) is None:
                raise BusinessException("父节点不存在")
            await _assert_not_cycle(session, kp_id, new_parent)

    updated = await kp_repo.update(session, kp_id, fields)
    await session.commit()
    return updated


async def delete_knowledge_point(session: AsyncSession, kp_id: int) -> None:
    if await kp_repo.get_by_id(session, kp_id) is None:
        raise BusinessException("知识点不存在", code=404)
    if await kp_repo.has_children(session, kp_id):
        raise BusinessException("存在子节点，请先删除子节点")
    try:
        await kp_repo.delete(session, kp_id)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BusinessException("该知识点已被题目等数据引用，不允许删除") from exc
