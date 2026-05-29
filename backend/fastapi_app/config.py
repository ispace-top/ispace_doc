"""v2.0 FastAPI 配置体系（11.1.2）。

使用 pydantic-settings 从 .env 和环境变量加载配置。
支持 YAML/JSON 配置文件的自动加载。
"""
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，所有值可从 .env 文件或环境变量覆盖。"""

    # ---- 应用 ----
    app_name: str = "i·Space Doc"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    base_dir: str = str(Path(__file__).resolve().parent.parent.parent)

    # ---- 数据库 ----
    database_url: str = "sqlite+aiosqlite:///db.sqlite3"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False

    # ---- Redis ----
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20

    # ---- JWT ----
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ---- CORS ----
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:8000"]

    # ---- 搜索引擎 ----
    search_backend: str = "whoosh"  # whoosh / elasticsearch / meilisearch
    es_hosts: str = "http://localhost:9200"
    es_index: str = "ispace_docs"

    # ---- 文件存储 ----
    storage_backend: str = "local"
    media_root: str = "media"
    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # ---- 邮件 ----
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@ispace.com"

    # ---- 认证 ----
    oidc_discovery_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    wecom_corp_id: str = ""
    wecom_corp_secret: str = ""
    dingtalk_app_key: str = ""
    dingtalk_app_secret: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def load_config_from_ini(ini_path: str = None) -> Settings:
    """从 Django style config.ini 加载配置并映射到 Settings。

    用于无缝桥接 Django 和 FastAPI 配置。
    """
    if ini_path is None:
        ini_path = os.environ.get("ISDOC_CONFIG", "config/conf/config.ini")

    import configparser
    parser = configparser.ConfigParser()
    parser.read(ini_path, encoding="utf-8")

    db = parser.get("database", "engine", fallback="sqlite")
    db_name = parser.get("database", "name", fallback="db.sqlite3")
    db_host = parser.get("database", "host", fallback="")
    db_port = parser.get("database", "port", fallback="")
    db_user = parser.get("database", "user", fallback="")
    db_password = parser.get("database", "password", fallback="")

    if db == "mysql":
        database_url = f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    elif db == "postgresql":
        database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        database_url = f"sqlite+aiosqlite:///{db_name}"

    return Settings(
        debug=parser.getboolean("common", "debug", fallback=True),
        secret_key=parser.get("common", "secret_key", fallback="change-me"),
        database_url=database_url,
        smtp_host=parser.get("email", "smtp_host", fallback=""),
        smtp_port=parser.getint("email", "smtp_port", fallback=587),
        smtp_user=parser.get("email", "smtp_user", fallback=""),
        smtp_password=parser.get("email", "smtp_password", fallback=""),
    )


# 全局单例
settings = Settings()
