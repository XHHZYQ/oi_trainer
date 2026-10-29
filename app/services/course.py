"""course 业务逻辑：状态机流转 + 批量操作 + code 唯一冲突兜底。"""
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exceptions import BusinessException
from app.models import Course
from app.models.enums import CourseStatus
from app.repositories import course as course_repo
from app.schemas.common import PageParams
from app.schemas.course import CourseCreate, CourseUpdate

# 状态机：draft→published→archived，archived→published（恢复上架）
ALLOWED_TRANSITIONS: dict[CourseStatus, set[CourseStatus]] = {
    CourseStatus.draft: {CourseStatus.published},
    CourseStatus.published: {CourseStatus.archived},
    CourseStatus.archived: {CourseStatus.published},
}


async def create_course(session: AsyncSession, payload: CourseCreate, *, created_by: int | None = None) -> Course:
    data = payload.model_dump()
    data["created_by"] = created_by
    try:
        course = await course_repo.create(session, **data)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BusinessException("课程编码已存在") from exc
    return course


async def create_courses_batch(
    session: AsyncSession, payloads: list[CourseCreate], *, created_by: int | None = None
) -> list[Course]:
    items = []
    for p in payloads:
        data = p.model_dump()
        data["created_by"] = created_by
        items.append(data)
    try:
        courses = await course_repo.create_batch(session, items)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BusinessException("存在重复的课程编码，整批已回滚") from exc
    return courses


async def get_course(session: AsyncSession, course_id: int) -> Course:
    course = await course_repo.get_by_id(session, course_id)
    if course is None:
        raise BusinessException("课程不存在", code=404)
    return course


async def list_courses(
    session: AsyncSession,
    *,
    status: str | None,
    level: str | None,
    page: PageParams,
    sort: str | None,
) -> tuple[list[Course], int]:
    total = await course_repo.count(session, status=status, level=level)
    items = await course_repo.list_page(session, status=status, level=level, page=page, sort=sort)
    return items, total


async def update_course(session: AsyncSession, course_id: int, payload: CourseUpdate) -> Course:
    fields = payload.model_dump(exclude_unset=True)
    course = await course_repo.get_by_id(session, course_id)
    if course is None:
        raise BusinessException("课程不存在", code=404)

    new_status = fields.get("status")
    if new_status is not None and CourseStatus(new_status) != CourseStatus(course.status):
        allowed = ALLOWED_TRANSITIONS.get(CourseStatus(course.status), set())
        if CourseStatus(new_status) not in allowed:
            raise BusinessException(f"非法状态流转: {course.status} -> {new_status}")

    try:
        updated = await course_repo.update_course(session, course_id, fields)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BusinessException("课程编码已存在") from exc
    return updated


async def soft_delete_course(session: AsyncSession, course_id: int) -> None:
    deleted = await course_repo.soft_delete(session, course_id)
    if not deleted:
        raise BusinessException("课程不存在", code=404)
    await session.commit()


async def batch_delete_courses(session: AsyncSession, ids: list[int]) -> int:
    """批量软删除，返回实际影响行数（已删除的不重复计数）。"""
    affected = await course_repo.soft_delete_batch(session, ids)
    await session.commit()
    return affected
