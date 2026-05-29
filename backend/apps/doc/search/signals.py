"""搜索索引同步信号。

监听 Doc 模型的变更事件，异步同步至搜索后端。
使用线程异步执行，避免阻塞 HTTP 请求响应。
"""
import logging
import threading

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from backend.apps.doc.models import Doc
from backend.apps.doc.search.backends.base import SearchDocument
from backend.apps.doc.search.backends.config import get_search

logger = logging.getLogger(__name__)

# 被忽略的状态：草稿和已删除文档不索引
_EXCLUDED_STATUSES = {"draft"}


def _doc_to_search_document(doc: Doc) -> SearchDocument:
    """将 Doc 实例转换为 SearchDocument。"""
    tags = list(doc.doctag_set.values_list("tag__name", flat=True)) if hasattr(doc, "doctag_set") else []
    author_name = doc.create_user.username if doc.create_user else ""
    status_str = _get_status_str(doc)

    return SearchDocument(
        id=str(doc.id),
        title=doc.name or "",
        content=doc.content or doc.pre_content or "",
        author=author_name,
        author_id=doc.create_user_id or 0,
        tags=tags,
        created_at=doc.create_time.isoformat() if doc.create_time else "",
        updated_at=doc.modify_time.isoformat() if doc.modify_time else "",
        status=status_str,
    )


def _get_status_str(doc: Doc) -> str:
    """将 Doc.status 整数转为字符串。"""
    # Doc.status: 0=草稿, 1=已发布
    if doc.is_deleted:
        return "deleted"
    if doc.status == 1:
        return "published"
    if doc.status == 0:
        return "draft"
    return "draft"


def _should_index(doc: Doc) -> bool:
    """判断文档是否应被索引。"""
    if doc.is_deleted:
        return False
    return _get_status_str(doc) not in _EXCLUDED_STATUSES


def _index_doc_async(doc: Doc):
    """异步索引文档（线程）。"""
    try:
        search = get_search()
        sd = _doc_to_search_document(doc)
        search.index_doc(sd)
        logger.debug("搜索索引已更新: doc=%s", doc.id)
    except Exception:
        logger.exception("搜索索引同步失败: doc=%s", doc.id)


def _delete_doc_async(doc_id: int):
    """异步删除文档索引（线程）。"""
    try:
        search = get_search()
        search.delete_doc(str(doc_id))
        logger.debug("搜索索引已删除: doc=%s", doc_id)
    except Exception:
        logger.exception("搜索索引删除失败: doc=%s", doc_id)


@receiver(post_save, sender=Doc)
def on_doc_saved(sender, instance, created, **kwargs):
    """Doc 保存后同步搜索索引。"""
    if _should_index(instance):
        t = threading.Thread(target=_index_doc_async, args=(instance,), daemon=True)
        t.start()
    else:
        # 草稿或删除状态，从索引中移除
        t = threading.Thread(target=_delete_doc_async, args=(instance.id,), daemon=True)
        t.start()


@receiver(post_delete, sender=Doc)
def on_doc_deleted(sender, instance, **kwargs):
    """Doc 删除后从搜索索引中移除。"""
    t = threading.Thread(target=_delete_doc_async, args=(instance.id,), daemon=True)
    t.start()
