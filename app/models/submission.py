"""③ 提交判题域：submission / submission_case_result / ai_code_review"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.enums import AiReviewStatus, ReviewErrorType, SubmissionLanguage, SubmissionStatus


class Submission(SQLModel, table=True):
    """提交记录（高频写入）。gin_sub_judge_detail（jsonb_path_ops GIN）在迁移 0004 中创建。"""

    __tablename__ = "submission"
    __table_args__ = (
        Index("ix_sub_student_time", "student_id", text("submitted_at DESC")),
        Index("ix_sub_problem_status", "problem_id", "status"),
        Index("ix_sub_contest_student", "contest_id", "student_id"),
        # 部分索引：只为待判题行建索引（判题队列拉取）
        Index("ix_sub_pending", "id", postgresql_where=text("status = 'pending'")),
        # 部分唯一索引：同学生同题同代码只允许一次提交（幂等返回依据）
        Index(
            "uq_sub_code_dedup",
            "student_id",
            "problem_id",
            "code_hash",
            unique=True,
            postgresql_where=text("code_hash IS NOT NULL"),
        ),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    problem_id: int = Field(sa_column=Column(BigInteger, ForeignKey("problem.id"), nullable=False))
    student_id: int = Field(sa_column=Column(BigInteger, ForeignKey("account.id"), nullable=False))
    contest_id: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("contest.id")))
    language: SubmissionLanguage = Field(sa_column=Column(String(16), nullable=False))
    code: str = Field(sa_column=Column(Text, nullable=False))
    code_hash: str | None = Field(default=None, sa_column=Column(CHAR(64)))
    status: SubmissionStatus = Field(
        default=SubmissionStatus.pending, sa_column=Column(String(24), nullable=False, server_default="pending")
    )
    score: int = Field(default=0, sa_column=Column(SmallInteger, nullable=False, server_default="0"))
    time_used_ms: int | None = Field(default=None, sa_column=Column(Integer))
    memory_used_kb: int | None = Field(default=None, sa_column=Column(Integer))
    judge_detail: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    submitted_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    judged_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class SubmissionCaseResult(SQLModel, table=True):
    """逐测试点结果。"""

    __tablename__ = "submission_case_result"
    __table_args__ = (
        Index("uq_scr_submission_case", "submission_id", "test_case_id", unique=True),
        Index("ix_scr_testcase", "test_case_id"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    submission_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("submission.id", ondelete="CASCADE"), nullable=False)
    )
    test_case_id: int = Field(sa_column=Column(BigInteger, ForeignKey("test_case.id"), nullable=False))
    status: str = Field(sa_column=Column(String(24), nullable=False))
    time_used_ms: int | None = Field(default=None, sa_column=Column(Integer))
    memory_used_kb: int | None = Field(default=None, sa_column=Column(Integer))
    score: int = Field(default=0, sa_column=Column(SmallInteger, nullable=False, server_default="0"))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class AiCodeReview(SQLModel, table=True):
    """AI 代码点评，与 submission 1:1。gin_review_suggestions 在迁移 0004 中创建。"""

    __tablename__ = "ai_code_review"
    __table_args__ = (
        Index("uq_review_submission", "submission_id", unique=True),
        Index("ix_review_status", "status"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    submission_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("submission.id", ondelete="CASCADE"), nullable=False)
    )
    model_name: str | None = Field(default=None, sa_column=Column(String(64)))
    prompt_version: str | None = Field(default=None, sa_column=Column(String(32)))
    review_text: str | None = Field(default=None, sa_column=Column(Text))
    error_type: ReviewErrorType | None = Field(default=None, sa_column=Column(String(24)))
    suggestions: list | None = Field(default=None, sa_column=Column(JSONB))
    suggested_score: int | None = Field(default=None, sa_column=Column(SmallInteger))
    tokens_input: int | None = Field(default=None, sa_column=Column(Integer))
    tokens_output: int | None = Field(default=None, sa_column=Column(Integer))
    # 金额规则显式例外：模型成本（元），需亚分精度，用 NUMERIC(10,4)
    cost_cents: Decimal | None = Field(default=None, sa_column=Column(Numeric(10, 4)))
    latency_ms: int | None = Field(default=None, sa_column=Column(Integer))
    status: AiReviewStatus = Field(
        default=AiReviewStatus.pending, sa_column=Column(String(16), nullable=False, server_default="pending")
    )
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
