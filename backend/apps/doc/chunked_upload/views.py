"""分片上传 API 视图。

支持大文件分片上传：初始化 → 上传分片 → 完成后通过 StorageBackend 组装保存。
"""
import logging
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from backend.apps.doc.chunked_upload.models import ChunkedUpload
from backend.apps.doc.storage import get_storage
from backend.apps.doc.storage.security import generate_storage_key, sanitize_filename

logger = logging.getLogger(__name__)

# 分片临时目录：MEDIA_ROOT/chunks/
CHUNKS_DIR = os.path.join(settings.MEDIA_ROOT, "chunks")


def _get_chunk_dir(upload_id: str) -> str:
    return os.path.join(CHUNKS_DIR, str(upload_id))


@csrf_exempt
@login_required
def chunked_upload_init(request):
    """初始化分片上传会话。

    POST /api/upload/chunked/init/
    Body: {filename, file_size, chunk_size, content_type?}
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    filename = request.POST.get("filename") or request.GET.get("filename") or ""
    file_size = _parse_int(request.POST.get("file_size", "0"))
    chunk_size = _parse_int(request.POST.get("chunk_size", str(1024 * 1024 * 5)))
    content_type = request.POST.get("content_type", "")

    if not filename or file_size <= 0:
        return HttpResponseBadRequest("缺少 filename 或 file_size 参数")

    filename = sanitize_filename(filename)
    total_chunks = max(1, (file_size + chunk_size - 1) // chunk_size)

    upload = ChunkedUpload.objects.create(
        filename=filename,
        file_size=file_size,
        chunk_size=chunk_size,
        total_chunks=total_chunks,
        content_type=content_type,
    )

    os.makedirs(_get_chunk_dir(upload.upload_id), exist_ok=True)

    return JsonResponse({
        "upload_id": str(upload.upload_id),
        "total_chunks": total_chunks,
        "chunk_size": chunk_size,
    })


@csrf_exempt
@login_required
def chunked_upload_chunk(request, upload_id: str):
    """上传单个分片。

    POST /api/upload/chunked/<upload_id>/
    Body: multipart with chunk_index (int), file (bytes)
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    upload = _get_upload(upload_id)
    if upload is None:
        return HttpResponseBadRequest("无效的上传会话")

    chunk_index = _parse_int(request.POST.get("chunk_index", "-1"))
    if chunk_index < 0:
        return HttpResponseBadRequest("缺少 chunk_index 参数")

    chunk_file = request.FILES.get("file")
    if not chunk_file:
        return HttpResponseBadRequest("缺少分片文件")

    chunk_dir = _get_chunk_dir(upload_id)
    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index}")

    with open(chunk_path, "wb") as dst:
        for data in chunk_file.chunks(8192):
            dst.write(data)

    # 记录已上传分片
    chunks = upload.uploaded_chunks or []
    if chunk_index not in chunks:
        chunks.append(chunk_index)
        upload.uploaded_chunks = chunks
        upload.save(update_fields=["uploaded_chunks", "updated_at"])

    return JsonResponse({
        "chunk_index": chunk_index,
        "uploaded_count": len(chunks),
        "total_chunks": upload.total_chunks,
        "progress": round(upload.progress, 1),
        "is_ready": upload.is_ready,
    })


@csrf_exempt
@login_required
def chunked_upload_complete(request, upload_id: str):
    """完成分片上传：组装分片并通过 StorageBackend 保存。

    POST /api/upload/chunked/<upload_id>/complete/
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    upload = _get_upload(upload_id)
    if upload is None:
        return HttpResponseBadRequest("无效的上传会话")

    if not upload.is_ready:
        missing = upload.total_chunks - len(upload.uploaded_chunks or [])
        return JsonResponse({
            "error": f"上传未完成，还缺少 {missing} 个分片",
            "uploaded_chunks": upload.uploaded_chunks,
            "total_chunks": upload.total_chunks,
        }, status=400)

    chunk_dir = _get_chunk_dir(upload_id)

    try:
        # 按分片顺序组装文件
        assembled_path = os.path.join(chunk_dir, "assembled")
        with open(assembled_path, "wb") as out:
            for i in range(upload.total_chunks):
                chunk_path = os.path.join(chunk_dir, f"chunk_{i}")
                if not os.path.exists(chunk_path):
                    return HttpResponseBadRequest(f"分片 {i} 缺失，请重新上传")
                with open(chunk_path, "rb") as chunk_f:
                    while True:
                        data = chunk_f.read(8192)
                        if not data:
                            break
                        out.write(data)

        # 通过 StorageBackend 上传
        storage = get_storage()
        ext = os.path.splitext(upload.filename)[1]
        storage_key = generate_storage_key(prefix="attachments", extension=ext)

        with open(assembled_path, "rb") as f:
            result = storage.upload(f, storage_key, content_type=upload.content_type or None)

        upload.status = "completed"
        upload.storage_key = storage_key
        upload.save(update_fields=["status", "storage_key", "updated_at"])

    except Exception:
        logger.exception("分片上传完成阶段失败")
        return JsonResponse({"error": "文件组装失败"}, status=500)
    finally:
        # 清理临时文件
        _cleanup_chunks(chunk_dir)

    return JsonResponse({
        "success": True,
        "url": result.url,
        "storage_key": storage_key,
        "file_size": upload.file_size,
        "filename": upload.filename,
    })


@csrf_exempt
@login_required
def chunked_upload_abort(request, upload_id: str):
    """取消分片上传并清理已上传分片。

    DELETE /api/upload/chunked/<upload_id>/
    """
    if request.method != "DELETE":
        return JsonResponse({"error": "仅支持 DELETE"}, status=405)

    upload = ChunkedUpload.objects.filter(upload_id=upload_id).first()
    if not upload:
        return JsonResponse({"error": "无效的上传会话"}, status=400)

    _cleanup_chunks(_get_chunk_dir(upload_id))
    upload.delete()

    return JsonResponse({"deleted": True})


@login_required
def chunked_upload_status(request, upload_id: str):
    """查询上传进度。

    GET /api/upload/chunked/<upload_id>/
    """
    upload = _get_upload(upload_id)
    if upload is None:
        return HttpResponseBadRequest("无效的上传会话")

    return JsonResponse({
        "upload_id": str(upload.upload_id),
        "filename": upload.filename,
        "file_size": upload.file_size,
        "total_chunks": upload.total_chunks,
        "uploaded_chunks": upload.uploaded_chunks,
        "progress": round(upload.progress, 1),
        "is_ready": upload.is_ready,
        "status": upload.status,
    })


def _get_upload(upload_id: str):
    try:
        return ChunkedUpload.objects.get(upload_id=upload_id)
    except ChunkedUpload.DoesNotExist:
        return None


def _cleanup_chunks(chunk_dir: str):
    """清理分片临时目录。"""
    try:
        if os.path.isdir(chunk_dir):
            import shutil
            shutil.rmtree(chunk_dir)
    except OSError:
        logger.warning("无法清理分片临时目录: %s", chunk_dir)


def _parse_int(val) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0
