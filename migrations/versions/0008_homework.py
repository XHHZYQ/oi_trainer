"""⑧ 作业与人工点评域：homework / homework_problem / homework_submission / teacher_review。

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "homework",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("class_id", sa.BigInteger(), sa.ForeignKey("class_group.id"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("assigned_at < due_at", name="ck_homework_time_range"),
    )
    op.create_index("ix_homework_class_status", "homework", ["class_id", "status"])

    op.create_table(
        "homework_problem",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("homework_id", sa.BigInteger(), sa.ForeignKey("homework.id", ondelete="CASCADE"), nullable=False),
        sa.Column("problem_id", sa.BigInteger(), sa.ForeignKey("problem.id"), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("score > 0", name="ck_hp_score"),
    )
    op.create_index("uq_hp", "homework_problem", ["homework_id", "problem_id"], unique=True)
    op.create_index("ix_hp_problem", "homework_problem", ["problem_id"])

    # 外键统一 NO ACTION（成绩留痕优先，删除需应用层先清理子行）
    op.create_table(
        "homework_submission",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("homework_id", sa.BigInteger(), sa.ForeignKey("homework.id"), nullable=False),
        sa.Column("student_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("problem_id", sa.BigInteger(), sa.ForeignKey("problem.id"), nullable=False),
        sa.Column("submission_id", sa.BigInteger(), sa.ForeignKey("submission.id"), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("submit_status", sa.String(16), nullable=False),
        sa.Column("graded_by", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_hs", "homework_submission", ["homework_id", "student_id", "problem_id"], unique=True)
    op.create_index("ix_hs_homework_status", "homework_submission", ["homework_id", "submit_status"])
    op.create_index("ix_hs_student_homework", "homework_submission", ["student_id", "homework_id"])
    op.create_index("ix_hs_submission", "homework_submission", ["submission_id"])

    op.create_table(
        "teacher_review",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("submission_id", sa.BigInteger(), sa.ForeignKey("submission.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("review_type", sa.String(16), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column("score_adjustment", sa.SmallInteger(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("score_adjustment >= -100 AND score_adjustment <= 100", name="ck_tr_score_adjustment"),
    )
    op.create_index("uq_tr_submission", "teacher_review", ["submission_id"], unique=True)
    op.create_index("ix_tr_reviewer_time", "teacher_review", ["reviewer_id", sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_table("teacher_review")
    op.drop_table("homework_submission")
    op.drop_table("homework_problem")
    op.drop_table("homework")
