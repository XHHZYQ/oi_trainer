"""⑤ 学习画像与推荐域：knowledge_mastery / study_plan，另含 gin_plan_items（jsonb_path_ops GIN）。

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_mastery",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("knowledge_point_id", sa.BigInteger(), sa.ForeignKey("knowledge_point.id"), nullable=False),
        sa.Column("mastery_score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_practiced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("mastery_score >= 0 AND mastery_score <= 100", name="ck_km_score"),
    )
    op.create_index("uq_km_student_kp", "knowledge_mastery", ["student_id", "knowledge_point_id"], unique=True)
    op.create_index("ix_km_kp_score", "knowledge_mastery", ["knowledge_point_id", "mastery_score"])

    op.create_table(
        "study_plan",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("items", JSONB(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_plan_student_date", "study_plan", ["student_id", "plan_date"], unique=True)
    op.create_index("ix_plan_date_status", "study_plan", ["plan_date", "status"])

    # JSONB GIN 索引，仅迁移层维护
    op.execute("CREATE INDEX gin_plan_items ON study_plan USING gin (items jsonb_path_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS gin_plan_items")
    op.drop_table("study_plan")
    op.drop_table("knowledge_mastery")
