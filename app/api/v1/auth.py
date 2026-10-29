"""认证接口：登录 + 当前用户。"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.response import EnvelopeRoute
from app.models import Account
from app.schemas.account import AccountRead
from app.schemas.auth import Token
from app.services import auth as auth_service

router = APIRouter(route_class=EnvelopeRoute, tags=["auth"])


@router.post("/auth/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> Token:
    """表单登录（username/password），与 Swagger Authorize 按钮兼容。"""
    return await auth_service.login(session, form.username, form.password)


@router.get("/auth/me", response_model=AccountRead)
async def me(user: Account = Depends(get_current_user)) -> Account:
    return user
