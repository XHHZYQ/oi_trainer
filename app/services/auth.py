"""认证服务：登录签发 JWT。"""
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exceptions import BusinessException
from app.core.security import create_access_token, verify_password
from app.models.enums import AccountStatus
from app.repositories import account as account_repo
from app.schemas.auth import Token


async def login(session: AsyncSession, username: str, password: str) -> Token:
    user = await account_repo.get_by_username(session, username)
    if user is None or not verify_password(password, user.hashed_password):
        raise BusinessException("用户名或密码错误")
    if user.status != AccountStatus.active:
        raise BusinessException("账号已被禁用")
    return Token(access_token=create_access_token(user.id))
