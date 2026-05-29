"""存储安全工具：文件名校验、MIME 类型检测、路径穿越防护。"""
import hashlib
import os
import re
import uuid
from datetime import datetime
from typing import BinaryIO, Optional

# 常见文件类型的魔数签名
MAGIC_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # RIFF....WEBP
    b"BM": "image/bmp",
    b"II*\x00": "image/tiff",
    b"MM\x00*": "image/tiff",
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/zip",
    b"Rar!\x1a\x07": "application/x-rar-compressed",
}


def generate_storage_key(prefix: str = "", extension: str = "") -> str:
    """生成安全的存储 Key（UUID + 日期，防碰撞、防路径穿越）。

    Args:
        prefix: 前缀路径（如 "images" → "images/202605/"）
        extension: 文件扩展名（不含点号）

    Returns:
        格式: <prefix>/YYYYMM/<uuid>.<ext>
    """
    date_part = datetime.now().strftime("%Y%m")
    uid = uuid.uuid4().hex[:16]
    key = f"{date_part}/{uid}"
    if prefix:
        safe_prefix = sanitize_path(prefix)
        key = f"{safe_prefix}/{key}"
    if extension:
        safe_ext = re.sub(r"[^a-zA-Z0-9]", "", extension).lower()
        key = f"{key}.{safe_ext}"
    return key


def sanitize_path(path: str) -> str:
    """移除路径穿越字符 (../, ..\\, null byte 等)。"""
    path = path.replace("\x00", "")
    path = path.replace("\\", "/")
    # 移除连续的斜杠
    path = re.sub(r"/{2,}", "/", path)
    # 分割后再拼接，去掉每段中的危险字符
    parts = []
    for part in path.split("/"):
        if part in ("", ".", ".."):
            continue
        parts.append(re.sub(r"[^a-zA-Z0-9._\-]", "_", part))
    return "/".join(parts)


def sanitize_filename(filename: str) -> str:
    """清理用户提供的文件名，移除路径穿越和危险字符。"""
    name = filename.replace("\x00", "")
    name = name.replace("\\", "/")
    name = os.path.basename(name)
    return re.sub(r"[^a-zA-Z0-9._\-]", "_", name)


def detect_content_type(file_bytes: bytes) -> str:
    """通过文件魔数检测真实 MIME 类型。

    Returns:
        MIME 类型字符串，无法识别时返回 "application/octet-stream"
    """
    for magic, mime_type in MAGIC_SIGNATURES.items():
        if file_bytes.startswith(magic):
            if magic == b"RIFF" and file_bytes[8:12] == b"WEBP":
                return "image/webp"
            return mime_type
    return "application/octet-stream"


def validate_content_type(
    file_bytes: bytes,
    allowed_extensions: list[str],
) -> tuple[bool, str]:
    """校验文件内容的真实类型是否在允许列表中。

    Args:
        file_bytes: 文件前几个字节（用于魔数检测）
        allowed_extensions: 允许的扩展名列表（如 ['jpg', 'png', 'gif']）

    Returns:
        (是否允许, 检测到的 MIME 类型)
    """
    detected = detect_content_type(file_bytes)
    # 从 MIME 类型提取子类型
    mime_subtype = detected.split("/")[-1] if "/" in detected else detected

    # 特殊映射：jpeg → jpg
    subtype_map = {"jpeg": "jpg"}
    mapped_subtype = subtype_map.get(mime_subtype, mime_subtype)

    if mapped_subtype in allowed_extensions:
        return True, detected
    return False, detected


def file_checksum(file_path: str, algorithm: str = "sha256") -> str:
    """计算文件哈希值。"""
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_safe_path(base_dir: str, key: str) -> bool:
    """验证 key 解析后是否在 base_dir 范围内。"""
    full_path = os.path.realpath(os.path.join(base_dir, key.lstrip("/")))
    real_base = os.path.realpath(base_dir)
    return full_path.startswith(real_base + os.sep) or full_path == real_base
