"""班级接口（基础 CRUD；enrolled_count/version 由业务流转维护，不走通用更新）。"""
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_session
from app.core.deps import require_role
from app.core.response import EnvelopeRoute
from app.models import Account, ClassGroup
from app.models.enums import ClassGroupStatus
from app.schemas.class_group import ClassGroupCreate, ClassGroupRead, ClassGroupUpdate
from app.schemas.common import Page, PageParams
from app.services import class_group as class_group_service

router = APIRouter(route_class=EnvelopeRoute, tags=["class_group"])


@router.post("/classes", response_model=ClassGroupRead)
async def create_class_group(
    payload: ClassGroupCreate,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("teacher", "admin")),
) -> ClassGroup:
    return await class_group_service.create_class_group(session, payload)


@router.get("/classes", response_model=Page[ClassGroupRead])
async def list_class_groups(
    page: PageParams = Depends(),
    course_id: int | None = Query(None),
    status: ClassGroupStatus | None = Query(None),
    teacher_id: int | None = Query(None),
    sort: str = Query("-created_at,id", description="排序：逗号分隔，- 前缀倒序"),
    session: AsyncSession = Depends(get_session),
) -> Page[ClassGroupRead]:
    items, total = await class_group_service.list_class_groups(
        session, course_id=course_id, status=status, teacher_id=teacher_id, page=page, sort=sort
    )
    # 显式逐项 model_validate，原因见 accounts 列表接口注释
    return Page[ClassGroupRead](
        items=[ClassGroupRead.model_validate(item) for item in items], total=total, page=page.page, size=page.size
    )


@router.get("/classes/{class_id}", response_model=ClassGroupRead)
async def get_class_group(class_id: int, session: AsyncSession = Depends(get_session)) -> ClassGroup:
    return await class_group_service.get_class_group(session, class_id)


@router.patch("/classes/{class_id}", response_model=ClassGroupRead)
async def update_class_group(
    class_id: int,
    payload: ClassGroupUpdate,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("teacher", "admin")),
) -> ClassGroup:
    return await class_group_service.update_class_group(session, class_id, payload)


@router.delete("/classes/{class_id}")
async def delete_class_group(
    class_id: int,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("admin")),
) -> dict:
    await class_group_service.delete_class_group(session, class_id)
    return {"deleted": True}
