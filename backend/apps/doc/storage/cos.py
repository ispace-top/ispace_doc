"""腾讯云 COS 存储后端。"""
from typing import BinaryIO, Optional

from qcloud_cos import CosConfig, CosS3Client

from .base import StorageBackend, UploadResult


class COSStorageBackend(StorageBackend):
    name = "cos"

    def __init__(
        self,
        region: str = None,
        secret_id: str = None,
        secret_key: str = None,
        bucket: str = None,
        public_base_url: str = None,
        scheme: str = "https",
    ):
        self._bucket = bucket
        self._public_base_url = public_base_url
        config = CosConfig(
            Region=region,
            SecretId=secret_id,
            SecretKey=secret_key,
            Scheme=scheme,
        )
        self._client = CosS3Client(config)

    def upload(self, file: BinaryIO, key: str, content_type: str = "application/octet-stream",
               metadata: Optional[dict] = None) -> UploadResult:
        extra = {"ContentType": content_type}
        if metadata:
            extra["Metadata"] = {k: str(v) for k, v in metadata.items()}
        data = file.read()
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, **extra)
        resp = self._client.head_object(Bucket=self._bucket, Key=key)
        return UploadResult(
            key=key,
            url=self.get_url(key),
            size=int(resp.get("Content-Length", 0)),
            content_type=content_type,
            etag=resp.get("ETag", "").strip('"'),
            metadata=metadata,
        )

    def get_url(self, key: str, expires: int = 3600) -> str:
        if self._public_base_url:
            return f"{self._public_base_url.rstrip('/')}/{key.lstrip('/')}"
        return self._client.get_presigned_url(
            Method="GET",
            Bucket=self._bucket,
            Key=key,
            Expired=expires,
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def get_presigned_upload_url(self, key: str, content_type: str = "application/octet-stream",
                                  expires: int = 3600) -> str:
        return self._client.get_presigned_url(
            Method="PUT",
            Bucket=self._bucket,
            Key=key,
            Expired=expires,
        )

    def copy(self, source_key: str, dest_key: str) -> None:
        source = f"{self._bucket}.cos.{self._client._conf.Region}.myqcloud.com/{source_key}"
        self._client.copy_object(
            Bucket=self._bucket,
            Key=dest_key,
            CopySource={"Bucket": self._bucket, "Key": source_key, "Region": self._client._conf.Region},
        )

    def get_size(self, key: str) -> int:
        resp = self._client.head_object(Bucket=self._bucket, Key=key)
        return int(resp.get("Content-Length", 0))

    def process_image(self, key: str, operations: dict) -> str:
        """COS 数据万象 CI 图片处理（1.5.2）。

        腾讯云 CI 对 COS 桶中的图片提供与 OSS x-oss-process 兼容的处理参数。
        """
        base_url = self.get_url(key)
        params = []

        if "resize" in operations:
            r = operations["resize"]
            w = r.get("width", "auto")
            h = r.get("height", "auto")
            fit = r.get("fit", "cover")
            fit_map = {"cover": "m_fill", "contain": "m_lfit", "fill": "m_fill", "stretch": "m_fixed"}
            m = fit_map.get(fit, "m_fill")
            params.append(f"imageMogr2/thumbnail/!{w}x{h}{'r' if fit == 'contain' else ''}")

        if "format" in operations:
            params.append(f"imageMogr2/format/{operations['format']}")

        if "quality" in operations:
            params.append(f"imageMogr2/quality/{operations['quality']}")

        if "watermark" in operations:
            wm = operations["watermark"]
            text = wm.get("text", "")
            pos = wm.get("position", "se")
            from urllib.parse import quote
            if text:
                params.append(f"watermark/2/text/{quote(text)}/gravity/{pos}")

        if "blur" in operations:
            b = operations["blur"]
            params.append(f"imageMogr2/blur/{b.get('radius', 3)}x{b.get('sigma', 2)}")

        if "rotate" in operations:
            params.append(f"imageMogr2/rotate/{operations['rotate']['angle']}")

        if params:
            return f"{base_url}?{'|'.join(params)}"
        return base_url
