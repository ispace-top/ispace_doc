"""Elasticsearch 8.x 搜索后端（IK 中文分词 + BM25 排序）。

依赖:
    pip install elasticsearch>=8.0.0
"""
from typing import Optional

from .base import SearchBackend, SearchResult, SearchDocument, SuggestResult


# ES 索引映射模板
INDEX_MAPPING = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "refresh_interval": "1s",
        },
        "analysis": {
            "analyzer": {
                "ik_smart_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_smart",
                    "filter": ["lowercase"],
                },
                "ik_max_word_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_max_word",
                    "filter": ["lowercase"],
                },
            },
            "normalizer": {
                "lowercase_normalizer": {
                    "type": "custom",
                    "filter": ["lowercase"],
                }
            },
        },
    },
    "mappings": {
        "properties": {
            "title": {
                "type": "text",
                "analyzer": "ik_max_word_analyzer",
                "search_analyzer": "ik_smart_analyzer",
                "fields": {
                    "raw": {"type": "keyword", "normalizer": "lowercase_normalizer"},
                },
            },
            "content": {
                "type": "text",
                "analyzer": "ik_max_word_analyzer",
                "search_analyzer": "ik_smart_analyzer",
            },
            "author": {
                "type": "keyword",
                "normalizer": "lowercase_normalizer",
            },
            "author_id": {"type": "integer"},
            "tags": {"type": "keyword"},
            "created_at": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss"},
            "updated_at": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss"},
            "status": {"type": "keyword"},
            "extra": {"type": "object", "enabled": False},
            "suggest": {
                "type": "completion",
                "analyzer": "ik_smart_analyzer",
            },
        }
    },
}


