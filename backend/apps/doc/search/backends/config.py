"""搜索后端配置加载器。

从 config.ini 读取搜索相关配置，初始化并返回对应的 SearchBackend 实例。
搜索后端的 SDK 采用延迟导入，仅在配置启用时才加载。
"""
import configparser
import os
from typing import Optional

from django.conf import settings

from .base import SearchBackend

CONFIG_PATH = os.environ.get("ISDOC_CONFIG", os.path.join(settings.BASE_DIR, "config", "conf", "config.ini"))


def _read_config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH, encoding="utf-8")
    return parser


def _import_backend(name: str):
    """延迟导入搜索后端类（仅在需要时才加载对应 SDK）。"""
    _backends = {
        "elasticsearch": ("backend.apps.doc.search.backends.elasticsearch", "ElasticsearchBackend"),
        "meilisearch": ("backend.apps.doc.search.backends.meilisearch", "MeilisearchBackend"),
    }
    if name not in _backends:
        raise ValueError(f"未知搜索后端: {name}，可用: {', '.join(_backends.keys())}")
    mod_path, cls_name = _backends[name]
    import importlib

    mod = importlib.import_module(mod_path)
    return getattr(mod, cls_name)


def build_search_backend(backend_name: str = None) -> SearchBackend:
    """根据配置文件构建搜索后端实例。

    配置示例 (config.ini):

        [search]
        # 搜索后端: whoosh / elasticsearch / meilisearch
        backend = whoosh

        [search.elasticsearch]
        hosts = http://localhost:9200
        index = ispace_docs
        username = elastic
        password = changeme
        verify_certs = false
    """
    parser = _read_config()
    if backend_name is None:
        backend_name = parser.get("search", "backend", fallback="whoosh")

    section = f"search.{backend_name}"

    if backend_name == "whoosh":
        from backend.apps.doc.search.backends.whoosh import WhooshBackend

        return WhooshBackend()

    cls = _import_backend(backend_name)

    if backend_name == "elasticsearch":
        return cls(
            hosts=parser.get(section, "hosts", fallback="http://localhost:9200"),
            index=parser.get(section, "index", fallback="ispace_docs"),
            username=parser.get(section, "username", fallback=None),
            password=parser.get(section, "password", fallback=None),
            verify_certs=parser.getboolean(section, "verify_certs", fallback=True),
        )

    if backend_name == "meilisearch":
        return cls(
            host=parser.get(section, "host", fallback="http://localhost:7700"),
            api_key=parser.get(section, "api_key", fallback=None),
            index=parser.get(section, "index", fallback="ispace_docs"),
        )

    return cls()


# 全局单例
_search_instance: Optional[SearchBackend] = None


def get_search() -> SearchBackend:
    """获取全局搜索后端单例。"""
    global _search_instance
    if _search_instance is None:
        _search_instance = build_search_backend()
    return _search_instance


def reset_search():
    """重置搜索后端单例（测试用）。"""
    global _search_instance
    _search_instance = None
