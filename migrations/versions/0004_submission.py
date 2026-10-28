"""③ 提交判题域：submission / submission_case_result / ai_code_review
另含 gin_sub_judge_detail（jsonb_path_ops）与 gin_review_suggestions 两个 GIN 索引。

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "submission",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("problem_id", sa.BigInteger(), sa.ForeignKey("problem.id"), nullable=False),
        sa.Column("student_id", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("contest_id", sa.BigInteger(), sa.ForeignKey("contest.id"), nullable=True),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("code_hash", sa.CHAR(64), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("time_used_ms", sa.Integer(), nullable=True),
        sa.Column("memory_used_kb", sa.Integer(), nullable=True),
        sa.Column("judge_detail", JSONB(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("judged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sub_student_time", "submission", ["student_id", sa.text("submitted_at DESC")])
    op.create_index("ix_sub_problem_status", "submission", ["problem_id", "status"])
    op.create_index("ix_sub_contest_student", "submission", ["contest_id", "student_id"])
    # 部分索引：判题队列只看待判题行
    op.create_index(
        "ix_sub_pending", "submission", ["id"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    # 部分唯一索引：同学生同题同代码只允许一次提交（幂等返回依据）
    op.create_index(
        "uq_sub_code_dedup", "submission", ["student_id", "problem_id", "code_hash"], unique=True,
        postgresql_where=sa.text("code_hash IS NOT NULL"),
    )

    op.create_table(
        "submission_case_result",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("submission_id", sa.BigInteger(), sa.ForeignKey("submission.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_case_id", sa.BigInteger(), sa.ForeignKey("test_case.id"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("time_used_ms", sa.Integer(), nullable=True),
        sa.Column("memory_used_kb", sa.Integer(), nullable=True),
        sa.Column("score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_scr_submission_case", "submission_case_result", ["submission_id", "test_case_id"], unique=True)
    op.create_index("ix_scr_testcase", "submission_case_result", ["test_case_id"])

    op.create_table(
        "ai_code_review",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("submission_id", sa.BigInteger(), sa.ForeignKey("submission.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column("review_text", sa.Text(), nullable=True),
        sa.Column("error_type", sa.String(24), nullable=True),
        sa.Column("suggestions", JSONB(), nullable=True),
        sa.Column("suggested_score", sa.SmallInteger(), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        # 金额规则显式例外：模型成本（元），需亚分精度
        sa.Column("cost_cents", sa.Numeric(10, 4), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_review_submission", "ai_code_review", ["submission_id"], unique=True)
    op.create_index("ix_review_status", "ai_code_review", ["status"])

    # JSONB GIN 索引，仅迁移层维护
    op.execute("CREATE INDEX gin_sub_judge_detail ON submission USING gin (judge_detail jsonb_path_ops)")
    op.execute("CREATE INDEX gin_review_suggestions ON ai_code_review USING gin (suggestions)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS gin_review_suggestions")
    op.execute("DROP INDEX IF EXISTS gin_sub_judge_detail")
    op.drop_table("ai_code_review")
    op.drop_table("submission_case_result")
    op.drop_table("submission")
