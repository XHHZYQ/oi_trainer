"""account 数据访问：基础 CRUD + 分页/过滤/排序 + 存在性判断。

约定：本层只 flush 不 commit，事务边界由 service 控制。
"""
from datetime import datetime, timezone

from sqlalchemy import exists, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Account
from app.schemas.common import PageParams, apply_sort

SORTABLE_FIELDS = {"id", "username", "created_at"}


async def create(session: AsyncSession, **fields) -> Account:
    """INSERT；唯一约束冲突在 flush 时抛 IntegrityError，由上层兜底。"""
    account = Account(**fields)
    session.add(account)
    await session.flush()
    return account


async def get_by_id(session: AsyncSession, account_id: int) -> Account | None:
    """详情：软删除行不可见。"""
    stmt = select(Account).where(Account.id == account_id, Account.deleted_at.is_(None))
    result = await session.exec(stmt)
    return result.first()


async def get_by_username(session: AsyncSession, username: str) -> Account | None:
    stmt = select(Account).where(Account.username == username, Account.deleted_at.is_(None))
    result = await session.exec(stmt)
    return result.first()


async def exists_by_username(session: AsyncSession, username: str) -> bool:
    """SELECT EXISTS：只判断"有没有"，不把整行捞回来（任务 1.5）。"""
    stmt = select(exists(Account.id).where(Account.username == username))
    result = await session.exec(stmt)
    return bool(result.one())


def _apply_filters(stmt, *, role: str | None, status: str | None):
    stmt = stmt.where(Account.deleted_at.is_(None))
    if role is not None:
        stmt = stmt.where(Account.role == role)
    if status is not None:
        stmt = stmt.where(Account.status == status)
    return stmt


async def count(session: AsyncSession, *, role: str | None = None, status: str | None = None) -> int:
    stmt = _apply_filters(select(func.count(Account.id)), role=role, status=status)
    result = await session.exec(stmt)
    return result.one()


async def list_page(
    session: AsyncSession,
    *,
    role: str | None = None,
    status: str | None = None,
    page: PageParams,
    sort: str | None = None,
) -> list[Account]:
    """offset 分页 + 动态过滤 + 白名单排序（任务 1.2）。"""
    stmt = _apply_filters(select(Account), role=role, status=status)
    stmt = apply_sort(stmt, Account, sort, SORTABLE_FIELDS)
    stmt = stmt.limit(page.size).offset(page.offset)
    result = await session.exec(stmt)
    return list(result.all())


async def update(session: AsyncSession, account_id: int, fields: dict) -> Account | None:
    """ORM 方式 UPDATE：get -> setattr -> flush（onupdate 自动刷新 updated_at）。"""
    account = await get_by_id(session, account_id)
    if account is None:
        return None
    for key, value in fields.items():
        setattr(account, key, value)
    session.add(account)
    await session.flush()
    # onupdate=func.now() 的列在 UPDATE 后会被标记过期（PG 只对 INSERT 默认走 RETURNING），
    # 显式 refresh 取回最新 updated_at，避免事后访问属性触发隐式同步 IO
    await session.refresh(account)
    return account


async def soft_delete(session: AsyncSession, account_id: int) -> bool:
    """软删除 = 置 deleted_at；行还在，只是所有查询默认过滤掉。"""
    account = await get_by_id(session, account_id)
    if account is None:
        return False
    account.deleted_at = datetime.now(timezone.utc)
    session.add(account)
    await session.flush()
    return True