class ElasticsearchBackend(SearchBackend):
    """Elasticsearch 8.x 后端。

    配置示例 (config.ini):

        [search.elasticsearch]
        hosts = http://localhost:9200
        index = ispace_docs
        username = elastic         ; 可选
        password = changeme        ; 可选
        verify_certs = false       ; 可选
    """

    name = "elasticsearch"

    def __init__(
        self,
        hosts: str = "http://localhost:9200",
        index: str = "ispace_docs",
        username: str = None,
        password: str = None,
        verify_certs: bool = True,
    ):
        try:
            from elasticsearch import Elasticsearch
        except ImportError:
            raise ImportError(
                "请安装 elasticsearch: pip install elasticsearch>=8.0.0"
            )

        self._index = index
        es_kwargs = {"hosts": hosts.split(",") if "," in hosts else hosts}
        if username and password:
            es_kwargs["basic_auth"] = (username, password)
        if not verify_certs:
            es_kwargs["verify_certs"] = False
        self._client = Elasticsearch(**es_kwargs)
        self._ensure_index()

    def _ensure_index(self) -> None:
        """确保索引存在，不存在则创建。"""
        if not self._client.indices.exists(index=self._index):
            self._client.indices.create(index=self._index, body=INDEX_MAPPING)

    # ---- 索引操作 ----

    def index_doc(self, doc: SearchDocument) -> None:
        body = {
            "title": doc.title,
            "content": doc.content,
            "author": doc.author,
            "author_id": doc.author_id,
            "tags": doc.tags,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "status": doc.status,
            "extra": doc.extra,
            "suggest": {
                "input": [doc.title] + doc.tags,
                "weight": 10,
            },
        }
        self._client.index(index=self._index, id=doc.id, document=body, refresh=False)

    def index_docs(self, docs: list[SearchDocument]) -> None:
        """使用 ES bulk API 批量索引。"""
        from elasticsearch.helpers import bulk

        actions = [
            {
                "_index": self._index,
                "_id": doc.id,
                "_source": {
                    "title": doc.title,
                    "content": doc.content,
                    "author": doc.author,
                    "author_id": doc.author_id,
                    "tags": doc.tags,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at,
                    "status": doc.status,
                    "extra": doc.extra,
                    "suggest": {
                        "input": [doc.title] + doc.tags,
                        "weight": 10,
                    },
                },
            }
            for doc in docs
        ]
        success, errors = bulk(self._client, actions, refresh=False)
        self._client.indices.refresh(index=self._index)

    def delete_doc(self, doc_id: str) -> None:
        self._client.delete(index=self._index, id=doc_id, ignore=[404])

    def clear_index(self) -> None:
        self._client.indices.delete(index=self._index, ignore=[404])
        self._ensure_index()

    def rebuild_index(self, docs: list[SearchDocument]) -> None:
        self.clear_index()
        if docs:
            self.index_docs(docs)
        self._client.indices.refresh(index=self._index)

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
        from elasticsearch import Elasticsearch

        body: dict = {"query": {"bool": {"must": [], "filter": []}}, "from": (page - 1) * page_size, "size": page_size}

        if query.strip():
            body["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "content", "tags^2", "author"],
                    "type": "best_fields",
                }
            })
        else:
            body["query"]["bool"]["must"].append({"match_all": {}})

        # 应用过滤条件
        if filters:
            for key, value in filters.items():
                if key == "status":
                    body["query"]["bool"]["filter"].append({"term": {"status": value}})
                elif key == "tags":
                    body["query"]["bool"]["filter"].append({"terms": {"tags": value if isinstance(value, list) else [value]}})
                elif key == "author_id":
                    body["query"]["bool"]["filter"].append({"term": {"author_id": value}})
                elif key == "date_from":
                    body["query"]["bool"]["filter"].append({"range": {"created_at": {"gte": value}}})
                elif key == "date_to":
                    body["query"]["bool"]["filter"].append({"range": {"created_at": {"lte": value}}})

        # 排序
        if sort:
            if sort == "relevance":
                pass  # ES 默认按相关性排序
            elif sort.startswith("-"):
                body["sort"] = [{sort[1:]: "desc"}]
            else:
                body["sort"] = [{sort: "asc"}]

        # 高亮
        if highlight:
            body["highlight"] = {
                "fields": {
                    "title": {"number_of_fragments": 0},
                    "content": {"fragment_size": 150, "number_of_fragments": 3},
                },
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"],
            }

        resp = self._client.search(index=self._index, body=body)

        hits = []
        highlights_map = {}
        for hit in resp["hits"]["hits"]:
            source = hit["_source"]
            source["_score"] = hit["_score"]
            hits.append(source)
            if highlight and "highlight" in hit:
                highlights_map[str(hit["_id"])] = hit["highlight"]

        return SearchResult(
            hits=hits,
            total=resp["hits"]["total"]["value"] if isinstance(resp["hits"]["total"], dict) else resp["hits"]["total"],
            page=page,
            page_size=page_size,
            query=query,
            highlights=highlights_map,
            took_ms=resp.get("took", 0),
        )

    # ---- 搜索建议 ----

    def suggest(self, prefix: str, limit: int = 5) -> SuggestResult:
        body = {
            "suggest": {
                "title_suggest": {
                    "prefix": prefix,
                    "completion": {
                        "field": "suggest",
                        "size": limit,
                        "skip_duplicates": True,
                    },
                }
            }
        }
        resp = self._client.search(index=self._index, body=body)

        suggestions = []
        for item in resp.get("suggest", {}).get("title_suggest", [{}])[0].get("options", []):
            suggestions.append(item["text"])

        return SuggestResult(suggestions=suggestions, took_ms=resp.get("took", 0))

    # ---- 健康检查 ----

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False

    def stats(self) -> dict:
        stats = self._client.indices.stats(index=self._index)
        count_resp = self._client.count(index=self._index)
        return {
            "backend": self.name,
            "index": self._index,
            "doc_count": count_resp.get("count", 0),
            "size_bytes": stats["indices"].get(self._index, {}).get("total", {}).get("store", {}).get("size_in_bytes", 0),
        }
