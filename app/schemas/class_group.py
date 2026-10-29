"""class_group 请求/响应 schema。"""
from datetime import date, datetime

from pydantic import ConfigDict, Field
from sqlmodel import SQLModel

from app.models.enums import ClassGroupStatus


class ClassGroupCreate(SQLModel):
    course_id: int
    name: str = Field(min_length=1, max_length=128)
    teacher_id: int
    campus: str | None = Field(default=None, max_length=64)
    start_date: date
    end_date: date
    capacity: int = Field(gt=0)


class ClassGroupUpdate(SQLModel):
    """不含 enrolled_count / version / course_id：计数与乐观锁由业务流转维护，不走通用更新。"""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    teacher_id: int | None = None
    campus: str | None = Field(default=None, max_length=64)
    start_date: date | None = None
    end_date: date | None = None
    capacity: int | None = Field(default=None, gt=0)
    status: ClassGroupStatus | None = None


class ClassGroupRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    name: str
    teacher_id: int
    campus: str | None
    start_date: date
    end_date: date
    capacity: int
    enrolled_count: int
    version: int
    status: ClassGroupStatus
    created_at: datetime
    updated_at: datetime
