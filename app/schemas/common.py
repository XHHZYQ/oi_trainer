"""通用 schema：分页参数、分页响应、排序解析。"""
from typing import Generic, TypeVar

from fastapi import Query
from sqlmodel import SQLModel

from app.core.exceptions import BusinessException

T = TypeVar("T")


class Page(SQLModel, Generic[T]):
    """通用分页响应。"""

    items: list[T]
    total: int
    page: int
    size: int


class PageParams:
    """分页查询参数依赖：?page=1&size=20。"""

    def __init__(self, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)) -> None:
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def apply_sort(stmt, model, sort: str | None, allowed: set[str]):
    """解析 sort 参数并追加 ORDER BY。

    sort 形如 "-created_at,id"：逗号分隔多字段，"-" 前缀表示 DESC。
    字段必须落在 allowed 白名单内，防止拼接任意列。
    """
    if not sort:
        return stmt
    for part in sort.split(","):
        name = part.strip()
        if not name:
            continue
        desc = name.startswith("-")
        if desc:
            name = name[1:]
        if name not in allowed:
            raise BusinessException(f"不支持的排序字段: {name}")
        column = getattr(model, name)
        stmt = stmt.order_by(column.desc() if desc else column.asc())
    return stmt
