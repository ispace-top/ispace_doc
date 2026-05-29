"""认证路由（登录/刷新/登出）。"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import (
    create_access_token, create_refresh_token, refresh_access_token,
    blacklist_token, get_current_user, CurrentUser, verify_password, decode_token,
)
from ..config import settings

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


def _django_authenticate(username: str, password: str):
    """桥接 Django 认证系统。"""
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.core.settings")
    import django
    django.setup()
    from django.contrib.auth import authenticate
    return authenticate(username=username, password=password)


@router.post("/login/", response_model=TokenResponse)
async def login(body: LoginRequest):
    """用户名密码登录，返回 JWT Token 对。"""
    user = _django_authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    access_token = create_access_token(user_id=user.id, username=user.username)
    refresh_token = create_refresh_token(user_id=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/refresh/", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    """使用 Refresh Token 获取新的 Token 对。"""
    new_access = refresh_access_token(body.refresh_token)
    if not new_access:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh Token 无效或已过期")

    payload = decode_token(body.refresh_token)
    user_id = int(payload["sub"])

    return TokenResponse(
        access_token=new_access,
        refresh_token=create_refresh_token(user_id=user_id),
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout/")
async def logout(user: CurrentUser = Depends(get_current_user)):
    """登出，Token 黑名单在 get_current_user 依赖中处理。"""
    return {"message": "已登出"}
