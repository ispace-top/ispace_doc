"""通知渠道适配器（5.2.1-5.2.4）。

支持: 钉钉 / 企业微信 / 飞书 / Slack Incoming Webhook
"""
import json
from abc import ABC, abstractmethod
from typing import Optional

import requests


class WebhookAdapter(ABC):
    """Webhook 适配器抽象基类。"""

    name: str = "base"

    @abstractmethod
    def send(self, title: str, body: str, url: str = "",
             mentioned_users: Optional[list[str]] = None,
             mentioned_all: bool = False) -> bool:
        """发送消息到指定平台。

        Args:
            title: 消息标题
            body: 消息内容（markdown 格式）
            url: 跳转链接
            mentioned_users: @指定人列表
            mentioned_all: 是否 @所有人

        Returns:
            bool: 发送是否成功
        """
        ...


# ================================================================
# 5.2.1 钉钉机器人
# ================================================================

class DingTalkAdapter(WebhookAdapter):
    """钉钉 Webhook 机器人 — Markdown 消息格式。

    配置 (config.ini):
        [notification.dingtalk]
        webhook_url = https://oapi.dingtalk.com/robot/send?access_token=xxx
        secret = SECxxx  # 加签密钥（可选）
    """

    name = "dingtalk"

    def __init__(self, webhook_url: str, secret: str = ""):
        self._webhook_url = webhook_url
        self._secret = secret

    def send(self, title: str, body: str, url: str = "",
             mentioned_users: Optional[list[str]] = None,
             mentioned_all: bool = False) -> bool:
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"## {title}\n\n{body}\n\n" + (f"[查看详情]({url})" if url else ""),
            },
            "at": {
                "atMobiles": mentioned_users or [],
                "isAtAll": mentioned_all,
            },
        }
        try:
            resp = requests.post(self._webhook_url, json=payload, timeout=10)
            result = resp.json()
            return result.get("errcode") == 0
        except Exception:
            return False


# ================================================================
# 5.2.2 企业微信机器人
# ================================================================

class WeComBotAdapter(WebhookAdapter):
    """企业微信群机器人 — Markdown 消息格式。

    配置 (config.ini):
        [notification.wecom]
        webhook_url = https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
    """

    name = "wecom_bot"

    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    def send(self, title: str, body: str, url: str = "",
             mentioned_users: Optional[list[str]] = None,
             mentioned_all: bool = False) -> bool:
        md_content = f"# {title}\n{body}"
        if url:
            md_content += f"\n\n[点击查看]({url})"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": md_content,
            },
        }
        try:
            resp = requests.post(self._webhook_url, json=payload, timeout=10)
            result = resp.json()
            return result.get("errcode") == 0
        except Exception:
            return False


# ================================================================
# 5.2.3 飞书机器人
# ================================================================

class FeishuAdapter(WebhookAdapter):
    """飞书 Webhook 机器人 — 富文本消息格式。

    配置 (config.ini):
        [notification.feishu]
        webhook_url = https://open.feishu.cn/open-apis/bot/v2/hook/xxx
        secret = 签名校验密钥（可选）
    """

    name = "feishu"

    def __init__(self, webhook_url: str, secret: str = ""):
        self._webhook_url = webhook_url
        self._secret = secret

    def send(self, title: str, body: str, url: str = "",
             mentioned_users: Optional[list[str]] = None,
             mentioned_all: bool = False) -> bool:
        elements = [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**{title}**\n{body}"}},
        ]
        if url:
            elements.append({
                "tag": "a",
                "text": {"tag": "lark_md", "content": "查看详情"},
                "href": url,
            })

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": title}},
                "elements": elements,
            },
        }
        try:
            resp = requests.post(self._webhook_url, json=payload, timeout=10)
            result = resp.json()
            return result.get("code") == 0
        except Exception:
            return False


# ================================================================
# 5.2.4 Slack Incoming Webhook
# ================================================================

class SlackAdapter(WebhookAdapter):
    """Slack Incoming Webhook — Block Kit 消息格式。

    配置 (config.ini):
        [notification.slack]
        webhook_url = https://hooks.slack.com/services/Txxx/Bxxx/xxx
    """

    name = "slack"

    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    def send(self, title: str, body: str, url: str = "",
             mentioned_users: Optional[list[str]] = None,
             mentioned_all: bool = False) -> bool:
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": title},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": body},
            },
        ]
        if url:
            blocks.append({
                "type": "actions",
                "elements": [{
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Details"},
                    "url": url,
                }],
            })

        payload = {"blocks": blocks}
        try:
            resp = requests.post(self._webhook_url, json=payload, timeout=10)
            return resp.status_code == 200 and resp.text == "ok"
        except Exception:
            return False


# ================================================================
# 适配器工厂
# ================================================================

def create_adapter(provider: str, webhook_url: str, secret: str = "") -> Optional[WebhookAdapter]:
    """根据 provider 创建通知适配器。"""
    adapters = {
        "dingtalk": DingTalkAdapter,
        "wecom": WeComBotAdapter,
        "feishu": FeishuAdapter,
        "slack": SlackAdapter,
    }
    cls = adapters.get(provider)
    if cls is None:
        return None
    return cls(webhook_url, secret) if secret else cls(webhook_url)
