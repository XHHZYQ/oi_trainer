"""⑥ 竞赛域：contest / contest_problem / contest_participant（须在 submission 之前，submission.contest_id 引用 contest）

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contest",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("course_id", sa.BigInteger(), sa.ForeignKey("course.id"), nullable=True),
        sa.Column("contest_type", sa.String(16), nullable=False),
        sa.Column("rules", JSONB(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("freeze_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("start_at < end_at", name="ck_contest_time_range"),
    )
    op.create_index("ix_contest_status_start", "contest", ["status", "start_at"])

    op.create_table(
        "contest_problem",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("contest_id", sa.BigInteger(), sa.ForeignKey("contest.id"), nullable=False),
        sa.Column("problem_id", sa.BigInteger(), sa.ForeignKey("problem.id"), nullable=False),
        sa.Column("alias", sa.CHAR(2), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("max_score", sa.SmallInteger(), nullable=False),
    )
    op.create_index("uq_cp", "contest_problem", ["contest_id", "problem_id"], unique=True)
    op.create_index("uq_cp_alias", "contest_problem", ["contest_id", "alias"], unique=True)

    op.create_table(
        "contest_participant",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("contest_id", sa.BigInteger(), sa.ForeignKey("contest.id"), nullable=False),
        sa.Column("student_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("solved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("penalty", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("uq_participant", "contest_participant", ["contest_id", "student_id"], unique=True)


def downgrade() -> None:
    op.drop_table("contest_participant")
    op.drop_table("contest_problem")
    op.drop_table("contest")
