"""搜索建议/自动补全。

基于 SearchBackend.suggest() 提供前缀搜索建议。
当搜索后端不支持 suggest 时，使用简单的基于搜索的降级方案。
"""
import logging

from backend.apps.doc.search.backends.config import get_search

logger = logging.getLogger(__name__)


def suggest(prefix: str, limit: int = 5) -> list[str]:
    """获取搜索建议。

    优先使用搜索后端的 suggest 方法（completion suggester / 前缀匹配）。
    降级方案：直接搜索前缀获取标题匹配。
    """
    search = get_search()

    try:
        result = search.suggest(prefix, limit=limit)
        if result.suggestions:
            return result.suggestions[:limit]
    except Exception:
        logger.debug("搜索后端 suggest 不可用，降级为搜索匹配")

    # 降级：用前缀搜索获取结果标题
    try:
        result = search.search(
            query=prefix,
            page=1,
            page_size=limit,
            filters={"status": "published"},
            highlight=False,
        )
        titles = [h.get("title", "") for h in result.hits if h.get("title")]
        return list(dict.fromkeys(titles))[:limit]
    except Exception:
        logger.exception("搜索建议降级方案失败")
        return []
