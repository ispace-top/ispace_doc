"""JWT 认证体系（11.1.3）。

Access Token + Refresh Token，支持 Token 黑名单（Redis）。
FastAPI 依赖注入获取当前用户。
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

# ---- 密码哈希 ----
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---- HTTP Bearer ----
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# ---- Token 生成与验证 ----

def create_access_token(user_id: int, username: str = "",
                        extra_claims: Optional[dict] = None) -> str:
    """生成 Access Token。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: int) -> str:
    """生成 Refresh Token。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    """解码并验证 Token，失败返回 None。"""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """使用 Refresh Token 获取新的 Access Token。"""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None
    return create_access_token(
        user_id=int(payload["sub"]),
        username=payload.get("username", ""),
    )


# ---- Token 黑名单（Redis） ----

async def _get_redis():
    """延迟获取 Redis 连接。"""
    import redis.asyncio as aioredis
    return aioredis.from_url(settings.redis_url)


async def blacklist_token(token: str, ttl: int = None):
    """将 Token 加入黑名单（用于登出）。"""
    if ttl is None:
        ttl = settings.jwt_access_token_expire_minutes * 60
    try:
        r = await _get_redis()
        await r.setex(f"blacklist:token:{token}", ttl, "1")
        await r.close()
    except Exception:
        pass  # Redis 不可用时静默失败


async def is_token_blacklisted(token: str) -> bool:
    """检查 Token 是否在黑名单中。"""
    try:
        r = await _get_redis()
        result = await r.exists(f"blacklist:token:{token}")
        await r.close()
        return bool(result)
    except Exception:
        return False


# ---- 当前用户依赖注入 ----

class CurrentUser:
    """从 JWT Token 中提取的当前用户信息。"""
    def __init__(self, user_id: int, username: str = ""):
        self.id = user_id
        self.username = username
        self.is_authenticated = True


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """FastAPI 依赖：从 Authorization Header 获取当前用户。"""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证 Token")

    token = credentials.credentials

    if await is_token_blacklisted(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 已失效")

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效或已过期")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 类型错误")

    return CurrentUser(user_id=int(payload["sub"]), username=payload.get("username", ""))


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CurrentUser]:
    """FastAPI 依赖：可选认证（不强制登录）。"""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
