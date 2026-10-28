"""⑤ 学习画像与推荐域：knowledge_mastery / study_plan"""
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.enums import StudyPlanStatus


class KnowledgeMastery(SQLModel, table=True):
    """学生 x 知识点掌握度（UPSERT 目标键：uq_km_student_kp）。"""

    __tablename__ = "knowledge_mastery"
    __table_args__ = (
        CheckConstraint("mastery_score >= 0 AND mastery_score <= 100", name="ck_km_score"),
        Index("uq_km_student_kp", "student_id", "knowledge_point_id", unique=True),
        Index("ix_km_kp_score", "knowledge_point_id", "mastery_score"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    student_id: int = Field(sa_column=Column(BigInteger, ForeignKey("account.id"), nullable=False))
    knowledge_point_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("knowledge_point.id"), nullable=False)
    )
    mastery_score: int = Field(default=0, sa_column=Column(SmallInteger, nullable=False, server_default="0"))
    attempts: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    accepted_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    last_practiced_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )


class StudyPlan(SQLModel, table=True):
    """AI 个性化训练计划（每日一份）。gin_plan_items（jsonb_path_ops GIN）在迁移 0006 中创建。"""

    __tablename__ = "study_plan"
    __table_args__ = (
        Index("uq_plan_student_date", "student_id", "plan_date", unique=True),
        Index("ix_plan_date_status", "plan_date", "status"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    student_id: int = Field(sa_column=Column(BigInteger, ForeignKey("account.id"), nullable=False))
    plan_date: date = Field(sa_column=Column(Date, nullable=False))
    items: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    summary: str | None = Field(default=None, sa_column=Column(Text))
    status: StudyPlanStatus = Field(
        default=StudyPlanStatus.active, sa_column=Column(String(16), nullable=False, server_default="active")
    )
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
