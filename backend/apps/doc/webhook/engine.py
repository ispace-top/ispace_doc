"""WebHook 推送引擎（纯 Python，可移植至任何框架）。

功能:
    - 事件类型定义 + JSON Payload 构建
    - HMAC-SHA256 签名（X-ISpace-Signature 头）
    - 指数退避重试（1min → 5min → 15min）
    - 并发分发（ThreadPoolExecutor）
"""
import hashlib
import hmac
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ================================================================
# 事件类型
# ================================================================

class WebHookEvent(str, Enum):
    DOC_CREATED = "doc.created"
    DOC_UPDATED = "doc.updated"
    DOC_DELETED = "doc.deleted"
    DOC_PUBLISHED = "doc.published"
    COMMENT_CREATED = "comment.created"
    COMMENT_DELETED = "comment.deleted"
    USER_REGISTERED = "user.registered"
    USER_DELETED = "user.deleted"


EVENT_LABELS = {
    WebHookEvent.DOC_CREATED: "文档创建",
    WebHookEvent.DOC_UPDATED: "文档更新",
    WebHookEvent.DOC_DELETED: "文档删除",
    WebHookEvent.DOC_PUBLISHED: "文档发布",
    WebHookEvent.COMMENT_CREATED: "评论创建",
    WebHookEvent.COMMENT_DELETED: "评论删除",
    WebHookEvent.USER_REGISTERED: "用户注册",
    WebHookEvent.USER_DELETED: "用户删除",
}


# ================================================================
# 数据模型
# ================================================================

@dataclass
class WebHookConfig:
    """WebHook 订阅配置。"""

    id: str = ""
    name: str = ""
    url: str = ""
    events: list[str] = field(default_factory=list)
    secret: str = ""
    is_enabled: bool = True
    created_at: str = ""


@dataclass
class WebHookDelivery:
    """WebHook 投递记录。"""

    id: str = ""
    config_id: str = ""
    event: str = ""
    target_url: str = ""
    request_body: str = ""
    response_status: int = 0
    response_body: str = ""
    success: bool = False
    duration_ms: int = 0
    attempt: int = 1
    created_at: str = ""


# ================================================================
# Payload 构建
# ================================================================

def build_payload(event: WebHookEvent, data: dict) -> dict:
    """构建标准 WebHook JSON 载荷。"""
    return {
        "event": event.value,
        "timestamp": int(time.time()),
        "data": data,
    }


# ================================================================
# HMAC-SHA256 签名
# ================================================================

def sign_payload(payload: bytes, secret: str) -> str:
    """对载荷进行 HMAC-SHA256 签名。"""
    mac = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256)
    return mac.hexdigest()


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """验证 WebHook 签名（接收方使用）。"""
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


# ================================================================
# WebHook 分发引擎
# ================================================================

# 重试策略：指数退避（分钟）
RETRY_DELAYS = [1 * 60, 5 * 60, 15 * 60]


class WebHookEngine:
    """WebHook 分发引擎。

    用法:
        engine = WebHookEngine(configs, on_delivery_save)

        # 事件触发时
        engine.dispatch(WebHookEvent.DOC_CREATED, {"id": 1, "title": "新文档"})
    """

    def __init__(
        self,
        get_configs: Callable[[], list[WebHookConfig]],
        on_delivery: Callable[[WebHookDelivery], None],
        max_workers: int = 5,
        request_timeout: int = 10,
    ):
        self._get_configs = get_configs
        self._on_delivery = on_delivery
        self._max_workers = max_workers
        self._request_timeout = request_timeout

    def dispatch(self, event: WebHookEvent, data: dict) -> list[WebHookDelivery]:
        """向所有匹配的订阅者分发事件。

        Returns:
            投递记录列表
        """
        configs = [c for c in self._get_configs()
                   if c.is_enabled and event.value in c.events]
        if not configs:
            return []

        payload = build_payload(event, data)
        deliveries: list[WebHookDelivery] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {
                executor.submit(self._deliver_one, cfg, event, payload): cfg
                for cfg in configs
            }
            for future in as_completed(futures):
                try:
                    delivery = future.result()
                    deliveries.append(delivery)
                except Exception as e:
                    logger.error(f"WebHook 分发异常: {e}")

        return deliveries

    def _deliver_one(self, config: WebHookConfig, event: WebHookEvent,
                     payload: dict, attempt: int = 1) -> WebHookDelivery:
        """单次投递（带重试）。"""
        import requests

        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        signature = ""
        if config.secret:
            signature = sign_payload(body_bytes, config.secret)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "iSpaceDoc-WebHook/1.0",
            "X-ISpace-Event": event.value,
            "X-ISpace-Delivery": "",
        }
        if signature:
            headers["X-ISpace-Signature"] = f"sha256={signature}"

        start = time.monotonic()
        success = False
        resp_status = 0
        resp_body = ""

        try:
            resp = requests.post(
                config.url,
                data=body_bytes,
                headers=headers,
                timeout=self._request_timeout,
            )
            resp_status = resp.status_code
            resp_body = resp.text[:1000]
            success = 200 <= resp_status < 300
        except requests.exceptions.Timeout:
            resp_body = "timeout"
        except requests.exceptions.ConnectionError as e:
            resp_body = f"connection_error: {e}"
        except Exception as e:
            resp_body = f"error: {e}"

        duration_ms = int((time.monotonic() - start) * 1000)
        delivery = WebHookDelivery(
            config_id=config.id,
            event=event.value,
            target_url=config.url,
            request_body=body_bytes.decode("utf-8", errors="replace"),
            response_status=resp_status,
            response_body=resp_body,
            success=success,
            duration_ms=duration_ms,
            attempt=attempt,
        )

        # 重试逻辑
        if not success and attempt <= len(RETRY_DELAYS):
            delay = RETRY_DELAYS[attempt - 1]
            logger.info(f"WebHook 投递失败，{delay}s 后重试 ({attempt}/{len(RETRY_DELAYS)}): {config.url}")
            time.sleep(delay)
            retry_delivery = self._deliver_one(config, event, payload, attempt + 1)
            # 合并结果：保留最后一次投递的详情
            return retry_delivery

        self._on_delivery(delivery)
        return delivery


# ================================================================
# 接收方验证工具
# ================================================================

def verify_webhook_request(
    body: bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int = 300,
) -> tuple[bool, str]:
    """验证收到的 WebHook 请求（接收方使用）。

    检验:
        1. HMAC-SHA256 签名
        2. 时间戳防重放

    Args:
        body: 请求体
        signature_header: X-ISpace-Signature 头的值
        secret: 共享密钥
        tolerance_seconds: 时间戳容差（秒）

    Returns:
        (是否通过, 错误消息)
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False, "缺少签名头"
    signature = signature_header[7:]

    if not verify_signature(body, signature, secret):
        return False, "签名验证失败"

    # 可选的时间戳验证
    try:
        payload = json.loads(body)
        ts = payload.get("timestamp", 0)
        now = int(time.time())
        if abs(now - ts) > tolerance_seconds:
            return False, f"时间戳过期 (差 {abs(now - ts)}s)"
    except (json.JSONDecodeError, KeyError):
        pass

    return True, "ok"
