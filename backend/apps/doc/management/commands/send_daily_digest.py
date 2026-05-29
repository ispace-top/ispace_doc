# coding:utf-8
"""每日通知汇总邮件发送命令。

用法: python manage.py send_daily_digest
可配合 cron / 计划任务使用，建议每小时执行一次。
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from loguru import logger


class Command(BaseCommand):
    help = '向启用了每日汇总的用户发送未读通知摘要邮件'

    def handle(self, *args, **options):
        from backend.apps.doc.email_service import EmailService
        from backend.apps.doc.models import Notification, UserProfile

        if not EmailService.is_enabled():
            self.stdout.write('邮件功能未启用，跳过')
            return

        now = timezone.now()
        current_hour = now.hour
        sent_count = 0

        # 遍历所有有邮箱且启用了每日汇总的用户
        for profile in UserProfile.objects.select_related('user').exclude(
            user__email=''
        ).iterator():
            try:
                import json
                settings = json.loads(profile.notify_settings or '{}')
            except (json.JSONDecodeError, TypeError):
                settings = {}

            if not settings.get('email_daily_summary'):
                continue

            # 检查当前小时是否匹配用户设定的小时（默认 9 点）
            preferred_hour = settings.get('email_daily_hour', 9)
            try:
                preferred_hour = int(preferred_hour)
            except (ValueError, TypeError):
                preferred_hour = 9

            if current_hour != preferred_hour:
                continue

            user = profile.user
            unread = Notification.objects.filter(recipient=user, is_read=False).order_by('-created_at')

            unread_count = unread.count()
            if unread_count == 0:
                continue

            # 取最近 20 条
            notifications = list(unread[:20])

            success, err = EmailService.send_daily_digest(
                to_email=user.email,
                notifications=notifications,
                unread_count=unread_count,
                site_name=EmailService._get_site_name(),
            )
            if success:
                sent_count += 1
                logger.info(f'每日汇总已发送: {user.email} ({unread_count}条)')
            else:
                logger.warning(f'每日汇总发送失败: {user.email} — {err}')

        self.stdout.write(f'每日汇总发送完成，共发送 {sent_count} 封')
