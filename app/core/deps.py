"""认证与角色依赖：get_current_user / require_role。"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_session
from app.core.security import decode_access_token
from app.models import Account
from app.models.enums import AccountStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效或过期的登录凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> Account:
    """从 JWT 解析当前用户（过滤软删除与禁用账号）。"""
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        raise _credentials_exception()
    result = await session.exec(select(Account).where(Account.id == user_id, Account.deleted_at.is_(None)))
    user = result.first()
    if user is None or user.status != AccountStatus.active:
        raise _credentials_exception()
    return user


def require_role(*roles: str):
    """角色校验依赖工厂，如 require_role("teacher", "admin")。"""

    async def checker(user: Account = Depends(get_current_user)) -> Account:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限执行该操作")
        return user

    return checker
