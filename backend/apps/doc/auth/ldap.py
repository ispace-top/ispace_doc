"""LDAP 认证后端（支持 DN 绑定 + 用户搜索两种模式）。"""
from .base import AuthBackend, AuthResult, OAuthUserInfo, register_backend


class LDAPAuthBackend(AuthBackend):
    """LDAP 认证后端。

    配置示例 (config.ini):

        [auth.ldap]
        server_uri = ldap://ldap.example.com:389
        bind_dn = cn=admin,dc=example,dc=com    ; 管理员 DN（用于搜索模式）
        bind_password = admin_password
        user_base_dn = ou=users,dc=example,dc=com
        user_filter = (uid=%(user)s)             ; %(user)s 替换为登录用户名
        username_attr = uid
        email_attr = mail
        use_tls = false
    """

    name = "ldap"

    def __init__(
        self,
        server_uri: str = "ldap://localhost:389",
        bind_dn: str = None,
        bind_password: str = None,
        user_base_dn: str = None,
        user_filter: str = "(uid=%(user)s)",
        username_attr: str = "uid",
        email_attr: str = "mail",
        use_tls: bool = False,
    ):
        self._server_uri = server_uri
        self._bind_dn = bind_dn
        self._bind_password = bind_password
        self._user_base_dn = user_base_dn
        self._user_filter = user_filter
        self._username_attr = username_attr
        self._email_attr = email_attr
        self._use_tls = use_tls

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        # LDAP 不使用 OAuth 流程，这里返回空（前端直接展示用户名密码表单）
        return ""

    def authenticate(self, request_params: dict, redirect_uri: str = "") -> AuthResult:
        """验证 LDAP 用户凭据。

        request_params 应包含:
            username: LDAP 用户名
            password: 密码
        """
        try:
            import ldap
        except ImportError:
            raise ImportError("请安装 python-ldap: pip install python-ldap")

        username = request_params.get("username", "")
        password = request_params.get("password", "")
        if not username or not password:
            raise ValueError("缺少用户名或密码")

        conn = ldap.initialize(self._server_uri)
        if self._use_tls:
            conn.start_tls_s()
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 10)

        if self._bind_dn and self._user_base_dn:
            # 搜索模式：先以管理员身份绑定，搜索用户 DN，再以用户身份绑定
            conn.simple_bind_s(self._bind_dn, self._bind_password)
            search_filter = self._user_filter % {"user": ldap.filter.escape_filter_chars(username)}
            result = conn.search_s(
                self._user_base_dn,
                ldap.SCOPE_SUBTREE,
                search_filter,
                [self._username_attr, self._email_attr, "cn", "displayName"],
            )
            if not result:
                raise ValueError("用户不存在")
            user_dn, user_attrs = result[0]
            # 验证用户密码
            conn.simple_bind_s(user_dn, password)
        else:
            # 直接绑定模式：构造 DN 尝试直接认证
            user_dn = self._bind_dn % {"user": username} if "%(user)s" in (self._bind_dn or "") else f"uid={username},{self._user_base_dn}"
            conn.simple_bind_s(user_dn, password)
            user_attrs = {}
            # 搜索自身信息
            try:
                result = conn.search_s(
                    user_dn,
                    ldap.SCOPE_BASE,
                    "(objectClass=*)",
                    [self._username_attr, self._email_attr, "cn", "displayName"],
                )
                if result:
                    user_attrs = result[0][1]
            except Exception:
                pass

        conn.unbind_s()

        def _get_attr(attrs, key):
            values = attrs.get(key, [])
            return values[0].decode("utf-8") if values else ""

        user_info = OAuthUserInfo(
            provider=self.name,
            provider_uid=f"ldap:{user_dn}",
            username=_get_attr(user_attrs, self._username_attr) or username,
            nickname=_get_attr(user_attrs, "displayName") or _get_attr(user_attrs, "cn"),
            email=_get_attr(user_attrs, self._email_attr),
        )
        return AuthResult(user_info=user_info)


register_backend("ldap", LDAPAuthBackend)
