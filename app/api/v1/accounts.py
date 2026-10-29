"""账号管理接口（任务 1.1 创建/详情/更新/软删除，1.2 列表分页/过滤/排序）。"""
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_session
from app.core.deps import require_role
from app.core.response import EnvelopeRoute
from app.models import Account
from app.models.enums import AccountRole, AccountStatus
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.schemas.common import Page, PageParams
from app.services import account as account_service

router = APIRouter(route_class=EnvelopeRoute, tags=["account"])


@router.post("/accounts", response_model=AccountRead)
async def create_account(
    payload: AccountCreate,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("admin")),
) -> Account:
    return await account_service.create_account(session, payload)


@router.get("/accounts", response_model=Page[AccountRead])
async def list_accounts(
    page: PageParams = Depends(),
    role: AccountRole | None = Query(None),
    status: AccountStatus | None = Query(None),
    sort: str = Query("-created_at,id", description="排序：逗号分隔，- 前缀倒序"),
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("teacher", "admin")),
) -> Page[AccountRead]:
    items, total = await account_service.list_accounts(session, role=role, status=status, page=page, sort=sort)
    # 显式逐项 model_validate：SQLModel 泛型 Page[AccountRead] 构造时不会校验 items，直接拼会泄漏 ORM 全字段
    return Page[AccountRead](
        items=[AccountRead.model_validate(item) for item in items], total=total, page=page.page, size=page.size
    )


@router.get("/accounts/{account_id}", response_model=AccountRead)
async def get_account(
    account_id: int,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("teacher", "admin")),
) -> Account:
    return await account_service.get_account(session, account_id)


@router.patch("/accounts/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: int,
    payload: AccountUpdate,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("admin")),
) -> Account:
    return await account_service.update_account(session, account_id, payload)


@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: int,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(require_role("admin")),
) -> dict:
    await account_service.soft_delete_account(session, account_id)
    return {"deleted": True}
