"""① 组织教务域：account / student_profile / teacher_profile / course / class_group / enrollment_order / enrollment

Revision ID: 0001
Revises:
Create Date: 2026-10-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 扩展：pgvector（题目向量）与 pg_trgm（中文子串检索）
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "account",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("real_name", sa.String(64), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("uq_account_username", "account", ["username"], unique=True)
    op.create_index(
        "uq_account_email_active", "account", ["email"], unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_account_phone_active", "account", ["phone"], unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_account_role_status", "account", ["role", "status"])

    op.create_table(
        "student_profile",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("account.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("grade", sa.String(8), nullable=True),
        sa.Column("school", sa.String(128), nullable=True),
        sa.Column("target_level", sa.String(16), nullable=True),
        sa.Column("oi_level", sa.String(16), nullable=True),
        sa.Column("advisor_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=True),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_student_profile_advisor", "student_profile", ["advisor_id"])

    op.create_table(
        "teacher_profile",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("account.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("title", sa.String(32), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "course",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.Column("total_hours", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_cents", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_course_code", "course", ["code"], unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_course_status_level", "course", ["status", "level"])
    # gin_course_search（pg_trgm 表达式索引）在 0002 与其他 GIN/HNSW 索引一起创建

    op.create_table(
        "class_group",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("course_id", sa.BigInteger(), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("teacher_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("campus", sa.String(64), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("enrolled_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="planned"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("capacity > 0", name="ck_class_group_capacity"),
        sa.CheckConstraint("start_date <= end_date", name="ck_class_group_date_range"),
        sa.CheckConstraint(
            "enrolled_count >= 0 AND enrolled_count <= capacity", name="ck_class_group_enrolled_range"
        ),
    )
    op.create_index("ix_class_group_course", "class_group", ["course_id"])
    op.create_index("ix_class_group_teacher", "class_group", ["teacher_id"])
    op.create_index("ix_class_group_status_start", "class_group", ["status", "start_date"])

    op.create_table(
        "enrollment_order",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("order_no", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=True),
        sa.Column("student_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("class_id", sa.BigInteger(), sa.ForeignKey("class_group.id"), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("channel", sa.String(16), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_cents >= 0", name="ck_order_amount"),
    )
    op.create_index("uq_order_no", "enrollment_order", ["order_no"], unique=True)
    op.create_index(
        "uq_order_idem", "enrollment_order", ["idempotency_key"], unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_index("ix_order_student_time", "enrollment_order", ["student_id", sa.text("created_at DESC")])
    op.create_index("ix_order_status_time", "enrollment_order", ["status", "created_at"])

    op.create_table(
        "enrollment",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("class_id", sa.BigInteger(), sa.ForeignKey("class_group.id"), nullable=False),
        sa.Column("order_id", sa.BigInteger(), sa.ForeignKey("enrollment_order.id"), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_enrollment_student_class", "enrollment", ["student_id", "class_id"], unique=True)
    op.create_index("ix_enrollment_class_status", "enrollment", ["class_id", "status"])
    op.create_index("ix_enrollment_student", "enrollment", ["student_id"])
    op.create_index("uq_enrollment_order", "enrollment", ["order_id"], unique=True)


def downgrade() -> None:
    # 表级索引/约束随表一并删除
    op.drop_table("enrollment")
    op.drop_table("enrollment_order")
    op.drop_table("class_group")
    op.drop_table("course")
    op.drop_table("teacher_profile")
    op.drop_table("student_profile")
    op.drop_table("account")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS vector")
