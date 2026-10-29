"""account 业务逻辑：唯一性预检 + 唯一约束兜底 + 软删除。"""
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exceptions import BusinessException
from app.core.security import hash_password
from app.models import Account
from app.repositories import account as account_repo
from app.schemas.account import AccountCreate, AccountUpdate
from app.schemas.common import PageParams


def _conflict_to_business(exc: IntegrityError) -> BusinessException:
    """把数据库唯一约束报错翻译成可读的业务提示。"""
    detail = str(exc.orig)
    if "uq_account_username" in detail:
        return BusinessException("用户名已存在")
    if "uq_account_email_active" in detail:
        return BusinessException("邮箱已被使用")
    if "uq_account_phone_active" in detail:
        return BusinessException("手机号已被使用")
    return BusinessException("数据冲突")


async def create_account(session: AsyncSession, payload: AccountCreate) -> Account:
    # 先查后插：错误提示友好，但存在竞态窗口
    if await account_repo.exists_by_username(session, payload.username):
        raise BusinessException("用户名已存在")
    data = payload.model_dump(exclude={"password"})
    data["hashed_password"] = hash_password(payload.password)
    try:
        account = await account_repo.create(session, **data)
        await session.commit()
    except IntegrityError as exc:
        # 唯一约束兜底：并发下即使预检通过也不会写入重复数据（最终防线）
        await session.rollback()
        raise _conflict_to_business(exc) from exc
    return account


async def get_account(session: AsyncSession, account_id: int) -> Account:
    account = await account_repo.get_by_id(session, account_id)
    if account is None:
        raise BusinessException("用户不存在", code=404)
    return account


async def list_accounts(
    session: AsyncSession,
    *,
    role: str | None,
    status: str | None,
    page: PageParams,
    sort: str | None,
) -> tuple[list[Account], int]:
    total = await account_repo.count(session, role=role, status=status)
    items = await account_repo.list_page(session, role=role, status=status, page=page, sort=sort)
    return items, total


async def update_account(session: AsyncSession, account_id: int, payload: AccountUpdate) -> Account:
    fields = payload.model_dump(exclude_unset=True)
    password = fields.pop("password", None)
    if password is not None:
        fields["hashed_password"] = hash_password(password)
    try:
        account = await account_repo.update(session, account_id, fields)
        if account is None:
            raise BusinessException("用户不存在", code=404)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise _conflict_to_business(exc) from exc
    return account


async def soft_delete_account(session: AsyncSession, account_id: int) -> None:
    deleted = await account_repo.soft_delete(session, account_id)
    if not deleted:
        raise BusinessException("用户不存在", code=404)
    await session.commit()
