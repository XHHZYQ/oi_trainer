"""② 题库知识域：knowledge_point / problem / problem_knowledge_point / tag / problem_tag / test_case
另含 problem / course 的 pg_trgm GIN 表达式索引与 hnsw_problem_embedding 向量索引。

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_point",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("parent_id", sa.BigInteger(), sa.ForeignKey("knowledge_point.id"), nullable=True),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_kp_code", "knowledge_point", ["code"], unique=True)
    op.create_index("ix_kp_parent", "knowledge_point", ["parent_id"])
    op.create_index("ix_kp_level_order", "knowledge_point", ["level", "order_index"])

    op.create_table(
        "problem",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("input_format", sa.Text(), nullable=True),
        sa.Column("output_format", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.SmallInteger(), nullable=False),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("time_limit_ms", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("memory_limit_mb", sa.Integer(), nullable=False, server_default="256"),
        sa.Column("total_submissions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_submissions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("account.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_problem_difficulty"),
    )
    op.create_index("ix_problem_status_diff_id", "problem", ["status", "difficulty", "id"])
    op.create_index("ix_problem_deleted", "problem", ["deleted_at"])

    op.create_table(
        "problem_knowledge_point",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("problem_id", sa.BigInteger(), sa.ForeignKey("problem.id", ondelete="CASCADE"), nullable=False),
        sa.Column("knowledge_point_id", sa.BigInteger(), sa.ForeignKey("knowledge_point.id"), nullable=False),
        sa.Column("weight", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("weight BETWEEN 1 AND 5", name="ck_pkp_weight"),
    )
    op.create_index("uq_pkp", "problem_knowledge_point", ["problem_id", "knowledge_point_id"], unique=True)
    op.create_index("ix_pkp_kp_problem", "problem_knowledge_point", ["knowledge_point_id", "problem_id"])

    op.create_table(
        "tag",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_tag_name_kind", "tag", ["name", "kind"], unique=True)

    # 复合主键 M:N（无代理键）
    op.create_table(
        "problem_tag",
        sa.Column("problem_id", sa.BigInteger(), sa.ForeignKey("problem.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.BigInteger(), sa.ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "test_case",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("problem_id", sa.BigInteger(), sa.ForeignKey("problem.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_index", sa.Integer(), nullable=False),
        sa.Column("input_data", sa.Text(), nullable=True),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("is_sample", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_testcase_problem_index", "test_case", ["problem_id", "case_index"], unique=True)
    op.create_index("ix_testcase_problem_sample", "test_case", ["problem_id", "is_sample"])

    # pg_trgm GIN 表达式索引（中文子串检索）与 HNSW 向量索引，仅迁移层维护
    op.execute("CREATE INDEX gin_problem_search ON problem USING gin ((title || ' ' || statement) gin_trgm_ops)")
    op.execute(
        "CREATE INDEX gin_course_search ON course USING gin ((title || ' ' || coalesce(description, '')) gin_trgm_ops)"
    )
    op.execute("CREATE INDEX hnsw_problem_embedding ON problem USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    # op.execute 创建的索引需显式删除（gin_course_search 挂在 0001 的 course 表上）
    op.execute("DROP INDEX IF EXISTS hnsw_problem_embedding")
    op.execute("DROP INDEX IF EXISTS gin_course_search")
    op.execute("DROP INDEX IF EXISTS gin_problem_search")
    op.drop_table("test_case")
    op.drop_table("problem_tag")
    op.drop_table("tag")
    op.drop_table("problem_knowledge_point")
    op.drop_table("problem")
    op.drop_table("knowledge_point")
