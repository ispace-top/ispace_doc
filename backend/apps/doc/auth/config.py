"""认证后端配置加载器。

从 config.ini 读取认证相关配置，初始化并返回对应的 AuthBackend 实例。
各后端 SDK 采用延迟导入，仅在配置启用时才加载。
"""
import configparser
import os
from typing import Optional

from django.conf import settings

from .base import AuthBackend

CONFIG_PATH = os.environ.get("ISDOC_CONFIG", os.path.join(settings.BASE_DIR, "config", "conf", "config.ini"))


def _read_config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH, encoding="utf-8")
    return parser


def build_auth_backend(name: str) -> AuthBackend:
    """根据配置构建认证后端实例。

    配置示例 (config.ini):

        [auth.oidc]
        provider_name = Keycloak
        discovery_url = https://keycloak.example.com/realms/myrealm/.well-known/openid-configuration
        client_id = ispace-doc
        client_secret = xxx
    """
    parser = _read_config()
    section = f"auth.{name}"

    if name == "oidc":
        from .oidc import OIDCAuthBackend

        return OIDCAuthBackend(
            provider_name=parser.get(section, "provider_name", fallback="OIDC"),
            discovery_url=parser.get(section, "discovery_url", fallback=None),
            client_id=parser.get(section, "client_id", fallback=None),
            client_secret=parser.get(section, "client_secret", fallback=None),
            authorize_url=parser.get(section, "authorize_url", fallback=None),
            token_url=parser.get(section, "token_url", fallback=None),
            userinfo_url=parser.get(section, "userinfo_url", fallback=None),
            scope=parser.get(section, "scope", fallback="openid profile email"),
            logout_url=parser.get(section, "logout_url", fallback=None),
        )

    if name == "dingtalk":
        from .dingtalk import DingTalkAuthBackend

        return DingTalkAuthBackend(
            app_id=parser.get(section, "app_id", fallback=None),
            app_secret=parser.get(section, "app_secret", fallback=None),
            corp_id=parser.get(section, "corp_id", fallback=None),
            agent_id=parser.get(section, "agent_id", fallback=None),
        )

    if name == "wecom":
        from .wecom import WeComAuthBackend

        return WeComAuthBackend(
            corp_id=parser.get(section, "corp_id", fallback=None),
            corp_secret=parser.get(section, "corp_secret", fallback=None),
            agent_id=parser.get(section, "agent_id", fallback=None),
        )

    if name == "ldap":
        from .ldap import LDAPAuthBackend

        return LDAPAuthBackend(
            server_uri=parser.get(section, "server_uri", fallback="ldap://localhost:389"),
            bind_dn=parser.get(section, "bind_dn", fallback=None),
            bind_password=parser.get(section, "bind_password", fallback=None),
            user_base_dn=parser.get(section, "user_base_dn", fallback=None),
            user_filter=parser.get(section, "user_filter", fallback="(uid=%(user)s)"),
            username_attr=parser.get(section, "username_attr", fallback="uid"),
            email_attr=parser.get(section, "email_attr", fallback="mail"),
            use_tls=parser.getboolean(section, "use_tls", fallback=False),
        )

    raise ValueError(f"未知认证后端: {name}")


def get_enabled_backends() -> list[str]:
    """获取已启用的认证后端列表。

    检查规则（按优先级）：
    1. 如果 config section 不存在 → 禁用
    2. 如果 section 中有 enabled=false → 禁用
    3. 否则 → 启用（section 存在且无 enabled 字段时默认为 true，向后兼容）
    """
    parser = _read_config()
    backends = []
    for name in ["oidc", "dingtalk", "wecom", "ldap"]:
        section = f"auth.{name}"
        if not parser.has_section(section):
            continue
        enabled = parser.getboolean(section, "enabled", fallback=True)
        if enabled:
            backends.append(name)
    return backends


# 后端实例缓存
_instances: dict[str, AuthBackend] = {}


def get_auth_backend(name: str) -> AuthBackend:
    """获取指定认证后端实例（带缓存）。"""
    if name not in _instances:
        _instances[name] = build_auth_backend(name)
    return _instances[name]


def reset_auth():
    """重置认证后端缓存（测试用）。"""
    global _instances
    _instances = {}
