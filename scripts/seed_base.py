"""阶段 0 基础种子数据（幂等，可重复执行）：

- 1 个 admin、2 个教练（含 teacher_profile）、20 个学生（含 student_profile），密码统一 123456
- 2 门课程、每门 1 个班级
- 知识点树：2 棵 3 层小树
- 50 道题（published），embedding 为确定性伪向量（同题同文本必得同向量）
- 每题 3 个测试用例

运行：python -m scripts.seed_base
"""
import asyncio
import hashlib
import math
import struct
from collections import defaultdict
from datetime import date, datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import new_session
from app.core.security import hash_password
from app.models import (
    Account,
    ClassGroup,
    Course,
    KnowledgePoint,
    Problem,
    StudentProfile,
    TeacherProfile,
    TestCase,
)
from app.models.enums import AccountRole, ClassGroupStatus, CourseStatus, ProblemStatus

PASSWORD = "123456"

# 知识点树：(code, name, parent_code, level, order_index)，2 棵 3 层小树
KP_TREE = [
    ("KP-ALG", "算法基础", None, "L1", 0),
    ("KP-ALG-REC", "递归", "KP-ALG", "L2", 0),
    ("KP-ALG-REC-ITER", "递推", "KP-ALG-REC", "L3", 0),
    ("KP-ALG-DC", "分治", "KP-ALG", "L2", 1),
    ("KP-ALG-DC-BS", "二分查找", "KP-ALG-DC", "L3", 0),
    ("KP-DS", "数据结构", None, "L1", 1),
    ("KP-DS-BT", "二叉树", "KP-DS", "L2", 0),
    ("KP-DS-BT-BST", "二叉搜索树", "KP-DS-BT", "L3", 0),
    ("KP-DS-HEAP", "堆", "KP-DS", "L2", 1),
    ("KP-DS-HEAP-PQ", "优先队列", "KP-DS-HEAP", "L3", 0),
]

# 题组：(专题名, 关联知识点 code, [基础题名...])，4 组 x 5 题 x 3 轮 = 60，取前 50
PROBLEM_GROUPS = [
    ("递归", "KP-ALG-REC", ["汉诺塔问题", "斐波那契数列", "全排列生成", "阶乘计算", "逆序输出"]),
    ("分治", "KP-ALG-DC", ["快速幂", "归并排序", "二分查找", "最接近点对", "逆序对统计"]),
    ("二叉树", "KP-DS-BT", ["二叉树遍历", "求二叉树高度", "最近公共祖先", "镜像二叉树", "叶子节点计数"]),
    ("堆", "KP-DS-HEAP", ["堆排序", "合并果子", "Top K 问题", "动态中位数", "任务调度"]),
]
ROUND_SUFFIX = ["", "（巩固练习）", "（提高练习）"]

COURSES = [
    dict(code="CSPJ-BASE", title="CSP-J 入门训练营", level="入门", total_hours=48, price_cents=299900,
         description="面向零基础学员的 CSP-J 入门课程。"),
    dict(code="CSPS-ADV", title="CSP-S 提高冲刺班", level="提高", total_hours=64, price_cents=499900,
         description="面向有一定基础学员的 CSP-S 冲刺课程。"),
]

GRADES = ["五年级", "六年级", "初一", "初二", "初三"]
TARGET_LEVELS = ["入门", "普及", "提高", "省选", "NOI"]


