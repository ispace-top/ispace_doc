"""可视化绘图 API 视图。

支持思维导图、Draw.io 流程图、Excalidraw 手绘图的数据存取。
所有绘图数据存储在 Doc.content_json 字段中。
"""
import json
import logging
from datetime import datetime, timezone

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.apps.doc.models import Doc
from backend.apps.doc.services import PermissionService
from .schemas import DrawingType, validate_data, parse_content_json

logger = logging.getLogger(__name__)


# ================================================================
# 思维导图
# ================================================================

@login_required
@require_http_methods(["GET"])
def get_mindmap(request, doc_id: int):
    """获取思维导图数据。

    GET /api/drawing/mindmap/<doc_id>/
    """
    doc = _get_accessible_doc(doc_id, request.user)
    if doc is None:
        return HttpResponseNotFound("文档不存在或无权访问")

    data = parse_content_json(doc.content_json)
    if data.get("type") != DrawingType.MINDMAP.value:
        return JsonResponse({"data": None, "message": "该文档无思维导图数据"})

    return JsonResponse({"data": data, "doc_id": doc_id})


@csrf_exempt
@login_required
@require_http_methods(["PUT", "POST"])
def save_mindmap(request, doc_id: int):
    """保存思维导图数据。

    PUT /api/drawing/mindmap/<doc_id>/
    Body: {root: {...}, theme: {...}, layout: "mindmap"}
    """
    doc = _get_editable_doc(doc_id, request.user)
    if doc is None:
        return HttpResponseNotFound("文档不存在或无权编辑")

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return HttpResponseBadRequest("无效的 JSON 数据")

    body["type"] = DrawingType.MINDMAP.value
    body["version"] = body.get("version", "1.0")
    now_str = datetime.now(timezone.utc).isoformat()
    body.setdefault("created_at", now_str)
    body["updated_at"] = now_str

    valid, error = validate_data(body, DrawingType.MINDMAP)
    if not valid:
        return HttpResponseBadRequest(error)

    doc.content_json = body
    doc.save(update_fields=["content_json", "modify_time"])

    return JsonResponse({
        "success": True,
        "doc_id": doc_id,
        "updated_at": now_str,
    })


# ================================================================
# Draw.io 流程图
# ================================================================

@login_required
@require_http_methods(["GET"])
def get_drawio(request, doc_id: int):
    """获取 Draw.io 流程图数据。

    GET /api/drawing/drawio/<doc_id>/
    """
    doc = _get_accessible_doc(doc_id, request.user)
    if doc is None:
        return HttpResponseNotFound("文档不存在或无权访问")

    data = parse_content_json(doc.content_json)
    if data.get("type") != DrawingType.DRAWIO.value:
        return JsonResponse({"data": None, "message": "该文档无 Draw.io 流程图数据"})

    return JsonResponse({"data": data, "doc_id": doc_id})


@csrf_exempt
@login_required
@require_http_methods(["PUT", "POST"])
def save_drawio(request, doc_id: int):
    """保存 Draw.io 流程图数据。

    PUT /api/drawing/drawio/<doc_id>/
    Body: {xml: "<mxGraphModel>...</mxGraphModel>", png_preview: "data:..."}
    """
    doc = _get_editable_doc(doc_id, request.user)
    if doc is None:
        return HttpResponseNotFound("文档不存在或无权编辑")

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return HttpResponseBadRequest("无效的 JSON 数据")

    body["type"] = DrawingType.DRAWIO.value
    body["version"] = body.get("version", "1.0")
    now_str = datetime.now(timezone.utc).isoformat()
    body.setdefault("created_at", now_str)
    body["updated_at"] = now_str

    valid, error = validate_data(body, DrawingType.DRAWIO)
    if not valid:
        return HttpResponseBadRequest(error)

    doc.content_json = body
    doc.save(update_fields=["content_json", "modify_time"])

    return JsonResponse({
        "success": True,
        "doc_id": doc_id,
        "updated_at": now_str,
    })


# ================================================================
# Excalidraw 手绘图
# ================================================================

