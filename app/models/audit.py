"""⑦ 审计域：audit_log（append-only，阶段 5 进阶做按月分区，届时主键需含分区键）"""
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    """操作审计：只写不改，与业务事务同事务写入。"""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_actor_time", "actor_id", text("created_at DESC")),
        Index("ix_audit_created", "created_at"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    actor_id: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("account.id")))
    actor_role: str | None = Field(default=None, sa_column=Column(String(16)))
    action: str = Field(sa_column=Column(String(64), nullable=False))
    entity_type: str = Field(sa_column=Column(String(32), nullable=False))
    entity_id: int | None = Field(default=None, sa_column=Column(BigInteger))
    before_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    after_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    ip: str | None = Field(default=None, sa_column=Column(String(45)))
    user_agent: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
