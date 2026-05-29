"""WebHook 管理 API 视图。"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .engine import EVENT_LABELS, WebHookEvent, WebHookEngine, sign_payload
from .models import WebHookConfig, WebHookDelivery


@login_required
def webhook_config_list(request):
    """获取当前用户的 WebHook 配置列表。"""
    configs = WebHookConfig.objects.filter(created_by=request.user)
    data = [
        {
            "id": c.id,
            "name": c.name,
            "url": c.url,
            "events": c.events,
            "secret": "***" if c.secret else "",
            "is_enabled": c.is_enabled,
            "created_at": c.created_at.isoformat() if c.created_at else "",
        }
        for c in configs
    ]
    return JsonResponse({"configs": data})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def webhook_config_create(request):
    """创建 WebHook 配置。"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "无效的 JSON"}, status=400)

    name = data.get("name", "").strip()
    url = data.get("url", "").strip()
    if not name:
        return JsonResponse({"error": "名称不能为空"}, status=400)
    if not url:
        return JsonResponse({"error": "URL 不能为空"}, status=400)

    cfg = WebHookConfig.objects.create(
        name=name,
        url=url,
        events=data.get("events", []),
        secret=data.get("secret", ""),
        is_enabled=data.get("is_enabled", True),
        created_by=request.user,
    )
    return JsonResponse({"id": cfg.id, "name": cfg.name})


@login_required
@csrf_exempt
@require_http_methods(["PUT", "POST"])
def webhook_config_update(request, config_id: int):
    """更新 WebHook 配置。"""
    cfg = get_object_or_404(WebHookConfig, id=config_id, created_by=request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "无效的 JSON"}, status=400)

    if "name" in data:
        cfg.name = data["name"]
    if "url" in data:
        cfg.url = data["url"]
    if "events" in data:
        cfg.events = data["events"]
    if "secret" in data and data["secret"] and data["secret"] != "***":
        cfg.secret = data["secret"]
    if "is_enabled" in data:
        cfg.is_enabled = data["is_enabled"]
    cfg.save()
    return JsonResponse({"status": "ok"})


@login_required
@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def webhook_config_delete(request, config_id: int):
    """删除 WebHook 配置。"""
    cfg = get_object_or_404(WebHookConfig, id=config_id, created_by=request.user)
    cfg.delete()
    return JsonResponse({"status": "ok"})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def webhook_config_test(request, config_id: int):
    """测试 WebHook 配置（发送一条测试事件）。"""
    import time

    cfg = get_object_or_404(WebHookConfig, id=config_id, created_by=request.user)
    test_payload = {
        "event": "ping",
        "timestamp": int(time.time()),
        "data": {"message": "iSpaceDoc WebHook 测试消息"},
    }

    engine = _get_engine()
    delivery = engine._deliver_one(
        _cfg_to_engine(cfg), WebHookEvent.DOC_CREATED, test_payload
    )

    return JsonResponse({
        "success": delivery.success,
        "response_status": delivery.response_status,
        "response_body": delivery.response_body,
        "duration_ms": delivery.duration_ms,
    })


@login_required
def webhook_deliveries(request):
    """查询 WebHook 投递日志。"""
    config_id = request.GET.get("config_id")
    page = int(request.GET.get("page", 1))
    page_size = min(int(request.GET.get("page_size", 20)), 100)

    qs = WebHookDelivery.objects.filter(config__created_by=request.user)
    if config_id:
        qs = qs.filter(config_id=config_id)

    qs = qs.order_by("-created_at")
    total = qs.count()
    deliveries = qs[(page - 1) * page_size : page * page_size]

    data = [
        {
            "id": d.id,
            "config_id": d.config_id,
            "event": d.event,
            "target_url": d.target_url,
            "response_status": d.response_status,
            "success": d.success,
            "duration_ms": d.duration_ms,
            "attempt": d.attempt,
            "created_at": d.created_at.isoformat() if d.created_at else "",
        }
        for d in deliveries
    ]
    return JsonResponse({"total": total, "page": page, "page_size": page_size, "deliveries": data})


@login_required
def webhook_delivery_detail(request, delivery_id: int):
    """查看投递详情（含请求体和响应体）。"""
    d = get_object_or_404(WebHookDelivery, id=delivery_id, config__created_by=request.user)
    return JsonResponse({
        "id": d.id,
        "config_id": d.config_id,
        "event": d.event,
        "target_url": d.target_url,
        "request_body": d.request_body,
        "response_status": d.response_status,
        "response_body": d.response_body,
        "success": d.success,
        "duration_ms": d.duration_ms,
        "attempt": d.attempt,
        "created_at": d.created_at.isoformat() if d.created_at else "",
    })


def webhook_event_types(request):
    """返回支持的 WebHook 事件类型列表。"""
    return JsonResponse({
        "events": [
            {"name": e.value, "label": EVENT_LABELS.get(e, e.value)}
            for e in WebHookEvent
        ]
    })


# ---- 内部工具 ----

def _get_engine() -> WebHookEngine:
    """创建 WebHook 引擎实例。"""
    def save_delivery(delivery_engine):
        WebHookDelivery.objects.create(
            config_id=int(delivery_engine.config_id),
            event=delivery_engine.event,
            target_url=delivery_engine.target_url,
            request_body=delivery_engine.request_body,
            response_status=delivery_engine.response_status,
            response_body=delivery_engine.response_body,
            success=delivery_engine.success,
            duration_ms=delivery_engine.duration_ms,
            attempt=delivery_engine.attempt,
        )

    def get_configs_engine():
        configs = WebHookConfig.objects.filter(is_enabled=True)
        return [_cfg_to_engine(c) for c in configs]

    return WebHookEngine(get_configs=get_configs_engine, on_delivery=save_delivery)


def _cfg_to_engine(cfg: WebHookConfig):
    from .engine import WebHookConfig as ECfg

    return ECfg(
        id=str(cfg.id),
        name=cfg.name,
        url=cfg.url,
        events=cfg.events,
        secret=cfg.secret,
        is_enabled=cfg.is_enabled,
    )
