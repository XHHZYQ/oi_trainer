"""⑥ 竞赛域：contest / contest_problem / contest_participant"""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.enums import ContestStatus, ContestType


class Contest(SQLModel, table=True):
    """竞赛。"""

    __tablename__ = "contest"
    __table_args__ = (
        CheckConstraint("start_at < end_at", name="ck_contest_time_range"),
        Index("ix_contest_status_start", "status", "start_at"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    title: str = Field(sa_column=Column(String(128), nullable=False))
    course_id: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("course.id")))
    contest_type: ContestType = Field(sa_column=Column(String(16), nullable=False))
    rules: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    start_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    end_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    freeze_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    status: ContestStatus = Field(sa_column=Column(String(16), nullable=False))
    created_by: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("account.id")))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )


class ContestProblem(SQLModel, table=True):
    """竞赛 <-> 题目 M:N。"""

    __tablename__ = "contest_problem"
    __table_args__ = (
        Index("uq_cp", "contest_id", "problem_id", unique=True),
        Index("uq_cp_alias", "contest_id", "alias", unique=True),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    contest_id: int = Field(sa_column=Column(BigInteger, ForeignKey("contest.id"), nullable=False))
    problem_id: int = Field(sa_column=Column(BigInteger, ForeignKey("problem.id"), nullable=False))
    alias: str = Field(sa_column=Column(CHAR(2), nullable=False))
    order_index: int = Field(sa_column=Column(Integer, nullable=False))
    max_score: int = Field(sa_column=Column(SmallInteger, nullable=False))


class ContestParticipant(SQLModel, table=True):
    """竞赛 <-> 学生 M:N，rank 由窗口函数重算回写。"""

    __tablename__ = "contest_participant"
    __table_args__ = (Index("uq_participant", "contest_id", "student_id", unique=True),)

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    contest_id: int = Field(sa_column=Column(BigInteger, ForeignKey("contest.id"), nullable=False))
    student_id: int = Field(sa_column=Column(BigInteger, ForeignKey("account.id"), nullable=False))
    registered_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    score: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    rank: int | None = Field(default=None, sa_column=Column(Integer))
    solved_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    penalty: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
