"""Celery Beat 定时任务（11.2.3）。

- 每日摘要：汇总通知邮件
- 索引健康检查：验证搜索索引完整性
- LDAP 同步：自动同步组织用户
"""
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task
def send_daily_digest_bulk():
    """给所有启用通知的用户发送每日摘要。

    遍历有邮箱的用户，逐个投递 send_daily_digest 子任务。
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(is_active=True, email__isnull=False).exclude(email="")
        count = 0
        for user in users:
            from .email import send_daily_digest
            send_daily_digest.delay(user.pk)
            count += 1
        logger.info("每日摘要已投递 %d 个用户", count)
    except Exception as exc:
        logger.error("每日摘要批量投递失败: %s", exc)


@shared_task
def index_health_check():
    """检查搜索索引健康状态，记录文档数差异。"""
    try:
        from backend.apps.doc.models import Doc
        from django.apps import apps

        total_docs = Doc.objects.filter(is_deleted=False).count()
        has_haystack = apps.is_installed("haystack")

        if not has_haystack:
            logger.info("Haystack 未安装，跳过索引健康检查")
            return {"status": "skipped", "reason": "haystack not installed"}

        from haystack import connections
        backend = connections["default"].get_backend()
        indexed = backend.search().models(Doc).count() if hasattr(backend, "search") else -1

        result = {
            "status": "ok" if indexed >= total_docs * 0.9 else "degraded",
            "db_docs": total_docs,
            "indexed_docs": indexed,
        }
        logger.info("索引健康检查: %s", result)
        return result
    except Exception as exc:
        logger.error("索引健康检查失败: %s", exc)
        return {"status": "error", "message": str(exc)}


@shared_task
def ldap_sync():
    """LDAP 用户自动同步（需配置 LDAP，3.3.2）。"""
    try:
        from configparser import ConfigParser
        import os

        config_file = os.environ.get("ISDOC_CONFIG", "config.ini")
        parser = ConfigParser()
        parser.read(os.path.join("config", "conf", config_file), encoding="utf-8")

        if not parser.has_section("auth.ldap"):
            logger.debug("LDAP 未配置，跳过同步")
            return {"status": "skipped", "reason": "ldap not configured"}

        server_uri = parser.get("auth.ldap", "server_uri", fallback="")
        if not server_uri:
            logger.debug("LDAP server_uri 为空，跳过同步")
            return {"status": "skipped", "reason": "ldap server_uri not set"}

        logger.info("LDAP 同步已触发（完整实现在 3.3.2）")
        return {"status": "pending", "message": "LDAP sync not yet implemented"}
    except Exception as exc:
        logger.error("LDAP 同步失败: %s", exc)
        return {"status": "error", "message": str(exc)}
