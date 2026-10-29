"""阶段 1 基础 CRUD 练习脚本：account / course / class_group / knowledge_point。

直连 DB 调 service/repository 层演示各知识点（与 HTTP 接口共用同一套业务逻辑）。
每次运行生成 run_id 后缀拼进 username/code，可重复执行不冲突。

运行：python -m scripts.阶段1_基础_crud
"""
import asyncio
from uuid import uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import new_session
from app.core.exceptions import BusinessException
from app.models.enums import AccountRole, CourseStatus
from app.repositories import account as account_repo
from app.schemas.account import AccountCreate, AccountUpdate
from app.schemas.common import PageParams
from app.schemas.course import CourseCreate, CourseUpdate
from app.schemas.knowledge_point import KnowledgePointCreate, KnowledgePointUpdate
from app.services import account as account_service
from app.services import course as course_service
from app.services import knowledge_point as kp_service

RUN_ID = uuid4().hex[:6]


def hr(title: str) -> None:
    print(f"\n===== {title} =====")


async def demo_account(session: AsyncSession) -> None:
    hr("1.1 用户创建/详情/更新/软删除（account）")
    username = f"demo_stu_{RUN_ID}"
    email = f"{username}@demo.local"

    stu = await account_service.create_account(
        session,
        AccountCreate(username=username, password="123456", role=AccountRole.student,
                      email=email, real_name="演示学生"),
    )
    print(f"[创建] id={stu.id} username={stu.username}")

    detail = await account_service.get_account(session, stu.id)
    print(f"[详情] username={detail.username} email={detail.email}")

    updated = await account_service.update_account(session, stu.id, AccountUpdate(real_name="演示学生-改"))
    print(f"[更新] real_name={updated.real_name} updated_at 自动刷新={updated.updated_at}")

    try:
        await account_service.create_account(
            session, AccountCreate(username=username, password="123456", role=AccountRole.student)
        )
    except BusinessException as exc:
        print(f"[唯一冲突] 重复 username 创建被拒: {exc.msg}")

    await account_service.soft_delete_account(session, stu.id)
    gone = await account_repo.get_by_id(session, stu.id)
    print(f"[软删除] deleted_at 已置位，get_by_id 返回: {gone}（None = 查询默认不可见）")

    # username 是全局唯一（不可复用）；email 是部分唯一（软删后可复用）——两种唯一策略对比
    stu2 = await account_service.create_account(
        session,
        AccountCreate(username=f"{username}_new", password="123456", role=AccountRole.student, email=email),
    )
    print(f"[部分唯一索引] 软删后同 email 重建成功: id={stu2.id}")
    await account_service.soft_delete_account(session, stu2.id)


async def demo_account_list(session: AsyncSession) -> None:
    hr("1.2 用户列表：offset 分页 + 动态过滤 + 排序（account）")
    for page_no in (1, 2):
        page = PageParams(page=page_no, size=5)
        items, total = await account_service.list_accounts(
            session, role=AccountRole.student, status=None, page=page, sort="-created_at,id"
        )
        print(f"[列表] role=student 第 {page_no} 页 total={total}: {[a.username for a in items]}")


async def demo_course(session: AsyncSession) -> None:
    hr("1.3 课程 CRUD + 状态机流转 + 软删后 code 复用（course）")
    code = f"DEMO-{RUN_ID}"
    course = await course_service.create_course(
        session, CourseCreate(code=code, title="演示课程", level="入门", price_cents=9900)
    )
    print(f"[创建] id={course.id} status={course.status}")

    for target in (CourseStatus.published, CourseStatus.archived, CourseStatus.published):
        course = await course_service.update_course(session, course.id, CourseUpdate(status=target))
        print(f"[流转] -> {course.status}")

    try:
        await course_service.update_course(session, course.id, CourseUpdate(status=CourseStatus.draft))
    except BusinessException as exc:
        print(f"[状态机] 非法流转 published->draft 被拒: {exc.msg}")

    await course_service.soft_delete_course(session, course.id)
    again = await course_service.create_course(
        session, CourseCreate(code=code, title="演示课程-重建", level="入门")
    )
    print(f"[部分唯一索引] 软删后同 code={code} 重建成功: id={again.id}")
    await course_service.soft_delete_course(session, again.id)


async def demo_batch(session: AsyncSession) -> None:
    hr("1.4 批量创建 / 批量软删除（course）")
    payloads = [
        CourseCreate(code=f"BATCH-{RUN_ID}-{i}", title=f"批量课程{i}", level="普及") for i in range(1, 4)
    ]
    courses = await course_service.create_courses_batch(session, payloads)
    ids = [c.id for c in courses]
    print(f"[批量创建] add_all 一次写入 {len(ids)} 门: {ids}")
    affected = await course_service.batch_delete_courses(session, ids)
    print(f"[批量软删除] UPDATE ... WHERE id = ANY(:ids)，affected={affected}")


async def demo_exists_count(session: AsyncSession) -> None:
    hr("1.5 存在性判断 / 计数")
    print(f"exists(admin) = {await account_repo.exists_by_username(session, 'admin')}")
    print(f"exists(not_exist_user) = {await account_repo.exists_by_username(session, 'not_exist_user')}")
    print(f"count(role=student) = {await account_repo.count(session, role=AccountRole.student)}")


async def demo_knowledge_point(session: AsyncSession) -> None:
    hr("1.6 知识点树 CRUD：自引用 + order_index 排序 + 防环（knowledge_point）")
    root = await kp_service.create_knowledge_point(
        session, KnowledgePointCreate(code=f"KP-DEMO-{RUN_ID}", name="演示专题", level="L1")
    )
    child_b = await kp_service.create_knowledge_point(
        session,
        KnowledgePointCreate(code=f"KP-DEMO-{RUN_ID}-B", name="子节点B", parent_id=root.id,
                             level="L2", order_index=1),
    )
    child_a = await kp_service.create_knowledge_point(
        session,
        KnowledgePointCreate(code=f"KP-DEMO-{RUN_ID}-A", name="子节点A", parent_id=root.id,
                             level="L2", order_index=0),
    )

    children = await kp_service.list_children(session, root.id)
    print(f"[同层排序] order_index 升序: {[c.name for c in children]}")

    try:
        await kp_service.update_knowledge_point(session, root.id, KnowledgePointUpdate(parent_id=child_a.id))
    except BusinessException as exc:
        print(f"[防环] 把父节点挂到自己的子节点下被拒: {exc.msg}")

    try:
        await kp_service.delete_knowledge_point(session, root.id)
    except BusinessException as exc:
        print(f"[删除保护] 有子节点时删除被拒: {exc.msg}")

    await kp_service.delete_knowledge_point(session, child_a.id)
    await kp_service.delete_knowledge_point(session, child_b.id)
    await kp_service.delete_knowledge_point(session, root.id)
    print("[删除] 先删子节点再删父节点，成功")


async def main() -> None:
    print(f"阶段 1 基础 CRUD 演示（run_id={RUN_ID}）")
    async with new_session() as session:
        await demo_account(session)
        await demo_account_list(session)
        await demo_course(session)
        await demo_batch(session)
        await demo_exists_count(session)
        await demo_knowledge_point(session)
    print("\n全部演示完成。")


if __name__ == "__main__":
    asyncio.run(main())
