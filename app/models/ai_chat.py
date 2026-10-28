"""④ AI 答疑域：ai_conversation / ai_message"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlmodel import Field, SQLModel

from app.models.enums import ConversationKind, MessageRole


class AiConversation(SQLModel, table=True):
    """答疑会话（冗余 message_count 与 last_message_at 避免每次 COUNT）。"""

    __tablename__ = "ai_conversation"
    __table_args__ = (
        Index("ix_conv_student_last", "student_id", text("last_message_at DESC")),
        Index("ix_conv_problem", "problem_id"),
    )

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    student_id: int = Field(sa_column=Column(BigInteger, ForeignKey("account.id"), nullable=False))
    problem_id: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("problem.id")))
    kind: ConversationKind = Field(sa_column=Column(String(16), nullable=False))
    title: str | None = Field(default=None, sa_column=Column(String(128)))
    message_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    last_message_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class AiMessage(SQLModel, table=True):
    """消息。gin_msg_content（pg_trgm GIN）在迁移 0005 中创建。"""

    __tablename__ = "ai_message"
    __table_args__ = (Index("ix_msg_conv_id", "conversation_id", "id"),)

    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    conversation_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("ai_conversation.id", ondelete="CASCADE"), nullable=False)
    )
    role: MessageRole = Field(sa_column=Column(String(16), nullable=False))
    content: str = Field(sa_column=Column(Text, nullable=False))
    model_name: str | None = Field(default=None, sa_column=Column(String(64)))
    tokens: int | None = Field(default=None, sa_column=Column(Integer))
    latency_ms: int | None = Field(default=None, sa_column=Column(Integer))
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
