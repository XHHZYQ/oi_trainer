"""知识点接口（任务 1.6：自引用树的基础 CRUD + 同层排序）。"""
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_session
from app.core.deps import require_role
from app.core.response import EnvelopeRoute
from app.models import Account, KnowledgePoint
from app.schemas.knowledge_point import KnowledgePointCreate, KnowledgePointRead, KnowledgePointUpdate
from app.services import knowledge_point as kp_service

router = APIRouter(route_class=EnvelopeRoute, tags=["knowledge_point"])


@router.post("/knowledge-points", response_model=KnowledgePointRead)
async def create_knowledge_point(
    payload: KnowledgePointCreate,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("admin")),
) -> KnowledgePoint:
    return await kp_service.create_knowledge_point(session, payload)


@router.get("/knowledge-points", response_model=list[KnowledgePointRead])
async def list_knowledge_points(
    parent_id: int = Query(..., description="父节点 id；传 0 表示查根节点"),
    session: AsyncSession = Depends(get_session),
) -> list[KnowledgePoint]:
    pid = None if parent_id == 0 else parent_id
    return await kp_service.list_children(session, pid)


@router.get("/knowledge-points/tree", response_model=list[KnowledgePointRead])
async def get_tree(session: AsyncSession = Depends(get_session)) -> list[KnowledgePointRead]:
    return await kp_service.get_tree(session)


@router.get("/knowledge-points/{kp_id}", response_model=KnowledgePointRead)
async def get_knowledge_point(kp_id: int, session: AsyncSession = Depends(get_session)) -> KnowledgePoint:
    return await kp_service.get_knowledge_point(session, kp_id)


@router.patch("/knowledge-points/{kp_id}", response_model=KnowledgePointRead)
async def update_knowledge_point(
    kp_id: int,
    payload: KnowledgePointUpdate,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("admin")),
) -> KnowledgePoint:
    return await kp_service.update_knowledge_point(session, kp_id, payload)


@router.delete("/knowledge-points/{kp_id}")
async def delete_knowledge_point(
    kp_id: int,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("admin")),
) -> dict:
    await kp_service.delete_knowledge_point(session, kp_id)
    return {"deleted": True}
