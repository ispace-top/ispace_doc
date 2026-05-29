"""七牛云 Kodo 原生存储后端。"""
from typing import BinaryIO, Optional

from qiniu import Auth, BucketManager, put_data

from .base import StorageBackend, UploadResult


class KodoStorageBackend(StorageBackend):
    name = "kodo"

    def __init__(
        self,
        access_key: str = None,
        secret_key: str = None,
        bucket: str = None,
        public_base_url: str = None,
    ):
        self._bucket = bucket
        self._public_base_url = public_base_url
        self._auth = Auth(access_key, secret_key)
        self._mgr = BucketManager(self._auth)

    def upload(self, file: BinaryIO, key: str, content_type: str = "application/octet-stream",
               metadata: Optional[dict] = None) -> UploadResult:
        upload_token = self._auth.upload_token(self._bucket, key, 3600)
        data = file.read()
        ret, info = put_data(upload_token, key, data, mime_type=content_type)
        if info.status_code != 200:
            raise IOError(f"七牛云上传失败: {info.text_body}")
        return UploadResult(
            key=ret["key"],
            url=self.get_url(ret["key"]),
            size=len(data),
            content_type=content_type,
            etag=ret.get("hash", ""),
            metadata=metadata,
        )

    def get_url(self, key: str, expires: int = 3600) -> str:
        if self._public_base_url:
            return f"{self._public_base_url.rstrip('/')}/{key.lstrip('/')}"
        return self._auth.private_download_url(
            f"{self._public_base_url.rstrip('/')}/{key.lstrip('/')}" if self._public_base_url else key,
            expires=expires,
        )

    def delete(self, key: str) -> None:
        self._mgr.delete(self._bucket, key)

    def exists(self, key: str) -> bool:
        ret, info = self._mgr.stat(self._bucket, key)
        return info.status_code == 200

    def copy(self, source_key: str, dest_key: str) -> None:
        self._mgr.copy(self._bucket, source_key, self._bucket, dest_key)

    def get_size(self, key: str) -> int:
        ret, info = self._mgr.stat(self._bucket, key)
        if info.status_code == 200:
            return ret.get("fsize", 0)
        return 0
