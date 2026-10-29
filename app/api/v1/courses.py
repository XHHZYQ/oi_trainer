"""课程接口（任务 1.3 CRUD+状态流转，1.4 批量创建/批量软删除）。"""
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_session
from app.core.deps import require_role
from app.core.response import EnvelopeRoute
from app.models import Account, Course
from app.models.enums import CourseStatus
from app.schemas.common import Page, PageParams
from app.schemas.course import CourseBatchDelete, CourseCreate, CourseRead, CourseUpdate
from app.services import course as course_service

router = APIRouter(route_class=EnvelopeRoute, tags=["course"])


@router.post("/courses", response_model=CourseRead)
async def create_course(
    payload: CourseCreate,
    session: AsyncSession = Depends(get_session),
    current: Account = Depends(require_role("admin")),
) -> Course:
    return await course_service.create_course(session, payload, created_by=current.id)


@router.post("/courses/batch", response_model=list[CourseRead])
async def create_courses_batch(
    payloads: list[CourseCreate],
    session: AsyncSession = Depends(get_session),
    current: Account = Depends(require_role("admin")),
) -> list[Course]:
    return await course_service.create_courses_batch(session, payloads, created_by=current.id)


@router.post("/courses/batch-delete")
async def batch_delete_courses(
    payload: CourseBatchDelete,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("admin")),
) -> dict:
    affected = await course_service.batch_delete_courses(session, payload.ids)
    return {"affected": affected}


@router.get("/courses", response_model=Page[CourseRead])
async def list_courses(
    page: PageParams = Depends(),
    status: CourseStatus | None = Query(None),
    level: str | None = Query(None),
    sort: str = Query("-created_at,id", description="排序：逗号分隔，- 前缀倒序"),
    session: AsyncSession = Depends(get_session),
) -> Page[CourseRead]:
    items, total = await course_service.list_courses(session, status=status, level=level, page=page, sort=sort)
    # 显式逐项 model_validate，原因见 accounts 列表接口注释
    return Page[CourseRead](
        items=[CourseRead.model_validate(item) for item in items], total=total, page=page.page, size=page.size
    )


@router.get("/courses/{course_id}", response_model=CourseRead)
async def get_course(course_id: int, session: AsyncSession = Depends(get_session)) -> Course:
    return await course_service.get_course(session, course_id)


@router.patch("/courses/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: int,
    payload: CourseUpdate,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("admin")),
) -> Course:
    return await course_service.update_course(session, course_id, payload)


@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: int,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("admin")),
) -> dict:
    await course_service.soft_delete_course(session, course_id)
    return {"deleted": True}
