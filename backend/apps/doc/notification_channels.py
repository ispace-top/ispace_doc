# coding:utf-8
"""通知通道抽象层 — 可插拔的多渠道通知发送架构。

基于 PRD §8.6 通用统一通知接口设计，支持未来接入企业微信、钉钉、OA 等第三方通道。
"""

import json as _json
from abc import ABC, abstractmethod

from django.contrib.auth.models import User
from loguru import logger

from backend.apps.doc.models import Notification


# ---------------------------------------------------------------
#  通道路由规则 — 通知类型 → 应发送的通道列表
# ---------------------------------------------------------------

NOTIFICATION_CHANNEL_ROUTES: dict[str, list[str]] = {
    'system': ['in_app', 'email'],
    'comment': ['in_app'],
    'reply': ['in_app'],
    'mention': ['in_app', 'email'],
    'doc_change': ['in_app'],
    'doc_like': ['in_app'],
    'perm_apply': ['in_app', 'email'],
    'perm_change': ['in_app', 'email'],
}

# ---------------------------------------------------------------
#  BaseNotificationChannel — 抽象基类
# ---------------------------------------------------------------


class BaseNotificationChannel(ABC):
    """通知通道抽象基类。"""

    channel_id: str = ''
    channel_name: str = ''

    @abstractmethod
    def send(self, notification: Notification, recipient: User) -> bool:
        """发送单条通知，返回是否成功。"""
        ...

    @abstractmethod
    def validate_config(self) -> bool:
        """验证通道配置是否可用。"""
        ...

    def is_available_for(self, user: User) -> bool:
        """检查用户是否启用此通道（默认所有用户启用）。"""
        return True


# ---------------------------------------------------------------
#  InAppChannel — 站内通知（已存在，适配为通道）
# ---------------------------------------------------------------


class InAppChannel(BaseNotificationChannel):
    """站内通知通道 — Notification 模型持久化（始终启用）。"""

    channel_id = 'in_app'
    channel_name = '站内通知'

    def send(self, notification: Notification, recipient: User) -> bool:
        """站内通知已在 NotificationService.send() 中创建，此处为幂等跳过。"""
        return True

    def validate_config(self) -> bool:
        return True


# ---------------------------------------------------------------
#  EmailChannel — 邮件通知
# ---------------------------------------------------------------


class EmailChannel(BaseNotificationChannel):
    """邮件通知通道 — SMTP 发送，单条即时或每日汇总。"""

    channel_id = 'email'
    channel_name = '邮件通知'

    _EMAIL_PREF_KEY_MAP: dict[str, str] = {
        'comment': 'email_comment',
        'reply': 'email_comment',
        'mention': 'email_mention',
        'doc_change': 'email_doc_change',
        'perm_change': 'email_perm_change',
        'perm_apply': 'email_perm_apply',
    }

    def send(self, notification: Notification, recipient: User) -> bool:
        """发送邮件通知。"""
        from .email_service import EmailService
        from backend.apps.admin.models import UserProfile

        if not recipient.email or not EmailService.is_enabled():
            return False

        try:
            profile = UserProfile.objects.only('notify_settings').get(user=recipient)
            settings = _json.loads(profile.notify_settings or '{}')
        except UserProfile.DoesNotExist:
            settings = {}

        if not settings.get('email_enabled', True):
            return False

        # 检查是否开启了每日汇总（daily summary 模式则在定时任务中批量发送）
        if settings.get('email_daily_summary', False):
            return True  # 标记为已处理，定时任务负责发送

        # 检查特定类型的邮件开关
        pref_key = self._EMAIL_PREF_KEY_MAP.get(notification.notification_type)
        if pref_key and not settings.get(pref_key, True):
            return False

        return self._send_email_now(notification, recipient)

    def _send_email_now(self, notification: Notification, recipient: User) -> bool:
        """立即发送单封邮件。"""
        from .email_service import EmailService

        sender_name = (notification.sender.first_name or notification.sender.username) if notification.sender else '系统'
        ctx = {
            'sender_name': sender_name,
            'site_name': EmailService._get_site_name(),
            'site_url': EmailService._get_site_url(),
            'body': notification.body,
            'title': notification.title,
            'link': notification.link,
        }

        subject = f'【{ctx["site_name"]}】{notification.title}'
        try:
            EmailService.send_notification_email(recipient.email, subject, notification.notification_type, ctx)
            return True
        except Exception:
            logger.exception(f'EmailChannel: 邮件发送失败 recipient={recipient.pk} type={notification.notification_type}')
            return False

    def validate_config(self) -> bool:
        from .email_service import EmailService
        return EmailService.is_enabled()

    def is_available_for(self, user: User) -> bool:
        try:
            from backend.apps.admin.models import UserProfile
            profile = UserProfile.objects.only('notify_settings').get(user=user)
            settings = _json.loads(profile.notify_settings or '{}')
            return settings.get('email_enabled', True)
        except Exception:
            return True


# ---------------------------------------------------------------
#  第三方通道（预留桩实现 — 后续实际接入时补充完整逻辑）
# ---------------------------------------------------------------


