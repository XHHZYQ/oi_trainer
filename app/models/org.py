"""① 组织教务域：account / student_profile / teacher_profile / course / class_group / enrollment / enrollment_order"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlmodel import Field, SQLModel

from app.models.enums import (
    AccountRole,
    AccountStatus,
    ClassGroupStatus,
    CourseStatus,
    EnrollmentStatus,
    OrderStatus,
)


class Account(SQLModel, table=True):
    """用户主表（user 为 PG 保留字，故命名 account）。"""

    __tablename__ = "account"
    __table_args__ = (
        Index("uq_account_username", "username", unique=True),
        # 部分唯一索引：软删除后邮箱/手机号可复用
        Index("uq_account_email_active", "email", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("uq_account_phone_active", "phone", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("ix_account_role_status", "role", "status"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    username: str = Field(sa_column=Column(String(64), nullable=False))
    email: str | None = Field(default=None, sa_column=Column(String(255)))
    phone: str | None = Field(default=None, sa_column=Column(String(20)))
    hashed_password: str = Field(sa_column=Column(String(255), nullable=False))
    role: AccountRole = Field(sa_column=Column(String(16), nullable=False))
    real_name: str | None = Field(default=None, sa_column=Column(String(64)))
    avatar_url: str | None = Field(default=None, sa_column=Column(Text))
    status: AccountStatus = Field(
        default=AccountStatus.active, sa_column=Column(String(16), nullable=False, server_default="active")
    )
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class StudentProfile(SQLModel, table=True):
    """学生档案，与 account 共享主键（1:1）。"""

    __tablename__ = "student_profile"
    __table_args__ = (Index("ix_student_profile_advisor", "advisor_id"),)

    user_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("account.id", ondelete="CASCADE"), primary_key=True)
    )
    grade: str | None = Field(default=None, sa_column=Column(String(8)))
    school: str | None = Field(default=None, sa_column=Column(String(128)))
    target_level: str | None = Field(default=None, sa_column=Column(String(16)))
    oi_level: str | None = Field(default=None, sa_column=Column(String(16)))
    advisor_id: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("account.id")))
    enrolled_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    notes: str | None = Field(default=None, sa_column=Column(Text))


class TeacherProfile(SQLModel, table=True):
    """教练档案，与 account 共享主键（1:1）。"""

    __tablename__ = "teacher_profile"

    user_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("account.id", ondelete="CASCADE"), primary_key=True)
    )
    title: str | None = Field(default=None, sa_column=Column(String(32)))
    bio: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class Course(SQLModel, table=True):
    """课程。gin_course_search（pg_trgm 表达式索引）在迁移 0002 中用 op.execute 创建。"""

    __tablename__ = "course"
    __table_args__ = (
        Index("uq_course_code", "code", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("ix_course_status_level", "status", "level"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    code: str = Field(sa_column=Column(String(32), nullable=False))
    title: str = Field(sa_column=Column(String(128), nullable=False))
    level: str = Field(sa_column=Column(String(16), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text))
    cover_url: str | None = Field(default=None, sa_column=Column(Text))
    total_hours: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    price_cents: int = Field(default=0, sa_column=Column(BigInteger, nullable=False, server_default="0"))
    status: CourseStatus = Field(
        default=CourseStatus.draft, sa_column=Column(String(16), nullable=False, server_default="draft")
    )
    created_by: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("account.id")))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class ClassGroup(SQLModel, table=True):
    """班级/班次：含冗余计数 enrolled_count 与乐观锁版本号 version。"""

    __tablename__ = "class_group"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_class_group_capacity"),
        CheckConstraint("start_date <= end_date", name="ck_class_group_date_range"),
        CheckConstraint("enrolled_count >= 0 AND enrolled_count <= capacity", name="ck_class_group_enrolled_range"),
        Index("ix_class_group_course", "course_id"),
        Index("ix_class_group_teacher", "teacher_id"),
        Index("ix_class_group_status_start", "status", "start_date"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    course_id: int = Field(sa_column=Column(BigInteger, ForeignKey("course.id"), nullable=False))
    name: str = Field(sa_column=Column(String(128), nullable=False))
    teacher_id: int = Field(sa_column=Column(BigInteger, ForeignKey("account.id"), nullable=False))
    campus: str | None = Field(default=None, sa_column=Column(String(64)))
    start_date: date = Field(sa_column=Column(Date, nullable=False))
    end_date: date = Field(sa_column=Column(Date, nullable=False))
    capacity: int = Field(sa_column=Column(Integer, nullable=False))
    enrolled_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    version: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    status: ClassGroupStatus = Field(
        default=ClassGroupStatus.planned, sa_column=Column(String(16), nullable=False, server_default="planned")
    )
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )


class Enrollment(SQLModel, table=True):
    """选课记录（student <-> class 的 M:N 业务化实体）。"""

    __tablename__ = "enrollment"
    __table_args__ = (
        Index("uq_enrollment_student_class", "student_id", "class_id", unique=True),
        Index("ix_enrollment_class_status", "class_id", "status"),
        Index("ix_enrollment_student", "student_id"),
        # 可空唯一：一笔支付成功订单最多产生一条选课记录
        Index("uq_enrollment_order", "order_id", unique=True),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    student_id: int = Field(sa_column=Column(BigInteger, ForeignKey("account.id"), nullable=False))
    class_id: int = Field(sa_column=Column(BigInteger, ForeignKey("class_group.id"), nullable=False))
    order_id: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("enrollment_order.id")))
    status: EnrollmentStatus = Field(
        default=EnrollmentStatus.active, sa_column=Column(String(16), nullable=False, server_default="active")
    )
    joined_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    quit_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    final_score: Decimal | None = Field(default=None, sa_column=Column(Numeric(5, 2)))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )


class EnrollmentOrder(SQLModel, table=True):
    """报名订单：order_no / idempotency_key 双唯一键支撑幂等。"""

    __tablename__ = "enrollment_order"
    __table_args__ = (
        CheckConstraint("amount_cents >= 0", name="ck_order_amount"),
        Index("uq_order_no", "order_no", unique=True),
        Index("uq_order_idem", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
        Index("ix_order_student_time", "student_id", text("created_at DESC")),
        Index("ix_order_status_time", "status", "created_at"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    order_no: str = Field(sa_column=Column(String(32), nullable=False))
    idempotency_key: str | None = Field(default=None, sa_column=Column(String(64)))
    student_id: int = Field(sa_column=Column(BigInteger, ForeignKey("account.id"), nullable=False))
    class_id: int = Field(sa_column=Column(BigInteger, ForeignKey("class_group.id"), nullable=False))
    amount_cents: int = Field(sa_column=Column(BigInteger, nullable=False))
    status: OrderStatus = Field(
        default=OrderStatus.pending, sa_column=Column(String(16), nullable=False, server_default="pending")
    )
    channel: str | None = Field(default=None, sa_column=Column(String(16)))
    paid_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    cancelled_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    remark: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
