"""OIDC 认证后端（支持 Keycloak / Auth0 / Azure AD / Okta）。"""
from .base import AuthBackend, AuthResult, OAuthUserInfo, register_backend


class OIDCAuthBackend(AuthBackend):
    """OIDC 认证后端。

    配置示例 (config.ini):

        [auth.oidc]
        provider_name = Keycloak        ; 显示名称
        discovery_url = https://keycloak.example.com/realms/myrealm/.well-known/openid-configuration
        client_id = ispace-doc
        client_secret = xxx
        scope = openid profile email

        或直接指定端点（不使用 discovery）:
        authorize_url = https://...
        token_url = https://...
        userinfo_url = https://...
    """

    name = "oidc"

    def __init__(
        self,
        provider_name: str = "OIDC",
        discovery_url: str = None,
        client_id: str = None,
        client_secret: str = None,
        authorize_url: str = None,
        token_url: str = None,
        userinfo_url: str = None,
        scope: str = "openid profile email",
        logout_url: str = None,
    ):
        self._provider_name = provider_name
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope
        self._logout_url = logout_url

        if discovery_url:
            import requests

            resp = requests.get(discovery_url, timeout=10)
            resp.raise_for_status()
            config = resp.json()
            self._authorize_url = config["authorization_endpoint"]
            self._token_url = config["token_endpoint"]
            self._userinfo_url = config["userinfo_endpoint"]
            if not logout_url and "end_session_endpoint" in config:
                self._logout_url = config["end_session_endpoint"]
        else:
            self._authorize_url = authorize_url
            self._token_url = token_url
            self._userinfo_url = userinfo_url

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "scope": self._scope,
            "state": state,
        }
        query = "&".join(f"{k}={_urlencode(v)}" for k, v in params.items())
        return f"{self._authorize_url}?{query}"

    def authenticate(self, request_params: dict, redirect_uri: str) -> AuthResult:
        import requests

        code = request_params.get("code", "")
        if not code:
            raise ValueError("缺少授权码")

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        token_resp = requests.post(self._token_url, data=token_data, timeout=10)
        if token_resp.status_code != 200:
            raise ValueError(f"令牌交换失败: {token_resp.text}")
        tokens = token_resp.json()

        access_token = tokens["access_token"]
        user_resp = requests.get(
            self._userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if user_resp.status_code != 200:
            raise ValueError(f"获取用户信息失败: {user_resp.text}")
        user_data = user_resp.json()

        user_info = OAuthUserInfo(
            provider=self.name,
            provider_uid=user_data.get("sub", ""),
            username=user_data.get("preferred_username", "") or user_data.get("sub", ""),
            nickname=user_data.get("name", "") or user_data.get("nickname", ""),
            email=user_data.get("email", ""),
            avatar_url=user_data.get("picture", ""),
            extra=user_data,
        )
        return AuthResult(
            user_info=user_info,
            access_token=access_token,
            refresh_token=tokens.get("refresh_token", ""),
            expires_in=tokens.get("expires_in", 3600),
        )


def _urlencode(s: str) -> str:
    from urllib.parse import quote

    return quote(str(s), safe="")


register_backend("oidc", OIDCAuthBackend)
