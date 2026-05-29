"""存储配置加载器。

从 config.ini 读取存储相关配置，初始化并返回对应的 StorageBackend 实例。
云存储后端的 SDK 采用延迟导入，仅在配置启用时才加载，避免未安装的 SDK 导致导入失败。
"""
import configparser
import os
from typing import Optional

from django.conf import settings

from .base import StorageBackend
from .local import LocalStorageBackend

# 配置文件路径（与 settings.py 使用相同的路径解析逻辑）
CONFIG_DIR = os.path.join(settings.BASE_DIR, 'config', 'conf')
CONFIG_PATH = os.path.join(CONFIG_DIR, os.environ.get('ISDOC_CONFIG', 'config.ini'))


def _read_config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH, encoding="utf-8")
    return parser


def _import_backend(name: str):
    """延迟导入存储后端类（仅在需要时才加载对应 SDK）。"""
    _backends = {
        "s3": ("backend.apps.doc.storage.s3", "S3StorageBackend"),
        "oss": ("backend.apps.doc.storage.oss", "OSSStorageBackend"),
        "cos": ("backend.apps.doc.storage.cos", "COSStorageBackend"),
        "kodo": ("backend.apps.doc.storage.kodo", "KodoStorageBackend"),
    }
    if name not in _backends:
        raise ValueError(f"未知存储后端: {name}，可用: local, s3, oss, cos, kodo")
    mod_path, cls_name = _backends[name]
    import importlib
    mod = importlib.import_module(mod_path)
    return getattr(mod, cls_name)


def build_storage_backend(backend_name: str = None) -> StorageBackend:
    """根据配置文件构建存储后端实例。

    配置示例 (config.ini):

        [storage]
        # 默认后端: local / s3 / oss / cos / kodo
        backend = local
        public_base_url = http://cdn.example.com

        [storage.s3]
        endpoint_url = https://s3.amazonaws.com
        access_key = AKIDxxx
        secret_key = xxx
        bucket = ispace-doc
        region = us-east-1

    Args:
        backend_name: 指定后端名称，为 None 时使用配置文件中的默认值

    Returns:
        StorageBackend 实例
    """
    parser = _read_config()
    if backend_name is None:
        backend_name = parser.get("storage", "backend", fallback="local")

    public_base_url = parser.get("storage", "public_base_url", fallback=None)
    section = f"storage.{backend_name}"
    kwargs = {"public_base_url": public_base_url} if public_base_url else {}

    if backend_name == "local":
        return LocalStorageBackend(**kwargs)

    cls = _import_backend(backend_name)

    if backend_name == "s3":
        kwargs.update({
            "endpoint_url": parser.get(section, "endpoint_url", fallback=None),
            "access_key": parser.get(section, "access_key", fallback=None),
            "secret_key": parser.get(section, "secret_key", fallback=None),
            "bucket": parser.get(section, "bucket", fallback=None),
            "region": parser.get(section, "region", fallback="us-east-1"),
            "use_path_style": parser.getboolean(section, "use_path_style", fallback=False),
            "signature_version": parser.get(section, "signature_version", fallback="s3v4"),
        })

    elif backend_name == "oss":
        kwargs.update({
            "endpoint": parser.get(section, "endpoint", fallback=None),
            "access_key_id": parser.get(section, "access_key_id", fallback=None),
            "access_key_secret": parser.get(section, "access_key_secret", fallback=None),
            "bucket": parser.get(section, "bucket", fallback=None),
            "use_sts_token": parser.get(section, "sts_token", fallback=None),
        })

    elif backend_name == "cos":
        kwargs.update({
            "region": parser.get(section, "region", fallback=None),
            "secret_id": parser.get(section, "secret_id", fallback=None),
            "secret_key": parser.get(section, "secret_key", fallback=None),
            "bucket": parser.get(section, "bucket", fallback=None),
            "scheme": parser.get(section, "scheme", fallback="https"),
        })

    elif backend_name == "kodo":
        kwargs.update({
            "access_key": parser.get(section, "access_key", fallback=None),
            "secret_key": parser.get(section, "secret_key", fallback=None),
            "bucket": parser.get(section, "bucket", fallback=None),
        })

    return cls(**kwargs)


# 全局单例
_storage_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """获取全局存储后端单例。"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = build_storage_backend()
    return _storage_instance


def reset_storage():
    """重置存储后端单例（测试用）。"""
    global _storage_instance
    _storage_instance = None
