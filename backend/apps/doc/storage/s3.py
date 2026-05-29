"""AWS S3 兼容存储后端。

支持: AWS S3, MinIO, Cloudflare R2, 七牛云 S3 兼容模式
"""
from typing import BinaryIO, Optional

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from .base import StorageBackend, UploadResult


class S3StorageBackend(StorageBackend):
    name = "s3"

    def __init__(
        self,
        endpoint_url: str = None,
        access_key: str = None,
        secret_key: str = None,
        bucket: str = None,
        region: str = "us-east-1",
        public_base_url: str = None,
        use_path_style: bool = False,
        signature_version: str = "s3v4",
    ):
        self._bucket = bucket
        self._public_base_url = public_base_url
        self._region = region

        boto_config = BotoConfig(
            signature_version=signature_version,
            s3={"addressing_style": "path" if use_path_style else "virtual"},
        )
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=boto_config,
        )

    def upload(self, file: BinaryIO, key: str, content_type: str = "application/octet-stream",
               metadata: Optional[dict] = None) -> UploadResult:
        extra = {"ContentType": content_type}
        if metadata:
            extra["Metadata"] = {k: str(v) for k, v in metadata.items()}
        self._client.upload_fileobj(file, self._bucket, key, ExtraArgs=extra)

        resp = self._client.head_object(Bucket=self._bucket, Key=key)
        return UploadResult(
            key=key,
            url=self.get_url(key),
            size=resp.get("ContentLength", 0),
            content_type=content_type,
            etag=resp.get("ETag", "").strip('"'),
            metadata=metadata,
        )

    def get_url(self, key: str, expires: int = 3600) -> str:
        if self._public_base_url:
            return f"{self._public_base_url.rstrip('/')}/{key.lstrip('/')}"
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires,
            )
        except Exception:
            # fallback: 构造 endpoint URL
            ep = self._client._endpoint
            return f"{ep.url}/{self._bucket}/{key}"

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def get_presigned_upload_url(self, key: str, content_type: str = "application/octet-stream",
                                  expires: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires,
            HttpMethod="PUT",
        )

    def get_presigned_download_url(self, key: str, expires: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires,
        )

    def copy(self, source_key: str, dest_key: str) -> None:
        source = {"Bucket": self._bucket, "Key": source_key}
        self._client.copy_object(
            CopySource=source,
            Bucket=self._bucket,
            Key=dest_key,
        )

    def get_size(self, key: str) -> int:
        resp = self._client.head_object(Bucket=self._bucket, Key=key)
        return resp.get("ContentLength", 0)

    def process_image(self, key: str, operations: dict) -> str:
        """S3 图片处理（1.3.3）。

        生成 imgproxy 兼容的处理 URL，也可配合 S3 Object Lambda 使用。
        生产环境建议配置 dedicated imgproxy 服务。
        """
        base_url = self.get_url(key)
        params = []

        if "resize" in operations:
            r = operations["resize"]
            w = r.get("width", 0)
            h = r.get("height", 0)
            fit = r.get("fit", "cover")
            params.append(f"rs:{fit}:{w}:{h}")

        if "format" in operations:
            params.append(f"f:{operations['format']}")

        if "quality" in operations:
            params.append(f"q:{operations['quality']}")

        if "watermark" in operations:
            wm = operations["watermark"]
            text = wm.get("text", "")
            if text:
                from urllib.parse import quote
                params.append(f"wm:text:{quote(text)}")

        if "blur" in operations:
            b = operations["blur"]
            params.append(f"blur:{b.get('radius', 3)}:{b.get('sigma', 2)}")

        if "rotate" in operations:
            params.append(f"rot:{operations['rotate']['angle']}")

        if params:
            imgproxy_key = "|".join(params)
            return f"/imgproxy/{imgproxy_key}/{key.lstrip('/')}"
        return base_url
