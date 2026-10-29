"""认证相关 schema。"""
from sqlmodel import SQLModel


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
