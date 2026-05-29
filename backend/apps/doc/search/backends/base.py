"""搜索引擎抽象基类。

定义统一的搜索接口，支持不同后端（Elasticsearch、Meilisearch、Whoosh 等）的热插拔。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchResult:
    """搜索结果数据类。"""

    hits: list[dict] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10
    query: str = ""
    highlights: dict[str, list[str]] = field(default_factory=dict)
    facets: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    took_ms: float = 0.0

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


@dataclass
class SuggestResult:
    """搜索建议结果。"""

    suggestions: list[str] = field(default_factory=list)
    took_ms: float = 0.0


@dataclass
class SearchDocument:
    """待索引的文档。"""

    id: str
    title: str
    content: str
    author: str = ""
    author_id: int = 0
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    status: str = "published"
    extra: dict = field(default_factory=dict)


class SearchBackend(ABC):
    """搜索引擎抽象基类。

    子类需实现:
        index_doc, search, delete_doc, clear_index, rebuild_index
    """

    name: str = "base"

    # ---- 索引操作 ----

    @abstractmethod
    def index_doc(self, doc: SearchDocument) -> None:
        """索引或更新单个文档。"""

    @abstractmethod
    def index_docs(self, docs: list[SearchDocument]) -> None:
        """批量索引文档（默认逐条调用，子类可覆盖为 bulk 操作）。"""
        for doc in docs:
            self.index_doc(doc)

    @abstractmethod
    def delete_doc(self, doc_id: str) -> None:
        """从索引中删除文档。"""

    @abstractmethod
    def clear_index(self) -> None:
        """清空整个索引。"""

    @abstractmethod
    def rebuild_index(self, docs: list[SearchDocument]) -> None:
        """全量重建索引（清空 + 批量导入）。"""
        self.clear_index()
        self.index_docs(docs)

    # ---- 搜索操作 ----

    @abstractmethod
    def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[dict] = None,
        sort: Optional[str] = None,
        highlight: bool = True,
    ) -> SearchResult:
        """全文搜索。

        Args:
            query: 搜索关键词
            page: 页码（从1开始）
            page_size: 每页结果数
            filters: 过滤条件，如 {'status': 'published', 'tags': ['python'], 'date_from': '2026-01-01'}
            sort: 排序方式（'-created_at', 'relevance' 等）
            highlight: 是否返回高亮片段

        Returns:
            SearchResult
        """

    # ---- 建议/联想 ----

    def suggest(self, prefix: str, limit: int = 5) -> SuggestResult:
        """搜索自动补全（可选，子类按需覆盖）。"""
        return SuggestResult()

    # ---- 健康检查 ----

    def ping(self) -> bool:
        """检查搜索后端是否可用。"""
        return True

    def stats(self) -> dict:
        """返回索引统计信息（可选）。"""
        return {"backend": self.name, "doc_count": 0}
