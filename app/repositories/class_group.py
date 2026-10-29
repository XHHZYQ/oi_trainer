"""class_group 数据访问：基础 CRUD（无软删除，物理删除）。

约定：本层只 flush 不 commit，事务边界由 service 控制。
"""
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import ClassGroup
from app.schemas.common import PageParams, apply_sort

SORTABLE_FIELDS = {"id", "created_at", "start_date"}


async def create(session: AsyncSession, **fields) -> ClassGroup:
    class_group = ClassGroup(**fields)
    session.add(class_group)
    await session.flush()
    return class_group


async def get_by_id(session: AsyncSession, class_id: int) -> ClassGroup | None:
    stmt = select(ClassGroup).where(ClassGroup.id == class_id)
    result = await session.exec(stmt)
    return result.first()


def _apply_filters(stmt, *, course_id: int | None, status: str | None, teacher_id: int | None):
    if course_id is not None:
        stmt = stmt.where(ClassGroup.course_id == course_id)
    if status is not None:
        stmt = stmt.where(ClassGroup.status == status)
    if teacher_id is not None:
        stmt = stmt.where(ClassGroup.teacher_id == teacher_id)
    return stmt


async def count(
    session: AsyncSession,
    *,
    course_id: int | None = None,
    status: str | None = None,
    teacher_id: int | None = None,
) -> int:
    stmt = _apply_filters(select(func.count(ClassGroup.id)), course_id=course_id, status=status, teacher_id=teacher_id)
    result = await session.exec(stmt)
    return result.one()


async def list_page(
    session: AsyncSession,
    *,
    course_id: int | None = None,
    status: str | None = None,
    teacher_id: int | None = None,
    page: PageParams,
    sort: str | None = None,
) -> list[ClassGroup]:
    stmt = _apply_filters(select(ClassGroup), course_id=course_id, status=status, teacher_id=teacher_id)
    stmt = apply_sort(stmt, ClassGroup, sort, SORTABLE_FIELDS)
    stmt = stmt.limit(page.size).offset(page.offset)
    result = await session.exec(stmt)
    return list(result.all())


async def update(session: AsyncSession, class_id: int, fields: dict) -> ClassGroup | None:
    class_group = await get_by_id(session, class_id)
    if class_group is None:
        return None
    for key, value in fields.items():
        setattr(class_group, key, value)
    session.add(class_group)
    await session.flush()
    # onupdate 列 UPDATE 后被标记过期，refresh 取回最新值（详见 account repo 注释）
    await session.refresh(class_group)
    return class_group


async def delete(session: AsyncSession, class_id: int) -> bool:
    """物理删除；被 enrollment/order/homework 引用时 FK 抛 IntegrityError，由上层转业务提示。"""
    class_group = await get_by_id(session, class_id)
    if class_group is None:
        return False
    await session.delete(class_group)
    await session.flush()
    return True
