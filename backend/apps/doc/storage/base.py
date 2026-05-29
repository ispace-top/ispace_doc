"""存储后端抽象基类。

定义所有存储后端必须实现的统一接口。新增存储后端只需继承此类并实现全部抽象方法，
即可无缝接入系统。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO, Optional


@dataclass
class UploadResult:
    """上传操作的返回结果。"""
    key: str              # 文件唯一标识（路径）
    url: str              # 公开访问 URL
    size: int             # 文件大小（字节）
    content_type: str     # MIME 类型
    etag: str = ""        # 文件 ETag / MD5
    metadata: dict = None  # 额外元数据


class StorageBackend(ABC):
    """存储后端抽象基类。

    所有云存储/本地存储后端必须实现此接口。
    """

    name: str = "base"  # 后端名称，注册时覆盖

    @abstractmethod
    def upload(self, file: BinaryIO, key: str, content_type: str = "application/octet-stream",
               metadata: Optional[dict] = None) -> UploadResult:
        """上传文件。

        Args:
            file: 类文件对象（支持 read 方法）
            key: 存储路径/键
            content_type: MIME 类型
            metadata: 用户自定义元数据

        Returns:
            UploadResult: 包含 key, url, size, content_type, etag
        """
        ...

    @abstractmethod
    def get_url(self, key: str, expires: int = 3600) -> str:
        """获取文件访问 URL。

        Args:
            key: 存储路径/键
            expires: 预签名 URL 有效期（秒），仅对私有存储有效

        Returns:
            str: 文件访问 URL
        """
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除文件。

        Args:
            key: 存储路径/键
        """
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查文件是否存在。

        Args:
            key: 存储路径/键

        Returns:
            bool: 文件是否存在
        """
        ...

    def get_presigned_upload_url(self, key: str, content_type: str = "application/octet-stream",
                                  expires: int = 3600) -> str:
        """获取预签名上传 URL（可选实现）。

        允许客户端直传文件到存储后端，减少服务端带宽压力。
        默认实现抛出 NotImplementedError，子类按需覆盖。

        Args:
            key: 存储路径/键
            content_type: MIME 类型
            expires: 有效期（秒）

        Returns:
            str: 预签名上传 URL
        """
        raise NotImplementedError(f"{self.name} 不支持预签名上传")

    def get_presigned_download_url(self, key: str, expires: int = 3600) -> str:
        """获取预签名下载 URL（可选实现）。

        默认等同于 get_url()，子类可按需生成专用预签名链接。

        Args:
            key: 存储路径/键
            expires: 有效期（秒）

        Returns:
            str: 预签名下载 URL
        """
        return self.get_url(key, expires)

    def copy(self, source_key: str, dest_key: str) -> None:
        """复制文件（可选实现）。

        Args:
            source_key: 源文件路径
            dest_key: 目标文件路径
        """
        raise NotImplementedError(f"{self.name} 不支持服务端复制")

    def get_size(self, key: str) -> int:
        """获取文件大小（可选实现）。

        Args:
            key: 存储路径/键

        Returns:
            int: 文件大小（字节）
        """
        raise NotImplementedError(f"{self.name} 不支持获取文件大小")

    def process_image(self, key: str, operations: dict) -> str:
        """图片处理 URL 生成（可选实现，1.4.2 / 1.3.3 / 1.5.2）。

        子类实现时返回带处理参数的 URL（如 OSS x-oss-process、S3 imgproxy）。

        Args:
            key: 存储路径/键
            operations: 处理操作 dict
                - resize: {"width": 200, "height": 200, "fit": "cover"}
                - format: "webp" | "jpg" | "png"
                - quality: 1-100
                - watermark: {"text": "xxx", "position": "se"}
                - blur: {"radius": 3, "sigma": 2}

        Returns:
            str: 带处理参数的图片 URL
        """
        raise NotImplementedError(f"{self.name} 不支持图片处理")
