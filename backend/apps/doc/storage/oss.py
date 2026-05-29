"""阿里云 OSS 存储后端。"""
from typing import BinaryIO, Optional

import oss2

from .base import StorageBackend, UploadResult


class OSSStorageBackend(StorageBackend):
    name = "oss"

    def __init__(
        self,
        endpoint: str = None,
        access_key_id: str = None,
        access_key_secret: str = None,
        bucket: str = None,
        public_base_url: str = None,
        use_sts_token: str = None,
    ):
        self._bucket_name = bucket
        self._public_base_url = public_base_url
        auth = oss2.Auth(access_key_id, access_key_secret)
        self._bucket = oss2.Bucket(auth, endpoint, bucket)
        if use_sts_token:
            auth = oss2.StsAuth(access_key_id, access_key_secret, use_sts_token)
            self._bucket = oss2.Bucket(auth, endpoint, bucket)

    def upload(self, file: BinaryIO, key: str, content_type: str = "application/octet-stream",
               metadata: Optional[dict] = None) -> UploadResult:
        headers = {"Content-Type": content_type}
        if metadata:
            for k, v in metadata.items():
                headers[f"x-oss-meta-{k}"] = str(v)

        data = file.read()
        result = self._bucket.put_object(key, data, headers=headers)
        return UploadResult(
            key=key,
            url=self.get_url(key),
            size=len(data),
            content_type=content_type,
            etag=result.etag,
            metadata=metadata,
        )

    def get_url(self, key: str, expires: int = 3600) -> str:
        if self._public_base_url:
            return f"{self._public_base_url.rstrip('/')}/{key.lstrip('/')}"
        return self._bucket.sign_url("GET", key, expires)

    def delete(self, key: str) -> None:
        self._bucket.delete_object(key)

    def exists(self, key: str) -> bool:
        return self._bucket.object_exists(key)

    def get_presigned_upload_url(self, key: str, content_type: str = "application/octet-stream",
                                  expires: int = 3600) -> str:
        return self._bucket.sign_url("PUT", key, expires, headers={"Content-Type": content_type})

    def copy(self, source_key: str, dest_key: str) -> None:
        self._bucket.copy_object(self._bucket_name, source_key, dest_key)

    def get_size(self, key: str) -> int:
        obj = self._bucket.get_object_meta(key)
        return int(obj.headers.get("Content-Length", 0))

    def process_image(self, key: str, operations: dict) -> str:
        """OSS 图片处理 via x-oss-process（1.4.2）。

        支持的 operations:
            resize: {"width": 200, "height": 200, "fit": "cover"|"contain"|"fill"|"stretch"}
            format: "webp"|"jpg"|"png"|"bmp"|"gif"
            quality: 1-100
            watermark: {"text": "xxx", "position": "se"}
            blur: {"radius": 3, "sigma": 2}
            rotate: {"angle": 90}
            crop: {"x": 0, "y": 0, "w": 100, "h": 100}
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
            params.append(f"resize,{m},w_{w},h_{h}")

        if "format" in operations:
            params.append(f"format,{operations['format']}")

        if "quality" in operations:
            params.append(f"quality,q_{operations['quality']}")

        if "watermark" in operations:
            wm = operations["watermark"]
            text = wm.get("text", "")
            pos = wm.get("position", "se")
            if text:
                params.append(f"watermark,text_{text},g_{pos}")

        if "blur" in operations:
            b = operations["blur"]
            r = b.get("radius", 3)
            s = b.get("sigma", 2)
            params.append(f"blur,r_{r},s_{s}")

        if "rotate" in operations:
            params.append(f"rotate,{operations['rotate']['angle']}")

        if "crop" in operations:
            c = operations["crop"]
            params.append(f"crop,x_{c['x']},y_{c['y']},w_{c['w']},h_{c['h']}")

        if params:
            return f"{base_url}?x-oss-process=image/{'/'.join(params)}"
        return base_url
