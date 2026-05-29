"""v2.0 REST API 视图。

基于新 Isp* 模型，统一的 RESTful 接口。
所有端点返回 JSON，使用 dataclass Schema 序列化响应。
"""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.apps.doc.models_v2 import (
    IspDocument, IspDocPermission, IspComment, IspNotification,
    IspAttachment, IspOrgNode, IspOrgUser, IspGroup, IspGroupMember,
)
from backend.apps.doc.services import PermissionService
from .schemas import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentTreeNode,
    CommentCreate, CommentUpdate, CommentResponse,
    PermissionGrant, PermissionBatch, PermissionResponse,
    NotificationResponse, AttachmentResponse,
    PaginatedResponse,
)

logger = logging.getLogger(__name__)


# ================================================================
# 9.1.3 + 9.1.4 Document CRUD + Tree
# ================================================================

@login_required
def doc_list(request):
    """文档列表。

    GET /api/documents/?page=1&page_size=20&status=1&search=xxx
    """
    page = _int(request.GET, "page", 1)
    page_size = _int(request.GET, "page_size", 20)
    status = _int(request.GET, "status", None)
    search = request.GET.get("search", "").strip()

    qs = IspDocument.objects.filter(is_deleted=False)
    if status is not None:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(content_plain__icontains=search))

    total = qs.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    docs = qs.order_by("-updated_at")[offset:offset + page_size]

    items = [DocumentResponse.from_model(d) for d in docs]

    return JsonResponse(_asdict(PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=total_pages, has_next=page < total_pages, has_prev=page > 1,
    )))


@csrf_exempt
@login_required
def doc_create(request):
    """创建文档。

    POST /api/documents/
    Body: {title, content?, content_json?, parent_id?, editor_mode?, status?, is_public?}
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    data = _parse_body(request)
    if not data.get("title"):
        return HttpResponseBadRequest("缺少 title 字段")

    parent = None
    if data.get("parent_id"):
        try:
            parent = IspDocument.objects.get(pk=data["parent_id"])
        except IspDocument.DoesNotExist:
            return HttpResponseBadRequest("父文档不存在")

    doc = IspDocument.objects.create(
        title=data["title"],
        content=data.get("content", ""),
        content_json=data.get("content_json", {}),
        content_plain=data.get("content", ""),
        parent=parent,
        editor_mode=data.get("editor_mode", 2),
        status=data.get("status", 1),
        is_public=data.get("is_public", True),
        created_by=request.user,
    )

    return JsonResponse(_asdict(DocumentResponse.from_model(doc)), status=201)


@login_required
@require_http_methods(["GET"])
def doc_detail(request, doc_id: str):
    """文档详情。

    GET /api/documents/<doc_id>/
    """
    doc = get_object_or_404(IspDocument, pk=doc_id, is_deleted=False)
    return JsonResponse(_asdict(DocumentResponse.from_model(doc)))


@csrf_exempt
@login_required
def doc_update(request, doc_id: str):
    """更新文档。

    PUT /api/documents/<doc_id>/
    """
    if request.method not in ("PUT", "PATCH"):
        return JsonResponse({"error": "仅支持 PUT/PATCH"}, status=405)

    doc = get_object_or_404(IspDocument, pk=doc_id, is_deleted=False)
    if doc.created_by != request.user and not request.user.is_superuser:
        return JsonResponse({"error": "无权编辑此文档"}, status=403)

    data = _parse_body(request)

    for field in ("title", "content", "status", "editor_mode", "is_public",
                  "is_watermark", "watermark_type", "watermark_value"):
        if field in data:
            setattr(doc, field, data[field])
    if "content_json" in data:
        doc.content_json = data["content_json"]
    if "parent_id" in data:
        doc.parent = IspDocument.objects.filter(pk=data["parent_id"]).first() if data["parent_id"] else None
    if "sort_order" in data:
        doc.sort_order = data["sort_order"]

    doc.save()
    return JsonResponse(_asdict(DocumentResponse.from_model(doc)))


@csrf_exempt
@login_required
def doc_delete(request, doc_id: str):
    """软删除文档。

    DELETE /api/documents/<doc_id>/
    """
    if request.method != "DELETE":
        return JsonResponse({"error": "仅支持 DELETE"}, status=405)

    doc = get_object_or_404(IspDocument, pk=doc_id, is_deleted=False)
    if doc.created_by != request.user and not request.user.is_superuser:
        return JsonResponse({"error": "无权删除此文档"}, status=403)

    doc.is_deleted = True
    doc.deleted_at = timezone.now()
    doc.deleted_by = request.user
    doc.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["GET"])
def doc_tree(request):
    """文档树。

    GET /api/documents/tree/?parent_id=<id>
    不传 parent_id 返回根节点列表。
    """
    parent_id = request.GET.get("parent_id") or None

    if parent_id:
        nodes = IspDocument.objects.filter(parent_id=parent_id, is_deleted=False)
    else:
        nodes = IspDocument.objects.filter(parent__isnull=True, is_deleted=False)

    nodes = nodes.order_by("sort_order", "-updated_at")

    def _build_node(doc) -> dict:
        children = IspDocument.objects.filter(parent=doc, is_deleted=False).order_by("sort_order")
        return _asdict(DocumentTreeNode(
            id=str(doc.id), title=doc.title,
            status=doc.status, is_public=doc.is_public,
            children=[_build_node(c) for c in children],
        ))

    return JsonResponse({"tree": [_build_node(n) for n in nodes]})


# ================================================================
# 9.1.5 Comment API
# ================================================================

@login_required
@require_http_methods(["GET"])
def comment_list(request, doc_id: str):
    """文档评论列表。

    GET /api/documents/<doc_id>/comments/
    """
    doc = get_object_or_404(IspDocument, pk=doc_id, is_deleted=False)

    comments = IspComment.objects.filter(document=doc, parent__isnull=True).order_by("-created_at")
    items = []
    for c in comments:
        item = _asdict(CommentResponse.from_model(c))
        replies = IspComment.objects.filter(parent=c).order_by("created_at")
        item["replies"] = [_asdict(CommentResponse.from_model(r)) for r in replies]
        items.append(item)

    return JsonResponse({"items": items})


@csrf_exempt
@login_required
def comment_create(request, doc_id: str):
    """创建评论。

    POST /api/documents/<doc_id>/comments/
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    doc = get_object_or_404(IspDocument, pk=doc_id, is_deleted=False)
    data = _parse_body(request)

    if not data.get("content"):
        return HttpResponseBadRequest("缺少 content 字段")

    parent = None
    if data.get("parent_id"):
        parent = IspComment.objects.filter(pk=data["parent_id"], document=doc).first()

    comment = IspComment.objects.create(
        document=doc,
        parent=parent,
        content=data["content"],
        anchor_id=data.get("anchor_id", ""),
        anchor_text=data.get("anchor_text", ""),
        created_by=request.user,
    )
    return JsonResponse(_asdict(CommentResponse.from_model(comment)), status=201)


