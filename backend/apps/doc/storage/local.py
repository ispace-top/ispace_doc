"""本地文件系统存储后端。"""
import os
import shutil
from datetime import datetime
from typing import BinaryIO, Optional

from django.conf import settings
from django.core.files.storage import default_storage

from .base import StorageBackend, UploadResult


class LocalStorageBackend(StorageBackend):
    name = "local"

    def __init__(self, base_dir: str = None, base_url: str = None):
        self._base_dir = base_dir or settings.MEDIA_ROOT
        self._base_url = base_url or settings.MEDIA_URL

    def _full_path(self, key: str) -> str:
        key = key.lstrip("/")
        return os.path.join(self._base_dir, key)

    def upload(self, file: BinaryIO, key: str, content_type: str = "application/octet-stream",
               metadata: Optional[dict] = None) -> UploadResult:
        full_path = self._full_path(key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as dst:
            shutil.copyfileobj(file, dst, length=1024 * 1024)  # 1MB 缓冲区
        size = os.path.getsize(full_path)
        return UploadResult(
            key=key,
            url=self.get_url(key),
            size=size,
            content_type=content_type,
            metadata=metadata,
        )

    def get_url(self, key: str, expires: int = 3600) -> str:
        key = key.lstrip("/")
        return f"{self._base_url.rstrip('/')}/{key}"

    def delete(self, key: str) -> None:
        full_path = self._full_path(key)
        if os.path.isfile(full_path):
            os.remove(full_path)

    def exists(self, key: str) -> bool:
        return os.path.isfile(self._full_path(key))

    def copy(self, source_key: str, dest_key: str) -> None:
        src = self._full_path(source_key)
        dst = self._full_path(dest_key)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

    def get_size(self, key: str) -> int:
        return os.path.getsize(self._full_path(key))
