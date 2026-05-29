"""Whoosh 搜索后端（兼容现有 Haystack Whoosh 引擎）。

将现有的 Haystack WhooshSearchBackend 适配到新的 SearchBackend 接口。
保持与现有索引数据的完全兼容。
"""
from typing import Optional

from django.conf import settings

from .base import SearchBackend, SearchResult, SearchDocument, SuggestResult


class WhooshBackend(SearchBackend):
    """Whoosh 搜索后端 — 适配现有 Haystack 引擎。

    读取已有的 Haystack 配置，通过 Haystack SearchQuerySet 执行搜索。
    """

    name = "whoosh"

    def __init__(self):
        from haystack.query import SearchQuerySet

        self._sqs = SearchQuerySet

    # ---- 索引操作 ----

    def index_doc(self, doc: SearchDocument) -> None:
        """单文档索引更新（通过 Haystack RealtimeSignalProcessor 自动处理）。"""
        from backend.apps.doc.models import Doc

        try:
            instance = Doc.objects.get(id=int(doc.id))
            from haystack import connections

            backend = connections["default"].get_backend()
            backend.update(instance, [instance])
        except Doc.DoesNotExist:
            pass

    def index_docs(self, docs: list[SearchDocument]) -> None:
        for doc in docs:
            self.index_doc(doc)

    def delete_doc(self, doc_id: str) -> None:
        try:
            from haystack import connections

            backend = connections["default"].get_backend()
            backend.remove(doc_id)
        except Exception:
            pass

    def clear_index(self) -> None:
        from haystack import connections

        backend = connections["default"].get_backend()
        backend.clear()

    def rebuild_index(self, docs: list[SearchDocument]) -> None:
        from haystack.management.commands import update_index

        self.clear_index()
        for doc in docs:
            self.index_doc(doc)

    # ---- 搜索操作 ----

    def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[dict] = None,
        sort: Optional[str] = None,
        highlight: bool = True,
    ) -> SearchResult:
        from haystack.query import SearchQuerySet

        sqs = self._sqs()

        if query.strip():
            sqs = sqs.filter(content=query)
        else:
            sqs = sqs.all()

        if filters:
            for key, value in filters.items():
                if key == "status":
                    sqs = sqs.filter(status=value)
                elif key == "date_from":
                    sqs = sqs.filter(modify_time__gte=value)
                elif key == "date_to":
                    sqs = sqs.filter(modify_time__lte=value)

        total = sqs.count()
        start = (page - 1) * page_size
        results = sqs[start : start + page_size]

        hits = []
        highlights_map = {}
        for r in results:
            hit = {
                "id": str(r.pk),
                "title": getattr(r, "name", ""),
                "content": getattr(r, "pre_content", ""),
                "_score": getattr(r, "score", 0.0),
            }
            hits.append(hit)
            if highlight:
                hl = r.highlighted if hasattr(r, "highlighted") else {}
                if hl:
                    highlights_map[str(r.pk)] = hl

        return SearchResult(
            hits=hits,
            total=total,
            page=page,
            page_size=page_size,
            query=query,
            highlights=highlights_map,
        )

    # ---- 健康检查 ----

    def ping(self) -> bool:
        try:
            from haystack import connections

            backend = connections["default"].get_backend()
            return hasattr(backend, "index")
        except Exception:
            return False

    def stats(self) -> dict:
        from haystack import connections

        backend = connections["default"].get_backend()
        count = 0
        try:
            count = backend.index.doc_count()
        except Exception:
            pass
        return {"backend": self.name, "doc_count": count}
