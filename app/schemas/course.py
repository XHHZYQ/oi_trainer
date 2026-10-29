"""course 请求/响应 schema。"""
from datetime import datetime

from pydantic import ConfigDict, Field
from sqlmodel import SQLModel

from app.models.enums import CourseStatus


class CourseCreate(SQLModel):
    code: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=128)
    level: str = Field(max_length=16)
    description: str | None = None
    cover_url: str | None = None
    total_hours: int = Field(default=0, ge=0)
    price_cents: int = Field(default=0, ge=0)


class CourseUpdate(SQLModel):
    """全字段可选（含 code，改 code 仍受部分唯一索引约束）；status 走状态机校验。"""

    code: str | None = Field(default=None, min_length=1, max_length=32)
    title: str | None = Field(default=None, min_length=1, max_length=128)
    level: str | None = Field(default=None, max_length=16)
    description: str | None = None
    cover_url: str | None = None
    total_hours: int | None = Field(default=None, ge=0)
    price_cents: int | None = Field(default=None, ge=0)
    status: CourseStatus | None = None


class CourseRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    level: str
    description: str | None
    cover_url: str | None
    total_hours: int
    price_cents: int
    status: CourseStatus
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class CourseBatchDelete(SQLModel):
    ids: list[int] = Field(min_length=1)
