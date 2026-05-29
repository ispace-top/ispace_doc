"""WebHook Django 信号处理 — 将文档事件转换为 WebHook 推送。

连接 Django 模型信号，当文档/评论/用户发生变更时，自动触发 WebHook 分发。
"""
import logging

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .engine import WebHookEvent

logger = logging.getLogger(__name__)


def _get_engine():
    """延迟获取 WebHook 引擎实例（避免循环导入）。"""
    from .views import _get_engine as _v_engine

    return _v_engine()


@receiver(post_save, sender="app_doc.Doc")
def on_doc_save(sender, instance, created, **kwargs):
    """文档保存时触发 WebHook。"""
    if instance.status not in (0, 1):
        return

    from django.utils import timezone

    engine = _get_engine()
    data = {
        "id": instance.id,
        "name": instance.name,
        "status": instance.status,
        "create_user_id": instance.create_user_id,
        "modify_time": instance.modify_time.isoformat() if instance.modify_time else "",
    }

    if created:
        engine.dispatch(WebHookEvent.DOC_CREATED, data)
    elif instance.status == 1:
        engine.dispatch(WebHookEvent.DOC_PUBLISHED, data)
    else:
        engine.dispatch(WebHookEvent.DOC_UPDATED, data)


@receiver(post_save, sender="app_doc.DocComment")
def on_comment_save(sender, instance, created, **kwargs):
    """评论创建时触发 WebHook。"""
    if not created:
        return

    engine = _get_engine()
    data = {
        "id": instance.id,
        "doc_id": instance.doc_id,
        "author": instance.user.username if instance.user else "",
        "content": instance.content[:200] if instance.content else "",
    }
    engine.dispatch(WebHookEvent.COMMENT_CREATED, data)
