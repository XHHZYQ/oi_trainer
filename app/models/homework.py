"""⑧ 作业与人工点评域：homework / homework_problem / homework_submission / teacher_review"""
from datetime import datetime

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
    text,
)
from sqlmodel import Field, SQLModel

from app.models.enums import HomeworkStatus, HomeworkSubmitStatus, TeacherReviewType


class Homework(SQLModel, table=True):
    """作业主表：draft -> published -> closed，硬截止靠 due_at 判定。"""

    __tablename__ = "homework"
    __table_args__ = (
        CheckConstraint("assigned_at < due_at", name="ck_homework_time_range"),
        Index("ix_homework_class_status", "class_id", "status"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    class_id: int = Field(sa_column=Column(BigInteger, ForeignKey("class_group.id"), nullable=False))
    created_by: int = Field(sa_column=Column(BigInteger, ForeignKey("account.id"), nullable=False))
    title: str = Field(sa_column=Column(String(128), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text))
    assigned_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    due_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    status: HomeworkStatus = Field(
        default=HomeworkStatus.draft, sa_column=Column(String(16), nullable=False, server_default="draft")
    )
    closed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )


class HomeworkProblem(SQLModel, table=True):
    """作业 <-> 题目 M:N。"""

    __tablename__ = "homework_problem"
    __table_args__ = (
        CheckConstraint("score > 0", name="ck_hp_score"),
        Index("uq_hp", "homework_id", "problem_id", unique=True),
        Index("ix_hp_problem", "problem_id"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    homework_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("homework.id", ondelete="CASCADE"), nullable=False)
    )
    problem_id: int = Field(sa_column=Column(BigInteger, ForeignKey("problem.id"), nullable=False))
    score: int = Field(sa_column=Column(SmallInteger, nullable=False))
    is_required: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, server_default="true"))
    order_index: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))


class HomeworkSubmission(SQLModel, table=True):
    """学生作业提交记录。外键统一 NO ACTION（成绩留痕优先）。"""

    __tablename__ = "homework_submission"
    __table_args__ = (
        Index("uq_hs", "homework_id", "student_id", "problem_id", unique=True),
        Index("ix_hs_homework_status", "homework_id", "submit_status"),
        Index("ix_hs_student_homework", "student_id", "homework_id"),
        Index("ix_hs_submission", "submission_id"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    homework_id: int = Field(sa_column=Column(BigInteger, ForeignKey("homework.id"), nullable=False))
    student_id: int = Field(sa_column=Column(BigInteger, ForeignKey("account.id"), nullable=False))
    problem_id: int = Field(sa_column=Column(BigInteger, ForeignKey("problem.id"), nullable=False))
    submission_id: int = Field(sa_column=Column(BigInteger, ForeignKey("submission.id"), nullable=False))
    score: int = Field(default=0, sa_column=Column(SmallInteger, nullable=False, server_default="0"))
    submit_status: HomeworkSubmitStatus = Field(sa_column=Column(String(16), nullable=False))
    graded_by: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("account.id")))
    graded_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )


class TeacherReview(SQLModel, table=True):
    """教练人工点评，与 submission 1:1（与 ai_code_review 对称）。"""

    __tablename__ = "teacher_review"
    __table_args__ = (
        CheckConstraint("score_adjustment >= -100 AND score_adjustment <= 100", name="ck_tr_score_adjustment"),
        Index("uq_tr_submission", "submission_id", unique=True),
        Index("ix_tr_reviewer_time", "reviewer_id", text("created_at DESC")),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    submission_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("submission.id", ondelete="CASCADE"), nullable=False)
    )
    reviewer_id: int = Field(sa_column=Column(BigInteger, ForeignKey("account.id"), nullable=False))
    review_type: TeacherReviewType = Field(sa_column=Column(String(16), nullable=False))
    review_text: str = Field(sa_column=Column(Text, nullable=False))
    score_adjustment: int | None = Field(default=None, sa_column=Column(SmallInteger))
    is_read: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="false"))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