@csrf_exempt
@login_required
def comment_delete(request, comment_id: str):
    """删除评论。

    DELETE /api/comments/<comment_id>/
    """
    if request.method != "DELETE":
        return JsonResponse({"error": "仅支持 DELETE"}, status=405)

    comment = get_object_or_404(IspComment, pk=comment_id)
    if comment.created_by != request.user and not request.user.is_superuser:
        return JsonResponse({"error": "无权删除"}, status=403)

    comment.delete()
    return JsonResponse({"success": True})


# ================================================================
# 9.1.6 Permission API
# ================================================================

@login_required
@require_http_methods(["GET"])
def permission_list(request, doc_id: str):
    """文档权限列表。

    GET /api/documents/<doc_id>/permissions/
    """
    doc = get_object_or_404(IspDocument, pk=doc_id, is_deleted=False)
    perms = IspDocPermission.objects.filter(document=doc)
    items = [_asdict(PermissionResponse.from_model(p)) for p in perms]
    return JsonResponse({"items": items})


@csrf_exempt
@login_required
def permission_grant(request, doc_id: str):
    """授予权限。

    POST /api/documents/<doc_id>/permissions/
    Body: {target_type, target_id, permission}
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    doc = get_object_or_404(IspDocument, pk=doc_id, is_deleted=False)
    if doc.created_by != request.user and not request.user.is_superuser:
        return JsonResponse({"error": "无权管理权限"}, status=403)

    data = _parse_body(request)
    target_type = data.get("target_type", "")
    target_id = _int_data(data, "target_id", 0)

    if target_type not in ("user", "group", "org") or not target_id:
        return HttpResponseBadRequest("target_type 和 target_id 参数无效")

    permission = data.get("permission", "view")
    if permission not in ("view", "edit", "admin"):
        return HttpResponseBadRequest("permission 必须为 view/edit/admin")

    perm, created = IspDocPermission.objects.update_or_create(
        document=doc, target_type=target_type, target_id=target_id,
        defaults={"permission": permission, "granted_by": request.user},
    )
    return JsonResponse(_asdict(PermissionResponse.from_model(perm)),
                        status=201 if created else 200)


@csrf_exempt
@login_required
def permission_revoke(request, doc_id: str, perm_id: str):
    """撤销权限。

    DELETE /api/documents/<doc_id>/permissions/<perm_id>/
    """
    if request.method != "DELETE":
        return JsonResponse({"error": "仅支持 DELETE"}, status=405)

    perm = get_object_or_404(IspDocPermission, pk=perm_id, document_id=doc_id)
    perm.delete()
    return JsonResponse({"success": True})


@csrf_exempt
@login_required
def permission_batch(request, doc_id: str):
    """批量授权/撤销。

    POST /api/documents/<doc_id>/permissions/batch/
    Body: {grants: [{target_type, target_id, permission}], revokes: [{target_type, target_id}]}
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    doc = get_object_or_404(IspDocument, pk=doc_id, is_deleted=False)
    if doc.created_by != request.user:
        return JsonResponse({"error": "无权管理权限"}, status=403)

    data = _parse_body(request)
    created = 0
    deleted = 0

    for g in data.get("grants", []):
        IspDocPermission.objects.update_or_create(
            document=doc, target_type=g.get("target_type", "user"),
            target_id=g.get("target_id", 0),
            defaults={"permission": g.get("permission", "view"), "granted_by": request.user},
        )
        created += 1

    for r in data.get("revokes", []):
        IspDocPermission.objects.filter(
            document=doc, target_type=r.get("target_type", "user"),
            target_id=r.get("target_id", 0),
        ).delete()
        deleted += 1

    return JsonResponse({"success": True, "created": created, "deleted": deleted})


