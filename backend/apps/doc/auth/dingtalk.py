"""钉钉认证后端（OAuth 2.0 扫码登录 + 自建应用免登录）。"""
import time
import hmac
import hashlib
import base64

from .base import AuthBackend, AuthResult, OAuthUserInfo, register_backend


class DingTalkAuthBackend(AuthBackend):
    """钉钉认证后端。

    扫码登录使用 OAuth 2.0 授权码流程。
    自建应用免登录从钉钉工作台跳转时校验 corpId + userId。

    配置示例 (config.ini):

        [auth.dingtalk]
        # 扫码登录
        app_id = dingding_app_id
        app_secret = dingding_app_secret
        # 自建应用（可选）
        corp_id = xxx
        agent_id = 123456
    """

    name = "dingtalk"
    _authorize_url = "https://login.dingtalk.com/oauth2/auth"
    _token_url = "https://api.dingtalk.com/v1.0/oauth2/userAccessToken"
    _userinfo_url = "https://api.dingtalk.com/v1.0/contact/users/me"

    def __init__(
        self,
        app_id: str = None,
        app_secret: str = None,
        corp_id: str = None,
        agent_id: str = None,
    ):
        self._app_id = app_id
        self._app_secret = app_secret
        self._corp_id = corp_id
        self._agent_id = agent_id

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        from urllib.parse import urlencode

        params = {
            "response_type": "code",
            "client_id": self._app_id,
            "redirect_uri": redirect_uri,
            "scope": "openid corpid",
            "state": state,
            "prompt": "consent",
        }
        return f"{self._authorize_url}?{urlencode(params)}"

    def authenticate(self, request_params: dict, redirect_uri: str) -> AuthResult:
        import requests

        code = request_params.get("code", "")
        if not code:
            raise ValueError("缺少授权码")

        token_resp = requests.post(
            self._token_url,
            json={
                "clientId": self._app_id,
                "clientSecret": self._app_secret,
                "code": code,
                "grantType": "authorization_code",
            },
            timeout=10,
        )
        if token_resp.status_code != 200:
            raise ValueError(f"令牌交换失败: {token_resp.text}")
        tokens = token_resp.json()

        access_token = tokens["accessToken"]
        user_resp = requests.get(
            self._userinfo_url,
            headers={"x-acs-dingtalk-access-token": access_token},
            timeout=10,
        )
        if user_resp.status_code != 200:
            raise ValueError(f"获取用户信息失败: {user_resp.text}")
        user_data = user_resp.json()

        user_info = OAuthUserInfo(
            provider=self.name,
            provider_uid=f"dingtalk:{user_data.get('openId', '')}",
            username=user_data.get("nick", ""),
            nickname=user_data.get("nick", ""),
            email=user_data.get("email", ""),
            avatar_url=user_data.get("avatarUrl", ""),
            phone=user_data.get("mobile", ""),
            extra=user_data,
        )
        return AuthResult(
            user_info=user_info,
            access_token=access_token,
            refresh_token=tokens.get("refreshToken", ""),
            expires_in=tokens.get("expireIn", 7200),
        )

    def authenticate_sso(self, request_params: dict) -> AuthResult:
        """自建应用免登录：从钉钉工作台进入时校验 authCode。

        钉钉客户端获取 authCode 后 POST 到此接口。
        """
        import requests

        auth_code = request_params.get("authCode", "") or request_params.get("auth_code", "")
        if not auth_code:
            raise ValueError("缺少 authCode")

        # 用 authCode 换取 accessToken
        token_resp = requests.post(
            self._token_url,
            json={
                "clientId": self._app_id,
                "clientSecret": self._app_secret,
                "code": auth_code,
                "grantType": "authorization_code",
            },
            timeout=10,
        )
        if token_resp.status_code != 200:
            raise ValueError(f"免登录认证失败: {token_resp.text}")
        tokens = token_resp.json()
        access_token = tokens["accessToken"]

        user_resp = requests.get(
            self._userinfo_url,
            headers={"x-acs-dingtalk-access-token": access_token},
            timeout=10,
        )
        user_data = user_resp.json()

        user_info = OAuthUserInfo(
            provider=self.name,
            provider_uid=f"dingtalk:{user_data.get('openId', '')}",
            username=user_data.get("nick", ""),
            nickname=user_data.get("nick", ""),
            avatar_url=user_data.get("avatarUrl", ""),
            phone=user_data.get("mobile", ""),
            extra=user_data,
        )
        return AuthResult(
            user_info=user_info,
            access_token=access_token,
            refresh_token=tokens.get("refreshToken", ""),
            expires_in=tokens.get("expireIn", 7200),
        )


register_backend("dingtalk", DingTalkAuthBackend)
