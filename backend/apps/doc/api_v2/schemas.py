"""v2.0 REST API Schema 定义。

使用 dataclass 定义所有请求/响应的数据结构，不依赖 Pydantic。
视图函数在入口处进行类型校验和默认值填充。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ================================================================
# Document
# ================================================================

@dataclass
class DocumentCreate:
    title: str
    content: str = ""
    content_json: dict = field(default_factory=dict)
    parent_id: str | None = None
    editor_mode: int = 2
    status: int = 1
    is_public: bool = True


@dataclass
class DocumentUpdate:
    title: str | None = None
    content: str | None = None
    content_json: dict | None = None
    parent_id: str | None = None
    sort_order: int | None = None
    editor_mode: int | None = None
    status: int | None = None
    is_public: bool | None = None
    is_watermark: bool | None = None
    watermark_type: int | None = None
    watermark_value: str | None = None


@dataclass
class DocumentResponse:
    id: str
    title: str
    content: str
    content_json: dict
    parent_id: str | None
    status: int
    editor_mode: int
    is_public: bool
    is_deleted: bool
    is_watermark: bool
    outline: str | None
    created_by: str
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, doc) -> "DocumentResponse":
        return cls(
            id=str(doc.id),
            title=doc.title,
            content=doc.content or "",
            content_json=doc.content_json or {},
            parent_id=str(doc.parent_id) if doc.parent_id else None,
            status=doc.status,
            editor_mode=doc.editor_mode,
            is_public=doc.is_public,
            is_deleted=doc.is_deleted,
            is_watermark=doc.is_watermark,
            outline=doc.outline,
            created_by=doc.created_by.username if doc.created_by else "",
            created_at=doc.created_at.isoformat() if doc.created_at else "",
            updated_at=doc.updated_at.isoformat() if doc.updated_at else "",
        )


@dataclass
class DocumentTreeNode:
    """文档树节点。"""
    id: str
    title: str
    status: int
    is_public: bool
    children: list["DocumentTreeNode"] = field(default_factory=list)


@dataclass
class PaginatedResponse:
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool = False
    has_prev: bool = False


# ================================================================
# Comment
# ================================================================

@dataclass
class CommentCreate:
    content: str
    parent_id: str | None = None
    anchor_id: str = ""
    anchor_text: str = ""


@dataclass
class CommentUpdate:
    content: str | None = None
    is_resolved: bool | None = None


@dataclass
class CommentResponse:
    id: str
    document_id: str
    parent_id: str | None
    content: str
    anchor_id: str
    anchor_text: str
    is_resolved: bool
    created_by: str
    created_at: str
    updated_at: str
    replies: list["CommentResponse"] = field(default_factory=list)

    @classmethod
    def from_model(cls, comment) -> "CommentResponse":
        return cls(
            id=str(comment.id),
            document_id=str(comment.document_id),
            parent_id=str(comment.parent_id) if comment.parent_id else None,
            content=comment.content,
            anchor_id=comment.anchor_id or "",
            anchor_text=comment.anchor_text or "",
            is_resolved=comment.is_resolved,
            created_by=comment.created_by.username if comment.created_by else "",
            created_at=comment.created_at.isoformat() if comment.created_at else "",
            updated_at=comment.updated_at.isoformat() if comment.updated_at else "",
        )


# ================================================================
# Permission
# ================================================================

@dataclass
class PermissionGrant:
    target_type: str  # user / group / org
    target_id: int
    permission: str  # view / edit / admin


@dataclass
class PermissionBatch:
    grants: list[PermissionGrant] = field(default_factory=list)
    revokes: list[PermissionGrant] = field(default_factory=list)


@dataclass
class PermissionResponse:
    id: str
    document_id: str
    target_type: str
    target_id: int
    permission: str
    target_name: str = ""
    granted_by: str = ""
    created_at: str = ""

    @classmethod
    def from_model(cls, perm) -> "PermissionResponse":
        return cls(
            id=str(perm.id),
            document_id=str(perm.document_id),
            target_type=perm.target_type,
            target_id=perm.target_id,
            permission=perm.permission,
            granted_by=perm.granted_by.username if getattr(perm, 'granted_by', None) else "",
            created_at=perm.created_at.isoformat() if perm.created_at else "",
        )


# ================================================================
# Notification
# ================================================================

@dataclass
class NotificationResponse:
    id: str
    recipient_id: int
    sender_name: str
    event_type: str
    title: str
    body: str
    link: str
    is_read: bool
    created_at: str

    @classmethod
    def from_model(cls, n) -> "NotificationResponse":
        return cls(
            id=str(n.id),
            recipient_id=n.recipient_id,
            sender_name=n.sender.username if n.sender else "",
            event_type=n.event_type,
            title=n.title,
            body=n.body or "",
            link=n.link or "",
            is_read=n.is_read,
            created_at=n.created_at.isoformat() if n.created_at else "",
        )


# ================================================================
# Attachment
# ================================================================

@dataclass
class AttachmentResponse:
    id: str
    file_name: str
    file_size: int
    content_type: str
    storage_key: str
    download_url: str
    uploaded_by: str
    created_at: str

    @classmethod
    def from_model(cls, a) -> "AttachmentResponse":
        return cls(
            id=str(a.id),
            file_name=a.file_name,
            file_size=a.file_size,
            content_type=a.content_type,
            storage_key=a.storage_key,
            download_url=a.download_url or "",
            uploaded_by=a.uploaded_by.username if a.uploaded_by else "",
            created_at=a.created_at.isoformat() if a.created_at else "",
        )


# ================================================================
# User / Profile
# ================================================================

@dataclass
class UserProfileResponse:
    user_id: int
    username: str
    email: str
    avatar: str
    gender: str
    phone: str
    bio: str
    oauth_bindings: list[str] = field(default_factory=list)


# ================================================================
# Org / Group (simplified)
# ================================================================

@dataclass
class OrgNodeResponse:
    id: str
    name: str
    parent_id: str | None
    depth: int
    external_source: str
    children: list["OrgNodeResponse"] = field(default_factory=list)


@dataclass
class GroupResponse:
    id: str
    name: str
    description: str
    owner_name: str
    member_count: int
    created_at: str
