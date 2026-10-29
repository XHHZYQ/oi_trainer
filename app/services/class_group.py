"""class_group 业务逻辑：外键存在性校验 + 日期区间校验 + 物理删除的 FK 兜底。"""
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exceptions import BusinessException
from app.models import ClassGroup
from app.repositories import account as account_repo
from app.repositories import class_group as class_group_repo
from app.repositories import course as course_repo
from app.schemas.class_group import ClassGroupCreate, ClassGroupUpdate
from app.schemas.common import PageParams


async def _assert_refs_exist(session: AsyncSession, course_id: int | None, teacher_id: int | None) -> None:
    if course_id is not None and await course_repo.get_by_id(session, course_id) is None:
        raise BusinessException("所属课程不存在")
    if teacher_id is not None and await account_repo.get_by_id(session, teacher_id) is None:
        raise BusinessException("主讲教练不存在")


async def create_class_group(session: AsyncSession, payload: ClassGroupCreate) -> ClassGroup:
    if payload.start_date > payload.end_date:
        raise BusinessException("开始日期不能晚于结束日期")
    await _assert_refs_exist(session, payload.course_id, payload.teacher_id)
    class_group = await class_group_repo.create(session, **payload.model_dump())
    await session.commit()
    return class_group


async def get_class_group(session: AsyncSession, class_id: int) -> ClassGroup:
    class_group = await class_group_repo.get_by_id(session, class_id)
    if class_group is None:
        raise BusinessException("班级不存在", code=404)
    return class_group


async def list_class_groups(
    session: AsyncSession,
    *,
    course_id: int | None,
    status: str | None,
    teacher_id: int | None,
    page: PageParams,
    sort: str | None,
) -> tuple[list[ClassGroup], int]:
    total = await class_group_repo.count(session, course_id=course_id, status=status, teacher_id=teacher_id)
    items = await class_group_repo.list_page(
        session, course_id=course_id, status=status, teacher_id=teacher_id, page=page, sort=sort
    )
    return items, total


async def update_class_group(session: AsyncSession, class_id: int, payload: ClassGroupUpdate) -> ClassGroup:
    class_group = await class_group_repo.get_by_id(session, class_id)
    if class_group is None:
        raise BusinessException("班级不存在", code=404)
    fields = payload.model_dump(exclude_unset=True)

    # 部分更新时用现有值补齐做跨列校验（DB 的 CHECK 兜底）
    start = fields.get("start_date", class_group.start_date)
    end = fields.get("end_date", class_group.end_date)
    if start > end:
        raise BusinessException("开始日期不能晚于结束日期")
    await _assert_refs_exist(session, None, fields.get("teacher_id"))

    try:
        updated = await class_group_repo.update(session, class_id, fields)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BusinessException("数据违反约束（如容量小于已报名人数）") from exc
    return updated


async def delete_class_group(session: AsyncSession, class_id: int) -> None:
    try:
        deleted = await class_group_repo.delete(session, class_id)
        if not deleted:
            raise BusinessException("班级不存在", code=404)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BusinessException("该班级下存在关联数据（选课/订单/作业），不允许删除") from exc
