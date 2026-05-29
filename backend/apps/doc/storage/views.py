"""存储增强 API 端点（1.3.2 / 1.7.2 / 1.4.2）。

- 预签名上传 URL 生成（S3 / OSS / COS / Kodo）
- 上传进度 SSE 事件流
- 图片处理 URL 生成
"""
import json
import uuid
import time
from datetime import datetime

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .config import get_storage
from .router import StorageRouter


# ================================================================
# 1.3.2 预签名上传 URL
# ================================================================

@csrf_exempt
def presigned_upload_url(request):
    """生成预签名上传 URL。

    POST /api/storage/presigned-upload/
    Body: {"file_name": "photo.png", "content_type": "image/png", "file_size": 102400}

    返回:
        {"upload_url": "https://...", "key": "uploads/uuid/photo.png", "expires_in": 3600}
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "无效的 JSON 请求体"}, status=400)

    file_name = body.get("file_name", "untitled")
    content_type = body.get("content_type", "application/octet-stream")
    file_size = body.get("file_size", 0)

    router = StorageRouter()
    backend = router.resolve(content_type, file_size)
    key = f"uploads/{datetime.now().strftime('%Y%m')}/{uuid.uuid4().hex[:12]}/{file_name}"

    try:
        upload_url = backend.get_presigned_upload_url(key, content_type, expires=3600)
    except NotImplementedError:
        return JsonResponse({
            "error": f"存储后端 '{backend.name}' 不支持预签名上传，请使用普通上传接口"
        }, status=501)

    return JsonResponse({
        "upload_url": upload_url,
        "key": key,
        "expires_in": 3600,
        "backend": backend.name,
    })


# ================================================================
# 1.7.2 上传进度 SSE 推送
# ================================================================

_progress_store: dict[str, dict] = {}


def set_upload_progress(upload_id: str, progress: dict):
    """记录上传进度（由分片上传视图调用）。"""
    _progress_store[upload_id] = {
        **progress,
        "updated_at": time.time(),
    }


def upload_progress_stream(request, upload_id: str):
    """SSE 事件流：推送上传进度。

    GET /api/storage/upload-progress/<upload_id>/

    每秒推送一次进度，上传完成或超时后关闭连接。
    """
    def event_stream():
        last_percent = -1
        for _ in range(300):  # 最多 5 分钟
            progress = _progress_store.get(upload_id, {})
            pct = progress.get("percent", 0)
            if pct != last_percent or progress.get("status") == "complete":
                yield f"data: {json.dumps(progress)}\n\n"
                last_percent = pct
            if progress.get("status") in ("complete", "error", "aborted"):
                _progress_store.pop(upload_id, None)
                break
            time.sleep(1)

    return StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ================================================================
# 1.4.2 / 1.3.3 / 1.5.2 图片处理 URL 生成
# ================================================================

@csrf_exempt
@require_http_methods(["POST"])
def process_image_url(request):
    """生成图片处理 URL（缩略图、水印、格式转换）。

    POST /api/storage/process-image/
    Body: {
        "key": "images/uuid/photo.png",
        "operations": {
            "resize": {"width": 200, "height": 200, "fit": "cover"},
            "format": "webp",
            "quality": 80
        }
    }

    返回:
        {"processed_url": "https://...?x-oss-process=..."}
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "无效的 JSON"}, status=400)

    key = body.get("key")
    operations = body.get("operations", {})

    if not key:
        return JsonResponse({"error": "缺少 key 参数"}, status=400)

    backend = get_storage()

    try:
        url = backend.process_image(key, operations)
    except NotImplementedError:
        # 回退：返回原始 URL
        url = backend.get_url(key)
    except AttributeError:
        url = backend.get_url(key)

    return JsonResponse({"processed_url": url, "original_key": key})