def make_embedding(text: str) -> list[float]:
    """确定性伪向量：sha256 摘要循环拼接填满 1024 个 uint32，缩放至 [0,1) 后 L2 归一化。"""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    raw = digest * (1024 * 4 // len(digest))  # 32 * 128 = 4096 字节
    values = [u / 2**32 for u in struct.unpack(">1024I", raw)]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


async def get_or_create(session: AsyncSession, model, stats: dict, defaults: dict | None = None, **lookup):
    """按唯一键先查再插，保证幂等。"""
    stmt = select(model)
    for key, value in lookup.items():
        stmt = stmt.where(getattr(model, key) == value)
    result = await session.exec(stmt)
    obj = result.first()
    if obj is not None:
        return obj
    obj = model(**lookup, **(defaults or {}))
    session.add(obj)
    await session.flush()
    stats[model.__tablename__] += 1
    return obj


def build_problems() -> list[tuple[str, str, str]]:
    """生成 50 道题的 (title, 专题名, 知识点 code)，确定性输出。"""
    problems = []
    for suffix in ROUND_SUFFIX:
        for topic, kp_code, titles in PROBLEM_GROUPS:
            for base in titles:
                problems.append((f"{base}{suffix}", topic, kp_code))
    return problems[:50]


async def seed() -> dict[str, int]:
    stats: dict[str, int] = defaultdict(int)
    async with new_session() as session:
        hashed = hash_password(PASSWORD)  # 密码统一，只算一次哈希

        # ---------- 账号 ----------
        admin = await get_or_create(
            session, Account, stats,
            username="admin",
            defaults=dict(email="admin@oi-trainer.local", phone="13800000000",
                          hashed_password=hashed, role=AccountRole.admin, real_name="系统管理员"),
        )
        teachers = []
        for i, (username, real_name, title) in enumerate(
            [("teacher01", "王老师", "金牌教练"), ("teacher02", "李老师", "资深教练")], start=1
        ):
            teacher = await get_or_create(
                session, Account, stats,
                username=username,
                defaults=dict(email=f"{username}@oi-trainer.local", phone=f"1380000001{i}",
                              hashed_password=hashed, role=AccountRole.teacher, real_name=real_name),
            )
            await get_or_create(
                session, TeacherProfile, stats,
                user_id=teacher.id,
                defaults=dict(title=title, bio=f"{real_name}，{title}，主讲信奥课程。"),
            )
            teachers.append(teacher)

        students = []
        for i in range(1, 21):
            username = f"student{i:02d}"
            student = await get_or_create(
                session, Account, stats,
                username=username,
                defaults=dict(email=f"{username}@oi-trainer.local", phone=f"139000000{i:02d}",
                              hashed_password=hashed, role=AccountRole.student, real_name=f"学生{i:02d}"),
            )
            await get_or_create(
                session, StudentProfile, stats,
                user_id=student.id,
                defaults=dict(grade=GRADES[i % len(GRADES)], school="示例中学",
                              target_level=TARGET_LEVELS[i % len(TARGET_LEVELS)],
                              advisor_id=teachers[i % len(teachers)].id,
                              enrolled_at=datetime(2026, 3, 1, tzinfo=timezone.utc)),
            )
            students.append(student)

        # ---------- 课程与班级 ----------
        classes = []
        for i, course_info in enumerate(COURSES):
            course = await get_or_create(
                session, Course, stats,
                code=course_info["code"],
                defaults=dict(**course_info, status=CourseStatus.published, created_by=admin.id),
            )
            cls = await get_or_create(
                session, ClassGroup, stats,
                name=f"{course.title} 1 班",
                defaults=dict(course_id=course.id, teacher_id=teachers[i].id, campus="总部校区",
                              start_date=date(2026, 3, 1), end_date=date(2026, 6, 30),
                              capacity=30, status=ClassGroupStatus.ongoing),
            )
            classes.append(cls)

        # ---------- 知识点树 ----------
        kp_by_code: dict[str, KnowledgePoint] = {}
        for code, name, parent_code, level, order_index in KP_TREE:
            kp = await get_or_create(
                session, KnowledgePoint, stats,
                code=code,
                defaults=dict(name=name, parent_id=kp_by_code[kp_parent_code].id
                              if (kp_parent_code := parent_code) else None,
                              level=level, order_index=order_index),
            )
            kp_by_code[code] = kp

        # ---------- 题目与测试用例 ----------
        case_scores = [30, 30, 40]
        for i, (title, topic, _kp_code) in enumerate(build_problems(), start=1):
            statement = (
                f"【题目描述】本题是「{topic}」专项练习：{title}。\n\n"
                "给定输入数据，请按照要求计算并输出结果。（训练平台种子数据，题面从简）"
            )
            problem = await get_or_create(
                session, Problem, stats,
                title=title,
                defaults=dict(statement=statement,
                              input_format="第一行一个整数 n（1 ≤ n ≤ 10^5）。",
                              output_format="输出一行，表示答案。",
                              difficulty=i % 5 + 1, source="OI-Trainer 自研",
                              embedding=make_embedding(title + statement),
                              status=ProblemStatus.published, created_by=admin.id),
            )
            for case_index in (1, 2, 3):
                await get_or_create(
                    session, TestCase, stats,
                    problem_id=problem.id, case_index=case_index,
                    defaults=dict(input_data=f"# 题目《{title}》用例 {case_index} 输入",
                                  expected_output=f"# 题目《{title}》用例 {case_index} 期望输出",
                                  is_sample=(case_index == 1), score=case_scores[case_index - 1]),
                )

        await session.commit()
    return stats


def main() -> None:
    stats = asyncio.run(seed())
    print("种子数据写入汇总（新增行数，幂等跳过的不计数）：")
    for table in sorted(stats):
        print(f"  {table}: {stats[table]} 行")
    print("完成。")


if __name__ == "__main__":
    main()
