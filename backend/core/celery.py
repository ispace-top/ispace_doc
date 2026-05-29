"""Celery 应用配置（11.2.1）。

Redis 作为 broker 和 result backend，JSON 序列化。
支持 Django ORM 和独立 Python 脚本两种上下文。
"""
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.core.settings")


def _build_broker_url() -> str:
    """从环境变量或 config.ini 构建 Redis broker URL。

    优先级: CELERY_BROKER_URL > REDIS_URL > config.ini [celery] > config.ini [cache] > 默认值
    """
    # 1. 显式 Celery broker URL
    broker = os.environ.get("CELERY_BROKER_URL")
    if broker:
        return broker

    # 2. REDIS_URL 环境变量
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        base = redis_url.rstrip("/")
        return f"{base}/1"

    # 3. config.ini 配置
    try:
        from configparser import ConfigParser
        parser = ConfigParser()
        config_file = os.environ.get("ISDOC_CONFIG", "config.ini")
        parser.read(os.path.join("config", "conf", config_file), encoding="utf-8")

        # 优先读取 [celery] 段
        if parser.has_option("celery", "broker_url"):
            return parser.get("celery", "broker_url")

        # 回退到 [cache] 段
        backend = parser.get("cache", "backend", fallback="locmem")
        if backend == "redis":
            location = parser.get("cache", "location", fallback="redis://127.0.0.1:6379/0")
            base = location.rstrip("/")
            return f"{base}/1"
    except Exception:
        pass

    # 4. 默认值
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = os.environ.get("REDIS_PORT", "6379")
    return f"redis://{redis_host}:{redis_port}/1"


app = Celery("iSpaceDoc")

app.conf.update(
    broker_url=_build_broker_url(),
    result_backend=_build_broker_url().replace("/1", "/2"),
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_max_tasks_per_child=200,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
)

app.autodiscover_tasks(["backend.tasks"])

# Celery Beat 定时任务调度（11.2.3）
from celery.schedules import crontab

app.conf.beat_schedule = {
    # 每日摘要 — 每天 8:00 发送
    "daily-digest": {
        "task": "backend.tasks.scheduled.send_daily_digest_bulk",
        "schedule": crontab(hour=8, minute=0),
        "options": {"expires": 3600},
    },
    # 索引健康检查 — 每天凌晨 3:00
    "index-health-check": {
        "task": "backend.tasks.scheduled.index_health_check",
        "schedule": crontab(hour=3, minute=0),
        "options": {"expires": 1800},
    },
    # LDAP 用户同步 — 每天凌晨 2:00（仅当配置了 LDAP 时生效）
    "ldap-sync": {
        "task": "backend.tasks.scheduled.ldap_sync",
        "schedule": crontab(hour=2, minute=0),
        "options": {"expires": 7200},
    },
}
