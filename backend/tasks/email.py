"""邮件发送任务（11.2.2）。

支持：
- 单封邮件发送
- 批量通知邮件
- 每日摘要
- 找回密码邮件
"""
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_mail_async(self, subject: str, body: str, to_emails: list[str],
                    html: bool = False, from_email: str = None):
    """异步发送邮件。

    Args:
        subject: 邮件主题
        body: 邮件正文（纯文本或 HTML）
        to_emails: 收件人邮箱列表
        html: 正文是否为 HTML 格式
        from_email: 发件人地址，默认使用系统配置
    """
    try:
        from django.core.mail import EmailMultiAlternatives

        if from_email is None:
            from django.conf import settings
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@ispace.com")

        msg = EmailMultiAlternatives(
            subject=subject,
            body=body if not html else "",
            from_email=from_email,
            to=to_emails,
        )
        if html:
            msg.attach_alternative(body, "text/html")
        msg.send(fail_silently=False)
        logger.info("邮件发送成功: subject=%s, to=%s", subject, to_emails)
    except Exception as exc:
        logger.error("邮件发送失败 (attempt %d): subject=%s, error=%s",
                     self.request.retries + 1, subject, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True)
def send_daily_digest(self, user_id: int):
    """给指定用户发送每日摘要邮件。"""
    try:
        from django.contrib.auth import get_user_model
        from backend.apps.doc.services import NotificationService

        User = get_user_model()
        user = User.objects.get(pk=user_id)
        notifications = NotificationService.get_daily_digest(user)
        if not notifications:
            logger.info("用户 %s 无新通知，跳过每日摘要", user.username)
            return

        subject = f"i·Space Doc 每日摘要 — {len(notifications)} 条新动态"
        lines = []
        for n in notifications:
            lines.append(f"- {n.get('title', '新通知')}: {n.get('summary', '')}")
        body = "\n".join(lines) if lines else "今日无新动态"

        send_mail_async.delay(
            subject=subject,
            body=body,
            to_emails=[user.email],
            html=False,
        )
        logger.info("每日摘要已投递: user=%s, count=%d", user.username, len(notifications))
    except Exception as exc:
        logger.error("每日摘要生成失败: user_id=%s, error=%s", user_id, exc)