# ================================================================
# 9.1.10 Notification API
# ================================================================

@login_required
@require_http_methods(["GET"])
def notification_list(request):
    """通知列表。

    GET /api/notifications/?page=1&page_size=20&is_read=0
    """
    page = _int(request.GET, "page", 1)
    page_size = _int(request.GET, "page_size", 20)
    is_read = request.GET.get("is_read")

    qs = IspNotification.objects.filter(recipient=request.user).order_by("-created_at")
    if is_read is not None:
        qs = qs.filter(is_read=is_read == "1")

    total = qs.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size

    items = [_asdict(NotificationResponse.from_model(n)) for n in qs[offset:offset + page_size]]

    return JsonResponse(_asdict(PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=total_pages, has_next=page < total_pages, has_prev=page > 1,
    )))


@csrf_exempt
@login_required
def notification_mark_read(request):
    """标记已读。

    POST /api/notifications/read/
    Body: {notification_ids: ["id1", "id2"]} 或空（全部已读）
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    data = _parse_body(request) if request.body else {}
    ids = data.get("notification_ids")

    qs = IspNotification.objects.filter(recipient=request.user, is_read=False)
    if ids:
        qs = qs.filter(id__in=ids)
    count = qs.update(is_read=True)

    return JsonResponse({"marked_read": count})


@login_required
@require_http_methods(["GET"])
def notification_unread_count(request):
    """未读通知数。

    GET /api/notifications/unread-count/
    """
    count = IspNotification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({"unread_count": count})


# ================================================================
# 9.1.11 Attachment API
# ================================================================

@login_required
@require_http_methods(["GET"])
def attachment_list(request, doc_id: str = None):
    """附件列表。

    GET /api/documents/<doc_id>/attachments/
    GET /api/attachments/ (所有附件)
    """
    qs = IspAttachment.objects.all()
    if doc_id:
        get_object_or_404(IspDocument, pk=doc_id, is_deleted=False)
        qs = qs.filter(document_id=doc_id)

    items = [_asdict(AttachmentResponse.from_model(a)) for a in qs.order_by("-created_at")]
    return JsonResponse({"items": items})


# ================================================================
# 9.1.7 User / 9.1.8 Org / 9.1.9 Group — 轻量封装
# ================================================================

@login_required
@require_http_methods(["GET"])
def org_tree(request):
    """组织架构树。

    GET /api/org/tree/
    """
    nodes = IspOrgNode.objects.filter(parent__isnull=True).order_by("sort_order")

    def _build(node):
        children = IspOrgNode.objects.filter(parent=node).order_by("sort_order")
        return {
            "id": str(node.id), "name": node.name,
            "parent_id": str(node.parent_id) if node.parent_id else None,
            "depth": node.depth, "external_source": node.external_source,
            "children": [_build(c) for c in children],
        }

    return JsonResponse({"tree": [_build(n) for n in nodes]})


@login_required
@require_http_methods(["GET"])
def group_list(request):
    """用户分组列表。

    GET /api/groups/
    """
    groups = IspGroup.objects.all().order_by("name")
    items = [{
        "id": str(g.id), "name": g.name, "description": g.description,
        "owner_name": g.owner.username if g.owner else "",
        "member_count": g.member_count, "created_at": g.created_at.isoformat(),
    } for g in groups]
    return JsonResponse({"items": items})


# ================================================================
# Utility
# ================================================================

def _parse_body(request) -> dict:
    try:
        return json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return {}


def _int(params, key, default=0):
    try:
        return int(params.get(key, default))
    except (TypeError, ValueError):
        return default or 0


def _int_data(data, key, default=0):
    try:
        return int(data.get(key, default))
    except (TypeError, ValueError):
        return default or 0


def _asdict(obj) -> dict:
    """将 dataclass 实例转为 dict，递归处理嵌套对象。"""
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for f_name in obj.__dataclass_fields__:
            val = getattr(obj, f_name)
            if isinstance(val, list):
                result[f_name] = [_asdict(v) for v in val]
            elif hasattr(val, "__dataclass_fields__"):
                result[f_name] = _asdict(val)
            else:
                result[f_name] = val
        return result
    return obj
