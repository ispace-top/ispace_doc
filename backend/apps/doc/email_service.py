# coding:utf-8
"""邮件发送服务 — 读取 SMTP 配置并通过 smtplib 发送 HTML 邮件。"""

import smtplib
from email.mime.text import MIMEText
from email.header import Header

from django.template.loader import render_to_string
from loguru import logger


class EmailService:
    """封装 SMTP 邮件发送，配置从 SysSetting 读取。"""

    @staticmethod
    def _get_config():
        """从 SysSetting 读取 SMTP 配置。"""
        from backend.apps.admin.models import SysSetting
        from backend.apps.admin.utils import dectry

        email_settings = SysSetting.objects.filter(types="email")
        config = {}
        for s in email_settings:
            config[s.name] = s.value
        # 解密密码
        if 'pwd' in config and config['pwd']:
            try:
                config['pwd'] = dectry(config['pwd'])
            except Exception:
                pass
        # 检查是否启用了邮箱
        try:
            enable = SysSetting.objects.get(name='enable_email', types='basic')
            config['enabled'] = enable.value == 'on'
        except SysSetting.DoesNotExist:
            config['enabled'] = False
        return config

    @staticmethod
    def is_enabled():
        config = EmailService._get_config()
        return config.get('enabled', False) and config.get('smtp_host') and config.get('send_emailer')

    @staticmethod
    def send_email(to_email, subject, html_body):
        """发送 HTML 邮件，返回 (success, error_msg)。"""
        config = EmailService._get_config()
        if not config.get('enabled'):
            return False, '邮件功能未启用'
        if not config.get('smtp_host') or not config.get('send_emailer'):
            return False, 'SMTP 配置不完整'

        try:
            sitename = EmailService._get_site_name()
            msg = MIMEText(html_body, _subtype='html', _charset='utf-8')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = Header(sitename, 'utf-8').encode() + ' <{}>'.format(config['send_emailer'])
            msg['To'] = to_email

            smtp_host = config['smtp_host']
            smtp_port = int(config.get('smtp_port', 465))
            use_ssl = config.get('smtp_ssl') == 'on'

            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)

            server.login(config['username'], config.get('pwd', ''))
            server.sendmail(from_addr=config['send_emailer'], to_addrs=to_email, msg=msg.as_string())
            server.quit()
            logger.info(f'邮件发送成功: {to_email} — {subject}')
            return True, None
        except smtplib.SMTPAuthenticationError:
            err = 'SMTP 认证失败，请检查用户名和密码'
            logger.error(f'邮件发送失败: {to_email} — {err}')
            return False, err
        except smtplib.SMTPException as e:
            err = f'SMTP 错误: {repr(e)}'
            logger.error(f'邮件发送失败: {to_email} — {err}')
            return False, err
        except Exception as e:
            err = f'发送异常: {repr(e)}'
            logger.error(f'邮件发送失败: {to_email} — {err}')
            return False, err

    @staticmethod
    def _get_site_name():
        try:
            from backend.apps.admin.models import SysSetting
            return SysSetting.objects.get(types='basic', name='site_name').value
        except Exception:
            return 'i·Space Doc'

    # ========== 模板化发送 ==========

    NOTIFY_TEMPLATES = {
        'comment': 'email/comment.html',
        'mention': 'email/mention.html',
        'perm_change': 'email/perm_change.html',
        'perm_apply': 'email/perm_apply.html',
        'doc_change': 'email/doc_change.html',
        'system': 'email/system.html',
    }

    @staticmethod
    def send_notification_email(to_email, subject, notification_type, context):
        """根据通知类型发送模板化的 HTML 邮件。"""
        template = EmailService.NOTIFY_TEMPLATES.get(notification_type, 'email/generic.html')
        try:
            html = render_to_string(template, context)
        except Exception:
            html = render_to_string('email/generic.html', context)
        return EmailService.send_email(to_email, subject, html)

    @staticmethod
    def send_daily_digest(to_email, notifications, unread_count, site_name='i·Space Doc'):
        """发送每日汇总邮件。"""
        html = render_to_string('email/daily_digest.html', {
            'notifications': notifications,
            'unread_count': unread_count,
            'site_name': site_name,
            'site_url': EmailService._get_site_url(),
        })
        return EmailService.send_email(to_email, f'【{site_name}】每日通知汇总', html)

    @staticmethod
    def _get_site_url():
        try:
            from django.conf import settings
            return getattr(settings, 'SITE_URL', 'http://localhost:8000')
        except Exception:
            return 'http://localhost:8000'
