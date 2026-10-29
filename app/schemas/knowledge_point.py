"""knowledge_point 请求/响应 schema。"""
from datetime import datetime

from pydantic import ConfigDict, Field
from sqlmodel import SQLModel


class KnowledgePointCreate(SQLModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    parent_id: int | None = None
    level: str = Field(max_length=16)
    description: str | None = None
    order_index: int = 0


class KnowledgePointUpdate(SQLModel):
    """全字段可选；显式传 parent_id=null 表示移动到根节点。"""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    parent_id: int | None = None
    level: str | None = Field(default=None, max_length=16)
    description: str | None = None
    order_index: int | None = None


class KnowledgePointRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    parent_id: int | None
    level: str
    description: str | None
    order_index: int
    created_at: datetime
    updated_at: datetime
    children: list["KnowledgePointRead"] = []


KnowledgePointRead.model_rebuild()