@login_required
@require_http_methods(["GET"])
def get_excalidraw(request, doc_id: int):
    """获取 Excalidraw 手绘图数据。

    GET /api/drawing/excalidraw/<doc_id>/
    """
    doc = _get_accessible_doc(doc_id, request.user)
    if doc is None:
        return HttpResponseNotFound("文档不存在或无权访问")

    data = parse_content_json(doc.content_json)
    if data.get("type") != DrawingType.EXCALIDRAW.value:
        return JsonResponse({"data": None, "message": "该文档无 Excalidraw 数据"})

    return JsonResponse({"data": data, "doc_id": doc_id})


@csrf_exempt
@login_required
@require_http_methods(["PUT", "POST"])
def save_excalidraw(request, doc_id: int):
    """保存 Excalidraw 手绘图数据。

    PUT /api/drawing/excalidraw/<doc_id>/
    Body: {elements: [...], appState: {...}, files: {...}}
    """
    doc = _get_editable_doc(doc_id, request.user)
    if doc is None:
        return HttpResponseNotFound("文档不存在或无权编辑")

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return HttpResponseBadRequest("无效的 JSON 数据")

    body["type"] = DrawingType.EXCALIDRAW.value
    body["version"] = body.get("version", 1)
    body["source"] = body.get("source", "https://excalidraw.com")
    now_str = datetime.now(timezone.utc).isoformat()
    body.setdefault("created_at", now_str)
    body["updated_at"] = now_str

    valid, error = validate_data(body, DrawingType.EXCALIDRAW)
    if not valid:
        return HttpResponseBadRequest(error)

    doc.content_json = body
    doc.save(update_fields=["content_json", "modify_time"])

    return JsonResponse({
        "success": True,
        "doc_id": doc_id,
        "updated_at": now_str,
    })


# ================================================================
# 辅助函数
# ================================================================

def _get_accessible_doc(doc_id: int, user):
    """获取用户可查看的文档。"""
    doc = get_object_or_404(Doc, id=doc_id)
    if doc.is_deleted:
        return None
    if doc.is_public:
        return doc
    if doc.create_user == user:
        return doc
    perm = PermissionService.get_effective_permission(user, doc)
    if perm is not None:
        return doc
    return None


def _get_editable_doc(doc_id: int, user):
    """获取用户可编辑的文档。"""
    doc = get_object_or_404(Doc, id=doc_id)
    if doc.is_deleted:
        return None
    if doc.create_user == user:
        return doc
    perm = PermissionService.get_effective_permission(user, doc)
    if perm in ('edit', 'admin'):
        return doc
    return None


# ================================================================
# 6.2.2 Draw.io 导出 API
# ================================================================

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def export_drawio(request, doc_id: int):
    """导出 Draw.io 图表为 PNG/SVG（6.2.2）。

    POST /api/drawing/drawio/<doc_id>/export/
    Body: {"format": "png", "scale": 2.0}

    依赖前端 drawio 库的服务端渲染能力，或使用 puppeteer 渲染。
    本端点返回绘图数据，前端自行处理导出。
    """
    doc = _get_readable_doc(doc_id, request.user)
    if doc is None:
        return HttpResponseNotFound("文档不存在或无权访问")

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        body = {}

    export_format = body.get("format", "svg")
    scale = body.get("scale", 1.0)
    bg = body.get("background", "white")

    content_data = doc.content_json or {}
    diagram_data = content_data.get("drawio", "")
    diagram_name = content_data.get("drawio_name", doc.name)

    if not diagram_data:
        return JsonResponse({"error": "文档不包含 Draw.io 数据"}, status=404)

    response_data = {
        "doc_id": doc_id,
        "diagram_name": diagram_name,
        "format": export_format,
        "scale": scale,
        "background": bg,
        "xml": diagram_data,
    }

    # 从 XML 中提取基本信息
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(diagram_data)
        cells = root.findall(".//mxCell")
        response_data["cell_count"] = len([c for c in cells if c.get("vertex") == "1"])
        response_data["edge_count"] = len([c for c in cells if c.get("edge") == "1"])
    except Exception:
        pass

    return JsonResponse(response_data)
