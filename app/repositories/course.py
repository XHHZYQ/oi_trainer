"""course 数据访问：基础 CRUD + 批量创建/批量软删除。

约定：本层只 flush/execute 不 commit，事务边界由 service 控制。
"""
from datetime import datetime, timezone

from sqlalchemy import func, update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Course
from app.schemas.common import PageParams, apply_sort

SORTABLE_FIELDS = {"id", "code", "created_at", "price_cents"}


async def create(session: AsyncSession, **fields) -> Course:
    course = Course(**fields)
    session.add(course)
    await session.flush()
    return course


async def create_batch(session: AsyncSession, items: list[dict]) -> list[Course]:
    """批量创建：一次 add_all + flush，任一冲突整批由上层回滚（任务 1.4）。"""
    courses = [Course(**item) for item in items]
    session.add_all(courses)
    await session.flush()
    return courses


async def get_by_id(session: AsyncSession, course_id: int) -> Course | None:
    stmt = select(Course).where(Course.id == course_id, Course.deleted_at.is_(None))
    result = await session.exec(stmt)
    return result.first()


def _apply_filters(stmt, *, status: str | None, level: str | None):
    stmt = stmt.where(Course.deleted_at.is_(None))
    if status is not None:
        stmt = stmt.where(Course.status == status)
    if level is not None:
        stmt = stmt.where(Course.level == level)
    return stmt


async def count(session: AsyncSession, *, status: str | None = None, level: str | None = None) -> int:
    stmt = _apply_filters(select(func.count(Course.id)), status=status, level=level)
    result = await session.exec(stmt)
    return result.one()


async def list_page(
    session: AsyncSession,
    *,
    status: str | None = None,
    level: str | None = None,
    page: PageParams,
    sort: str | None = None,
) -> list[Course]:
    stmt = _apply_filters(select(Course), status=status, level=level)
    stmt = apply_sort(stmt, Course, sort, SORTABLE_FIELDS)
    stmt = stmt.limit(page.size).offset(page.offset)
    result = await session.exec(stmt)
    return list(result.all())


async def update_course(session: AsyncSession, course_id: int, fields: dict) -> Course | None:
    course = await get_by_id(session, course_id)
    if course is None:
        return None
    for key, value in fields.items():
        setattr(course, key, value)
    session.add(course)
    await session.flush()
    # onupdate 列 UPDATE 后被标记过期，refresh 取回最新值（详见 account repo 注释）
    await session.refresh(course)
    return course


async def soft_delete(session: AsyncSession, course_id: int) -> bool:
    course = await get_by_id(session, course_id)
    if course is None:
        return False
    course.deleted_at = datetime.now(timezone.utc)
    session.add(course)
    await session.flush()
    return True


async def soft_delete_batch(session: AsyncSession, ids: list[int]) -> int:
    """批量软删除：一条 UPDATE ... WHERE id = ANY(:ids)，返回实际影响行数（任务 1.4）。"""
    stmt = (
        update(Course)
        .where(Course.id.in_(ids), Course.deleted_at.is_(None))
        .values(deleted_at=datetime.now(timezone.utc))
    )
    result = await session.execute(stmt)
    return result.rowcount
