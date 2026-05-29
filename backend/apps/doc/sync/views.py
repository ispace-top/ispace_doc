"""目录同步 API 视图。

提供手动触发同步和同步状态查询。
"""
import configparser
import logging
import os
import threading
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseBadRequest

from .wecom import WeComSyncBackend
from .base import SyncResult

logger = logging.getLogger(__name__)

CONFIG_PATH = os.environ.get("ISDOC_CONFIG", os.path.join(settings.BASE_DIR, "config", "conf", "config.ini"))

# 内存中的同步状态（简单实现，重启后丢失）
_last_sync_status: dict[str, dict] = {}


def _require_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(_require_admin)
def wecom_sync_trigger(request):
    """手动触发企业微信通讯录同步。

    POST /api/sync/wecom/trigger/
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    corp_id, corp_secret = _read_wecom_config()

    if not corp_id or not corp_secret:
        return JsonResponse({"error": "未配置企业微信 [auth.wecom] corp_id/corp_secret"}, status=400)

    backend = WeComSyncBackend(corp_id=corp_id, corp_secret=corp_secret)

    # 异步执行
    def _run():
        result = backend.sync()
        _last_sync_status["wecom"] = {
            "provider": "wecom",
            "success": result.success,
            "departments_created": result.departments_created,
            "departments_updated": result.departments_updated,
            "departments_deleted": result.departments_deleted,
            "users_created": result.users_created,
            "users_updated": result.users_updated,
            "users_deactivated": result.users_deactivated,
            "errors": result.errors,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
        }

    logger.info(f'[同步] 用户={request.user.username} 手动触发企业微信同步')
    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return JsonResponse({
        "success": True,
        "message": "同步已触发，请稍后查询状态",
    })


@login_required
@user_passes_test(_require_admin)
def sync_status(request, provider: str = "wecom"):
    """查询最近一次同步状态。

    GET /api/sync/<provider>/status/
    """
    status = _last_sync_status.get(provider)
    if not status:
        return JsonResponse({"provider": provider, "last_sync": None})
    return JsonResponse({"provider": provider, "last_sync": status})


@login_required
@user_passes_test(_require_admin)
def ldap_sync_trigger(request):
    """手动触发 LDAP 通讯录同步。

    POST /api/sync/ldap/trigger/
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH, encoding="utf-8")

    if not parser.has_section("auth.ldap"):
        return JsonResponse({"error": "未配置 LDAP [auth.ldap]"}, status=400)

    try:
        from .ldap import LDAPSsyncBackend

        backend = LDAPSsyncBackend(
            server_uri=parser.get("auth.ldap", "server_uri", fallback="ldap://localhost:389"),
            bind_dn=parser.get("auth.ldap", "bind_dn", fallback=""),
            bind_password=parser.get("auth.ldap", "bind_password", fallback=""),
            user_base_dn=parser.get("auth.ldap", "user_base_dn", fallback=""),
            user_filter=parser.get("auth.ldap", "user_filter", fallback="(objectClass=person)"),
            username_attr=parser.get("auth.ldap", "username_attr", fallback="uid"),
            email_attr=parser.get("auth.ldap", "email_attr", fallback="mail"),
            use_tls=parser.getboolean("auth.ldap", "use_tls", fallback=False),
            org_base_dn=parser.get("auth.ldap", "org_base_dn", fallback=""),
            org_filter=parser.get("auth.ldap", "org_filter", fallback="(objectClass=organizationalUnit)"),
            org_name_attr=parser.get("auth.ldap", "org_name_attr", fallback="ou"),
        )
    except Exception as e:
        return JsonResponse({"error": f"初始化 LDAP 后端失败: {e}"}, status=400)

    def _run():
        result = backend.sync()
        _last_sync_status["ldap"] = {
            "provider": "ldap",
            "success": result.success,
            "departments_created": result.departments_created,
            "departments_updated": result.departments_updated,
            "departments_deleted": result.departments_deleted,
            "users_created": result.users_created,
            "users_updated": result.users_updated,
            "users_deactivated": result.users_deactivated,
            "errors": result.errors,
        }

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return JsonResponse({
        "success": True,
        "message": "LDAP 同步已触发，请稍后查询状态",
    })


def _read_wecom_config():
    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH, encoding="utf-8")
    corp_id = parser.get("auth.wecom", "corp_id", fallback="")
    corp_secret = parser.get("auth.wecom", "corp_secret", fallback="")
    return corp_id, corp_secret
