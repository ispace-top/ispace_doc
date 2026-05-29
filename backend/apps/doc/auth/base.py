"""第三方认证抽象基类。

定义统一的认证后端接口，支持 OIDC、钉钉、企业微信、LDAP 等协议的热插拔。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OAuthUserInfo:
    """OAuth 用户信息。"""

    provider: str
    provider_uid: str
    username: str = ""
    nickname: str = ""
    email: str = ""
    avatar_url: str = ""
    phone: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class AuthResult:
    """认证结果。"""

    user_info: OAuthUserInfo
    access_token: str = ""
    refresh_token: str = ""
    expires_in: int = 3600


class AuthBackend(ABC):
    """第三方认证后端抽象基类。

    子类需实现:
        get_authorize_url, authenticate
    """

    name: str = "base"

    @abstractmethod
    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        """生成 OAuth 授权页面 URL。"""

    @abstractmethod
    def authenticate(self, request_params: dict, redirect_uri: str) -> AuthResult:
        """处理 OAuth 回调，验证并获取用户信息。

        Args:
            request_params: 回调请求参数（code, state 等）
            redirect_uri: 回调地址

        Returns:
            AuthResult

        Raises:
            ValueError: 认证失败
        """

    def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """通过 access_token 获取用户信息（可选，子类按需覆盖）。"""
        return OAuthUserInfo(provider=self.name, provider_uid="")

    def refresh_token(self, refresh_token: str) -> dict:
        """刷新 access_token（可选，子类按需覆盖）。"""
        return {}

    def get_bind_url(self, state: str, redirect_uri: str) -> str:
        """获取账号绑定授权 URL（默认与登录相同）。"""
        return self.get_authorize_url(state, redirect_uri)


# 支持的认证后端注册表
AUTH_BACKENDS: dict[str, type[AuthBackend]] = {}


def register_backend(name: str, cls: type[AuthBackend]):
    """注册认证后端类。"""
    AUTH_BACKENDS[name] = cls


def get_backend_class(name: str) -> type[AuthBackend]:
    """获取已注册的认证后端类。"""
    if name not in AUTH_BACKENDS:
        raise ValueError(f"未知认证后端: {name}")
    return AUTH_BACKENDS[name]
