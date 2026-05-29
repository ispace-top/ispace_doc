"""存储路由器。

按文件 MIME 类型或大小将上传请求路由到不同的存储后端。
典型场景：图片走 CDN 优化的 OSS，文档走 S3，其他文件走本地存储。
"""
import configparser
import os
from typing import BinaryIO, Optional

from django.conf import settings

from .base import StorageBackend, UploadResult
from .config import _read_config, build_storage_backend

CONFIG_PATH = os.environ.get("ISDOC_CONFIG", os.path.join(settings.BASE_DIR, "config", "conf", "config.ini"))


class StorageRouter:
    """按规则将文件路由到不同的存储后端。

    配置示例 (config.ini):

        [storage.rules]
        # 格式: pattern = backend_name
        # pattern 支持 MIME 前缀匹配（image/*, video/*）或精确匹配
        image/* = oss
        video/* = s3
        application/pdf = s3
        application/* = local
    """

    def __init__(self):
        parser = _read_config()
        self._default = build_storage_backend()
        self._backends: dict[str, StorageBackend] = {"default": self._default}
        self._rules: list[tuple[str, str]] = []

        if parser.has_section("storage.rules"):
            for pattern, backend_name in parser.items("storage.rules"):
                pattern = pattern.strip()
                backend_name = backend_name.strip()
                if backend_name not in self._backends:
                    self._backends[backend_name] = build_storage_backend(backend_name)
                self._rules.append((pattern, backend_name))

    def resolve(self, content_type: str = "application/octet-stream", file_size: int = 0) -> StorageBackend:
        """根据 MIME 类型和文件大小匹配存储后端。

        Args:
            content_type: 文件 MIME 类型（如 "image/png"）
            file_size: 文件大小（字节）

        Returns:
            StorageBackend 实例
        """
        for pattern, backend_name in self._rules:
            if pattern.endswith("/*"):
                prefix = pattern[:-2]
                if content_type.startswith(prefix):
                    return self._backends[backend_name]
            elif pattern == content_type:
                return self._backends[backend_name]
            elif pattern == f">{file_size}":
                return self._backends[backend_name]
        return self._default

    def upload(self, file: BinaryIO, key: str, content_type: str = "application/octet-stream",
               metadata: Optional[dict] = None) -> UploadResult:
        backend = self.resolve(content_type)
        return backend.upload(file, key, content_type, metadata)

    def get_url(self, key: str, expires: int = 3600) -> str:
        return self._default.get_url(key, expires)

    def delete(self, key: str) -> None:
        return self._default.delete(key)

    def exists(self, key: str) -> bool:
        return self._default.exists(key)


# 全局路由器单例
_router_instance: Optional[StorageRouter] = None


def get_storage(content_type: str = None, file_size: int = 0) -> StorageBackend:
    """获取适合当前文件的存储后端。

    优先使用路由器（如果配置了规则），否则返回默认后端。

    Args:
        content_type: 文件 MIME 类型
        file_size: 文件大小

    Returns:
        StorageBackend 实例
    """
    global _router_instance
    if _router_instance is not None:
        return _router_instance.resolve(content_type or "application/octet-stream", file_size)

    parser = _read_config()
    if parser.has_section("storage.rules") and len(parser.items("storage.rules")) > 0:
        _router_instance = StorageRouter()
        return _router_instance.resolve(content_type or "application/octet-stream", file_size)

    from .config import get_storage as get_default
    return get_default()


def reset_router():
    """重置路由器单例（测试用）。"""
    global _router_instance
    _router_instance = None
