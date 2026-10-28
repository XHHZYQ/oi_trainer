"""② 题库知识域：knowledge_point / problem / problem_knowledge_point / tag / problem_tag / test_case"""
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlmodel import Field, SQLModel

from app.models.enums import ProblemStatus


class KnowledgePoint(SQLModel, table=True):
    """知识点（树形自引用）。"""

    __tablename__ = "knowledge_point"
    __table_args__ = (
        Index("uq_kp_code", "code", unique=True),
        Index("ix_kp_parent", "parent_id"),
        Index("ix_kp_level_order", "level", "order_index"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    code: str = Field(sa_column=Column(String(64), nullable=False))
    name: str = Field(sa_column=Column(String(128), nullable=False))
    parent_id: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("knowledge_point.id")))
    level: str = Field(sa_column=Column(String(16), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text))
    order_index: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )


class Problem(SQLModel, table=True):
    """题目。

    gin_problem_search（pg_trgm 表达式索引）与 hnsw_problem_embedding（HNSW 向量索引）
    只在迁移 0002 中用 op.execute 创建，模型不声明。
    """

    __tablename__ = "problem"
    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_problem_difficulty"),
        Index("ix_problem_status_diff_id", "status", "difficulty", "id"),
        Index("ix_problem_deleted", "deleted_at"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    title: str = Field(sa_column=Column(String(255), nullable=False))
    statement: str = Field(sa_column=Column(Text, nullable=False))
    input_format: str | None = Field(default=None, sa_column=Column(Text))
    output_format: str | None = Field(default=None, sa_column=Column(Text))
    difficulty: int = Field(sa_column=Column(SmallInteger, nullable=False))
    source: str | None = Field(default=None, sa_column=Column(String(64)))
    source_url: str | None = Field(default=None, sa_column=Column(Text))
    time_limit_ms: int = Field(default=1000, sa_column=Column(Integer, nullable=False, server_default="1000"))
    memory_limit_mb: int = Field(default=256, sa_column=Column(Integer, nullable=False, server_default="256"))
    total_submissions: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    accepted_submissions: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    embedding: list[float] | None = Field(default=None, sa_column=Column(Vector(1024)))
    status: ProblemStatus = Field(
        default=ProblemStatus.draft, sa_column=Column(String(16), nullable=False, server_default="draft")
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


class ProblemKnowledgePoint(SQLModel, table=True):
    """题目 <-> 知识点 M:N（代理键风格，weight 表示考察权重）。"""

    __tablename__ = "problem_knowledge_point"
    __table_args__ = (
        CheckConstraint("weight BETWEEN 1 AND 5", name="ck_pkp_weight"),
        Index("uq_pkp", "problem_id", "knowledge_point_id", unique=True),
        Index("ix_pkp_kp_problem", "knowledge_point_id", "problem_id"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    problem_id: int = Field(sa_column=Column(BigInteger, ForeignKey("problem.id", ondelete="CASCADE"), nullable=False))
    knowledge_point_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("knowledge_point.id"), nullable=False)
    )
    weight: int = Field(default=1, sa_column=Column(SmallInteger, nullable=False, server_default="1"))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class Tag(SQLModel, table=True):
    """自由标签。"""

    __tablename__ = "tag"
    __table_args__ = (Index("uq_tag_name_kind", "name", "kind", unique=True),)

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    name: str = Field(sa_column=Column(String(32), nullable=False))
    kind: str = Field(sa_column=Column(String(16), nullable=False))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class ProblemTag(SQLModel, table=True):
    """题目 <-> 标签 M:N（复合主键风格，无代理键）。"""

    __tablename__ = "problem_tag"

    problem_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("problem.id", ondelete="CASCADE"), primary_key=True)
    )
    tag_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)
    )


class TestCase(SQLModel, table=True):
    """测试用例（删题级联删除）。"""

    __tablename__ = "test_case"
    __table_args__ = (
        Index("uq_testcase_problem_index", "problem_id", "case_index", unique=True),
        Index("ix_testcase_problem_sample", "problem_id", "is_sample"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    problem_id: int = Field(sa_column=Column(BigInteger, ForeignKey("problem.id", ondelete="CASCADE"), nullable=False))
    case_index: int = Field(sa_column=Column(Integer, nullable=False))
    input_data: str | None = Field(default=None, sa_column=Column(Text))
    expected_output: str | None = Field(default=None, sa_column=Column(Text))
    is_sample: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="false"))
    score: int = Field(default=0, sa_column=Column(SmallInteger, nullable=False, server_default="0"))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
