"""图标搜索与上传 API 视图（7.1.1 / 7.1.2）。"""
import json
import os
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .catalog import search_icons

CUSTOM_ICONS_DIR = os.path.join(settings.MEDIA_ROOT, "custom_icons")


@login_required
def icon_search(request):
    """搜索 Phosphor 图标 + 自定义图标。

    GET 参数:
        q         — 搜索关键词（名称或标签）
        category  — 分类过滤
        page      — 页码（默认 1）
        page_size — 每页数量（默认 50）
    """
    query = request.GET.get("q", "")
    category = request.GET.get("category", "")
    page = int(request.GET.get("page", 1))
    page_size = min(int(request.GET.get("page_size", 50)), 200)

    result = search_icons(query=query, category=category, page=page, page_size=page_size)

    # 附加自定义图标
    if category in ("", "custom"):
        custom_icons = _list_custom_icons(query)
        result["custom"] = custom_icons
        result["total"] = result.get("total", 0) + len(custom_icons)

    return JsonResponse(result)


@login_required
def icon_categories(request):
    """返回图标分类列表。"""
    from .catalog import CATEGORY_LABELS

    categories = [{"name": k, "label": v} for k, v in CATEGORY_LABELS.items()]
    categories.append({"name": "custom", "label": "自定义图标"})
    return JsonResponse({"categories": categories})


# ================================================================
# 7.1.2 自定义 SVG 图标上传 API
# ================================================================

@login_required
@csrf_exempt
def custom_icon_upload(request):
    """上传自定义 SVG 图标。

    POST /api/icons/upload/
    Body: multipart/form-data with "file" field (SVG file)

    返回:
        {"id": "custom/uuid", "name": "my-icon", "svg": "<svg>...</svg>"}
    """
    if request.method == "GET":
        return JsonResponse({"icons": _list_custom_icons()})

    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    file = request.FILES.get("file")
    if not file:
        return JsonResponse({"error": "缺少文件"}, status=400)

    if not file.name.lower().endswith(".svg"):
        return JsonResponse({"error": "仅支持 SVG 文件"}, status=400)

    content = file.read().decode("utf-8", errors="ignore")
    if "<svg" not in content.lower():
        return JsonResponse({"error": "无效的 SVG 文件内容"}, status=400)

    icon_id = uuid.uuid4().hex[:12]
    icon_name = request.POST.get("name", os.path.splitext(file.name)[0])
    file_name = f"{icon_id}.svg"

    os.makedirs(CUSTOM_ICONS_DIR, exist_ok=True)
    file_path = os.path.join(CUSTOM_ICONS_DIR, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    meta_path = os.path.join(CUSTOM_ICONS_DIR, f"{icon_id}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"id": icon_id, "name": icon_name, "file": file_name}, f)

    return JsonResponse({
        "id": icon_id,
        "name": icon_name,
        "svg": content,
        "url": f"/media/custom_icons/{file_name}",
    })


@login_required
@csrf_exempt
def custom_icon_delete(request, icon_id: str):
    """删除自定义 SVG 图标。

    DELETE /api/icons/custom/<icon_id>/
    """
    if request.method != "DELETE":
        return JsonResponse({"error": "仅支持 DELETE"}, status=405)

    svg_path = os.path.join(CUSTOM_ICONS_DIR, f"{icon_id}.svg")
    meta_path = os.path.join(CUSTOM_ICONS_DIR, f"{icon_id}.json")

    if os.path.exists(svg_path):
        os.remove(svg_path)
    if os.path.exists(meta_path):
        os.remove(meta_path)

    return JsonResponse({"deleted": icon_id})


def _list_custom_icons(query: str = "") -> list[dict]:
    """列出自定义图标。"""
    if not os.path.isdir(CUSTOM_ICONS_DIR):
        return []
    icons = []
    for fname in os.listdir(CUSTOM_ICONS_DIR):
        if fname.endswith(".svg"):
            icon_id = fname.replace(".svg", "")
            meta_path = os.path.join(CUSTOM_ICONS_DIR, f"{icon_id}.json")
            name = icon_id
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    name = meta.get("name", icon_id)
            if query and query.lower() not in name.lower():
                continue
            with open(os.path.join(CUSTOM_ICONS_DIR, fname), "r", encoding="utf-8") as f:
                svg = f.read()
            icons.append({
                "id": icon_id,
                "name": name,
                "svg": svg,
                "url": f"/media/custom_icons/{fname}",
            })
    return icons
