"""搜索 API 视图。

单一入口 `/api/search/`，通过 SearchBackend 抽象层统一支持
Whoosh / Elasticsearch / Meilisearch 等不同后端。
"""
import logging
import time

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone

from backend.apps.doc.search.backends.base import SearchResult
from backend.apps.doc.search.backends.config import get_search
from backend.apps.doc.search.suggest import suggest as do_suggest

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


@login_required
def search_api(request):
    """全文搜索 API。

    GET /api/search/
    Params:
        q            — 搜索关键词
        page         — 页码（默认 1）
        page_size    — 每页结果数（默认 10，最大 100）
        tags         — 标签过滤，逗号分隔
        date_from    — 开始日期 (YYYY-MM-DD)
        date_to      — 结束日期 (YYYY-MM-DD)
        status       — 状态过滤（默认 published）
        sort         — 排序：relevance / -created_at / -updated_at
        highlight    — 是否返回高亮（默认 true）
        suggest      — 是否返回搜索建议（默认 false）
    """
    query = request.GET.get("q", "").strip()
    if not query:
        return HttpResponseBadRequest("缺少搜索关键词参数 q")

    page = _parse_int(request.GET.get("page", "1"), min_val=1)
    page_size = _parse_int(request.GET.get("page_size", str(DEFAULT_PAGE_SIZE)), min_val=1, max_val=MAX_PAGE_SIZE)

    # 构建过滤条件
    filters = {}

    tags = request.GET.get("tags", "").strip()
    if tags:
        filters["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    date_from = request.GET.get("date_from", "").strip()
    if date_from:
        filters["date_from"] = date_from

    date_to = request.GET.get("date_to", "").strip()
    if date_to:
        filters["date_to"] = date_to

    status = request.GET.get("status", "published").strip()
    filters["status"] = status

    sort = request.GET.get("sort", "relevance").strip()
    highlight = request.GET.get("highlight", "true").lower() != "false"

    with_suggest = request.GET.get("suggest", "false").lower() == "true"

    search = get_search()

    t0 = time.monotonic()
    try:
        result = search.search(
            query=query,
            page=page,
            page_size=page_size,
            filters=filters or None,
            sort=sort,
            highlight=highlight,
        )
    except Exception:
        logger.exception("搜索请求失败: q=%s", query[:100])
        return JsonResponse({"error": "搜索服务暂时不可用，请稍后再试"}, status=500)
    elapsed = (time.monotonic() - t0) * 1000

    resp = _build_response(result, page, page_size)

    if with_suggest and result.total < 5:
        try:
            s = do_suggest(query, limit=5)
            resp["suggestions"] = s
        except Exception:
            pass

    resp["took_ms"] = round(elapsed, 1)

    return JsonResponse(resp)


@login_required
def suggest_api(request):
    """搜索自动补全。

    GET /api/search/suggest/?prefix=xxx
    """
    prefix = request.GET.get("prefix", "").strip()
    if not prefix or len(prefix) < 1:
        return HttpResponseBadRequest("缺少 prefix 参数（至少 1 个字符）")

    limit = _parse_int(request.GET.get("limit", "5"), min_val=1, max_val=20)

    try:
        suggestions = do_suggest(prefix, limit=limit)
    except Exception:
        return JsonResponse({"suggestions": []})

    return JsonResponse({"suggestions": suggestions, "prefix": prefix})


@login_required
def search_stats(request):
    """搜索后端状态（仅管理员可用）。

    GET /api/search/stats/
    """
    if not request.user.is_staff:
        return JsonResponse({"error": "仅管理员可用"}, status=403)

    search = get_search()
    try:
        stats = search.stats()
        stats["ping"] = search.ping()
    except Exception:
        stats = {"ping": False, "error": "无法连接搜索后端"}

    return JsonResponse(stats)


def _build_response(result: SearchResult, page: int, page_size: int) -> dict:
    """将 SearchResult 转为 JSON 响应数据。"""
    return {
        "hits": result.hits,
        "total": result.total,
        "page": result.page or page,
        "page_size": result.page_size or page_size,
        "total_pages": result.total_pages,
        "has_next": result.has_next,
        "has_prev": result.has_prev,
        "highlights": result.highlights,
    }


# ================================================================
# 2.1.8 相关推荐 API
# ================================================================

@login_required
def related_docs_api(request, doc_id: int):
    """相关文档推荐 API — more-like-this 语义。

    GET /api/search/related/<doc_id>/?limit=5

    基于文档标签和标题相似度排序相关文档。
    """
    limit = _parse_int(request.GET.get("limit", "5"), min_val=1, max_val=20)

    try:
        from backend.apps.doc.models import Doc
        doc = Doc.objects.filter(pk=doc_id, is_deleted=False).first()
        if not doc:
            return JsonResponse({"error": "文档不存在"}, status=404)

        tags = list(doc.doctag_set.values_list("tag__name", flat=True))
        search = get_search()

        if tags:
            result = search.search(
                query="",
                page=1,
                page_size=limit + 1,
                filters={"tags": tags},
                sort="relevance",
            )
        else:
            result = search.search(
                query=doc.name[:100],
                page=1,
                page_size=limit + 1,
                sort="relevance",
            )

        hits = [h for h in result.hits if str(h.get("id")) != str(doc_id)][:limit]

        return JsonResponse({
            "doc_id": doc_id,
            "related": hits,
        })
    except Exception as e:
        logger.exception("相关推荐失败: doc_id=%s", doc_id)
        return JsonResponse({"error": str(e)}, status=500)


def _parse_int(val, min_val=None, max_val=None) -> int:
    try:
        v = int(val)
    except (TypeError, ValueError):
        v = 0
    if min_val is not None:
        v = max(v, min_val)
    if max_val is not None:
        v = min(v, max_val)
    return v
