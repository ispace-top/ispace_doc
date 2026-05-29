"""FastAPI 依赖注入。

提供 Django ORM 模型桥接、Redis 连接等共享依赖。
"""
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _setup_django():
    """初始化 Django 环境（仅执行一次）。"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.core.settings")
    import django
    django.setup()


def get_django_doc_model():
    """获取 v2.0 IspDocument 模型（Django ORM 桥接）。"""
    _setup_django()
    from backend.apps.doc.models_v2 import IspDocument
    return IspDocument


def get_django_permission_model():
    """获取 v2.0 IspDocPermission 模型。"""
    _setup_django()
    from backend.apps.doc.models_v2 import IspDocPermission
    return IspDocPermission


async def get_redis():
    """获取异步 Redis 连接（11.1.5）。"""
    try:
        import redis.asyncio as aioredis
        from .config import settings
        return aioredis.from_url(settings.redis_url)
    except ImportError:
        return None
