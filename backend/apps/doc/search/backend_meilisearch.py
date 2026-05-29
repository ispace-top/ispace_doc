"""Meilisearch 搜索后端（2.2.1）。

基于 meilisearch-python SDK，轻量级备选方案。
支持中文搜索、Typo-tolerant、Faceting。
"""
import logging
from typing import Optional

from .base import SearchBackend, SearchDocument, SearchResult

logger = logging.getLogger(__name__)


class MeilisearchBackend(SearchBackend):
    """Meilisearch 搜索后端。

    配置 (config.ini):
        [search.meilisearch]
        host = http://localhost:7700
        api_key = master_key
        index = ispace_docs
    """

    name = "meilisearch"

    def __init__(self, host: str = "http://localhost:7700",
                 api_key: str = "", index_name: str = "ispace_docs"):
        self._host = host
        self._api_key = api_key
        self._index_name = index_name
        self._client = None
        self._ready = False

    def _get_client(self):
        if self._client is None:
            try:
                import meilisearch
                self._client = meilisearch.Client(self._host, self._api_key)
                self._client.create_index(self._index_name, {"primaryKey": "id"})
                self._ready = True
            except ImportError:
                logger.warning("meilisearch-python not installed")
            except Exception as e:
                logger.error(f"Meilisearch 连接失败: {e}")
        return self._client

    def index_doc(self, doc: SearchDocument) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            index = client.index(self._index_name)
            index.add_documents([{
                "id": doc.id,
                "title": doc.title,
                "content": doc.content[:10000],
                "author": doc.author,
                "tags": doc.tags,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "url": doc.url,
                "extra": doc.extra or {},
            }])
            return True
        except Exception as e:
            logger.error(f"Meilisearch 索引失败: {e}")
            return False

    def search(self, query: str, page: int = 1, page_size: int = 20,
               tags: Optional[list[str]] = None, date_from: Optional[str] = None,
               date_to: Optional[str] = None, sort: str = "relevance",
               highlight: bool = True) -> SearchResult:
        client = self._get_client()
        if client is None:
            return SearchResult(total=0, hits=[], page=page, page_size=page_size)

        index = client.index(self._index_name)
        filter_expr = []
        if tags:
            tag_filter = " OR ".join(f'tags = "{t}"' for t in tags)
            filter_expr.append(f"({tag_filter})")
        if date_from:
            filter_expr.append(f"created_at >= {date_from}")
        if date_to:
            filter_expr.append(f"created_at <= {date_to}")

        search_params = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if sort != "relevance":
            search_params["sort"] = [sort]
        if filter_expr:
            search_params["filter"] = " AND ".join(filter_expr)

        try:
            result = index.search(query, search_params)
            hits = []
            for hit in result.get("hits", []):
                hits.append(SearchDocument(
                    id=str(hit.get("id", "")),
                    title=hit.get("title", ""),
                    content=hit.get("content", ""),
                    author=hit.get("author", ""),
                    tags=hit.get("tags", []),
                    url=hit.get("url", ""),
                ))
            return SearchResult(
                total=result.get("estimatedTotalHits", 0),
                hits=hits,
                page=page,
                page_size=page_size,
            )
        except Exception as e:
            logger.error(f"Meilisearch 搜索失败: {e}")
            return SearchResult(total=0, hits=[], page=page, page_size=page_size)

    def delete_doc(self, doc_id: str) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            index = client.index(self._index_name)
            index.delete_document(doc_id)
            return True
        except Exception as e:
            logger.error(f"Meilisearch 删除失败: {e}")
            return False

    def suggest(self, prefix: str, limit: int = 10) -> list[str]:
        result = self.search(prefix, page=1, page_size=limit)
        return [h.title for h in result.hits]

    def health_check(self) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            client.health()
            return True
        except Exception:
            return False
