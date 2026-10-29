"""account 请求/响应 schema。"""
from datetime import datetime

from pydantic import ConfigDict, Field
from sqlmodel import SQLModel

from app.models.enums import AccountRole, AccountStatus


class AccountCreate(SQLModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=64)
    role: AccountRole
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    real_name: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = None


class AccountUpdate(SQLModel):
    """全字段可选；服务端按 exclude_unset 取"实际传了的字段"做部分更新。"""

    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    real_name: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = None
    role: AccountRole | None = None
    status: AccountStatus | None = None
    password: str | None = Field(default=None, min_length=6, max_length=64)


class AccountRead(SQLModel):
    """响应模型：不暴露 hashed_password / deleted_at。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None
    phone: str | None
    role: AccountRole
    real_name: str | None
    avatar_url: str | None
    status: AccountStatus
    created_at: datetime
    updated_at: datetime
