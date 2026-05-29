"""SQLAlchemy 异步引擎配置（11.1.4）。

支持 SQLite / MySQL / PostgreSQL，延迟初始化避免 import 时连接失败。
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类。"""
    pass


# 延迟初始化
_engine = None
_AsyncSessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        from .config import settings
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
        )
    return _engine


def _get_sessionmaker():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _AsyncSessionLocal


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话。"""
    sessionmaker = _get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_db_connection() -> bool:
    """检查数据库连接是否正常。"""
    try:
        engine = _get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
