"""企业微信认证后端（OAuth 2.0 扫码登录 + 自建应用免登录）。"""
from .base import AuthBackend, AuthResult, OAuthUserInfo, register_backend


class WeComAuthBackend(AuthBackend):
    """企业微信认证后端。

    配置示例 (config.ini):

        [auth.wecom]
        # 扫码登录 OAuth 2.0
        corp_id = ww1234567890abcdef
        corp_secret = xxx
        agent_id = 1000001
        # 自建应用免登录
        # token 和 encoding_aes_key 用于接收企微消息
        token = mytoken
        encoding_aes_key = xxx
    """

    name = "wecom"
    _authorize_url = "https://open.work.weixin.qq.com/wwopen/sso/qrConnect"
    _token_url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    _userinfo_url = "https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo"
    _user_detail_url = "https://qyapi.weixin.qq.com/cgi-bin/user/get"

    def __init__(
        self,
        corp_id: str = None,
        corp_secret: str = None,
        agent_id: str = None,
    ):
        self._corp_id = corp_id
        self._corp_secret = corp_secret
        self._agent_id = agent_id

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        from urllib.parse import urlencode

        params = {
            "appid": self._corp_id,
            "agentid": self._agent_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{self._authorize_url}?{urlencode(params)}"

    def _get_access_token(self) -> str:
        """获取企业微信 API access_token。"""
        import requests

        resp = requests.get(
            self._token_url,
            params={"corpid": self._corp_id, "corpsecret": self._corp_secret},
            timeout=10,
        )
        data = resp.json()
        if data.get("errcode", -1) != 0:
            raise ValueError(f"获取企业微信 access_token 失败: {data.get('errmsg', '')}")
        return data["access_token"]

    def authenticate(self, request_params: dict, redirect_uri: str) -> AuthResult:
        import requests

        code = request_params.get("code", "")
        if not code:
            raise ValueError("缺少授权码")

        access_token = self._get_access_token()

        # 获取 userId
        user_resp = requests.get(
            self._userinfo_url,
            params={"access_token": access_token, "code": code},
            timeout=10,
        )
        user_data = user_resp.json()
        if user_data.get("errcode", -1) != 0:
            raise ValueError(f"获取用户信息失败: {user_data.get('errmsg', '')}")
        user_id = user_data.get("UserId", "")

        # 获取用户详情
        detail_resp = requests.get(
            self._user_detail_url,
            params={"access_token": access_token, "userid": user_id},
            timeout=10,
        )
        detail = detail_resp.json()

        user_info = OAuthUserInfo(
            provider=self.name,
            provider_uid=f"wecom:{self._corp_id}:{user_id}",
            username=detail.get("name", user_id),
            nickname=detail.get("name", ""),
            email=detail.get("email", ""),
            avatar_url=detail.get("avatar", ""),
            phone=detail.get("mobile", ""),
            extra=detail,
        )
        return AuthResult(
            user_info=user_info,
            access_token=access_token,
        )

    def authenticate_sso(self, request_params: dict) -> AuthResult:
        """自建应用免登录：从企业微信工作台进入。

        企微客户端通过 OAuth 2.0 静默授权获取 code，回传到此接口。
        """
        return self.authenticate(request_params, "")


register_backend("wecom", WeComAuthBackend)