class WeComChannel(BaseNotificationChannel):
    """企业微信通知通道（预留）。"""

    channel_id = 'wecom'
    channel_name = '企业微信'

    def send(self, notification: Notification, recipient: User) -> bool:
        logger.info(f'[WeComChannel] 预留通道，未实际发送: recipient={recipient.pk} type={notification.notification_type}')
        return False

    def validate_config(self) -> bool:
        from backend.apps.admin.models import SysConfig
        try:
            enabled = SysConfig.objects.get(key='channel.wecom.enabled')
            return enabled.value.lower() == 'true'
        except SysConfig.DoesNotExist:
            return False

    def is_available_for(self, user: User) -> bool:
        try:
            from backend.apps.admin.models import UserProfile
            profile = UserProfile.objects.only('notify_settings').get(user=user)
            settings = _json.loads(profile.notify_settings or '{}')
            return bool(settings.get('wecom_userid'))
        except Exception:
            return False


class DingTalkChannel(BaseNotificationChannel):
    """钉钉通知通道（预留）。"""

    channel_id = 'dingtalk'
    channel_name = '钉钉'

    def send(self, notification: Notification, recipient: User) -> bool:
        logger.info(f'[DingTalkChannel] 预留通道，未实际发送: recipient={recipient.pk} type={notification.notification_type}')
        return False

    def validate_config(self) -> bool:
        from backend.apps.admin.models import SysConfig
        try:
            enabled = SysConfig.objects.get(key='channel.dingtalk.enabled')
            return enabled.value.lower() == 'true'
        except SysConfig.DoesNotExist:
            return False

    def is_available_for(self, user: User) -> bool:
        try:
            from backend.apps.admin.models import UserProfile
            profile = UserProfile.objects.only('notify_settings').get(user=user)
            settings = _json.loads(profile.notify_settings or '{}')
            return bool(settings.get('dingtalk_userid'))
        except Exception:
            return False


class OAChannel(BaseNotificationChannel):
    """企业OA通知通道（预留）。"""

    channel_id = 'oa'
    channel_name = '企业OA'

    def send(self, notification: Notification, recipient: User) -> bool:
        logger.info(f'[OAChannel] 预留通道，未实际发送: recipient={recipient.pk} type={notification.notification_type}')
        return False

    def validate_config(self) -> bool:
        from backend.apps.admin.models import SysConfig
        try:
            enabled = SysConfig.objects.get(key='channel.oa.enabled')
            return enabled.value.lower() == 'true'
        except SysConfig.DoesNotExist:
            return False

    def is_available_for(self, user: User) -> bool:
        try:
            from backend.apps.admin.models import UserProfile
            profile = UserProfile.objects.only('notify_settings').get(user=user)
            settings = _json.loads(profile.notify_settings or '{}')
            return bool(settings.get('oa_userid'))
        except Exception:
            return False


class WebhookChannel(BaseNotificationChannel):
    """Webhook 通知通道（预留）。"""

    channel_id = 'webhook'
    channel_name = 'Webhook'

    def send(self, notification: Notification, recipient: User) -> bool:
        logger.info(f'[WebhookChannel] 预留通道，未实际发送: recipient={recipient.pk} type={notification.notification_type}')
        return False

    def validate_config(self) -> bool:
        from backend.apps.admin.models import SysConfig
        try:
            url = SysConfig.objects.get(key='channel.webhook.url')
            return bool(url.value)
        except SysConfig.DoesNotExist:
            return False


# ---------------------------------------------------------------
#  NotificationChannelManager — 通道管理器
# ---------------------------------------------------------------


class NotificationChannelManager:
    """通知通道管理器 — 负责通道注册、调度与降级。

    使用方式:
        manager = NotificationChannelManager()
        manager.register(InAppChannel())
        manager.register(EmailChannel())
        manager.send(notification)  # 按路由规则分发到各通道
    """

    def __init__(self):
        self._channels: dict[str, BaseNotificationChannel] = {}

    def register(self, channel: BaseNotificationChannel):
        """注册通知通道。"""
        self._channels[channel.channel_id] = channel
        logger.debug(f'NotificationChannelManager: 已注册通道 {channel.channel_id} ({channel.channel_name})')

    def get_channel(self, channel_id: str) -> BaseNotificationChannel | None:
        return self._channels.get(channel_id)

    def send(self, notification: Notification) -> dict[str, bool]:
        """根据路由规则向各通道发送通知，返回各通道发送结果。"""
        routes = NOTIFICATION_CHANNEL_ROUTES.get(notification.notification_type, ['in_app'])
        results: dict[str, bool] = {}
        for channel_id in routes:
            channel = self._channels.get(channel_id)
            if channel is None:
                results[channel_id] = False
                continue
            if not channel.validate_config():
                results[channel_id] = False
                continue
            if not channel.is_available_for(notification.recipient):
                results[channel_id] = False
                continue
            try:
                results[channel_id] = channel.send(notification, notification.recipient)
            except Exception:
                logger.exception(f'NotificationChannelManager: 通道 {channel_id} 发送异常')
                results[channel_id] = False
        return results

    @property
    def registered_channels(self) -> list[str]:
        return list(self._channels.keys())


# ---------------------------------------------------------------
#  全局单例
# ---------------------------------------------------------------

_channel_manager: NotificationChannelManager | None = None


def get_channel_manager() -> NotificationChannelManager:
    """获取全局通道管理器单例，首次调用时自动注册内置通道。"""
    global _channel_manager
    if _channel_manager is None:
        _channel_manager = NotificationChannelManager()
        _channel_manager.register(InAppChannel())
        _channel_manager.register(EmailChannel())
        # 预留通道 — 配置未启用时 validate_config() 返回 False，不会实际发送
        _channel_manager.register(WeComChannel())
        _channel_manager.register(DingTalkChannel())
        _channel_manager.register(OAChannel())
        _channel_manager.register(WebhookChannel())
    return _channel_manager
