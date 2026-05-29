"""文档 API 路由（FastAPI 版本）。

桥接 Django ORM 的 v2.0 isp_documents 模型。
后续可逐步迁移为纯 SQLAlchemy 异步查询。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ..auth import get_current_user, CurrentUser, get_optional_user
from ..dependencies import get_django_doc_model

router = APIRouter()


# ---- Pydantic Schemas ----

class DocumentOut(BaseModel):
    id: str
    title: str
    content: str = ""
    status: int = 1
    editor_mode: int = 2
    is_public: bool = True
    is_deleted: bool = False
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""

    model_config = {"from_attributes": True}


class DocumentCreate(BaseModel):
    title: str
    content: str = ""
    parent_id: Optional[str] = None
    editor_mode: int = 2
    status: int = 1
    is_public: bool = True


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[int] = None
    is_public: Optional[bool] = None


class PaginatedDocuments(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---- Routes ----

@router.get("/documents/", response_model=PaginatedDocuments)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """获取文档列表。"""
    IspDocument = get_django_doc_model()

    qs = IspDocument.objects.filter(is_deleted=False)
    if search:
        from django.db.models import Q
        qs = qs.filter(Q(title__icontains=search) | Q(content_plain__icontains=search))

    total = qs.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size

    docs = qs.order_by("-updated_at")[offset:offset + page_size]

    items = [
        DocumentOut(
            id=str(d.id), title=d.title, content=d.content or "",
            status=d.status, editor_mode=d.editor_mode,
            is_public=d.is_public, is_deleted=d.is_deleted,
            created_by=d.created_by.username if d.created_by else "",
            created_at=d.created_at.isoformat() if d.created_at else "",
            updated_at=d.updated_at.isoformat() if d.updated_at else "",
        ) for d in docs
    ]

    return PaginatedDocuments(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


@router.get("/documents/{doc_id}/", response_model=DocumentOut)
async def get_document(
    doc_id: str,
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """获取文档详情。"""
    IspDocument = get_django_doc_model()
    try:
        doc = IspDocument.objects.get(pk=doc_id, is_deleted=False)
    except IspDocument.DoesNotExist:
        raise HTTPException(status_code=404, detail="文档不存在")

    return DocumentOut(
        id=str(doc.id), title=doc.title, content=doc.content or "",
        status=doc.status, editor_mode=doc.editor_mode,
        is_public=doc.is_public, is_deleted=doc.is_deleted,
        created_by=doc.created_by.username if doc.created_by else "",
        created_at=doc.created_at.isoformat() if doc.created_at else "",
        updated_at=doc.updated_at.isoformat() if doc.updated_at else "",
    )


@router.post("/documents/", response_model=DocumentOut, status_code=201)
async def create_document(
    body: DocumentCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """创建文档。"""
    IspDocument = get_django_doc_model()
    from django.contrib.auth import get_user_model
    User = get_user_model()
    django_user = User.objects.get(pk=user.id)

    doc = IspDocument.objects.create(
        title=body.title,
        content=body.content,
        content_plain=body.content,
        editor_mode=body.editor_mode,
        status=body.status,
        is_public=body.is_public,
        created_by=django_user,
    )

    return DocumentOut(
        id=str(doc.id), title=doc.title, content=doc.content or "",
        status=doc.status, editor_mode=doc.editor_mode,
        is_public=doc.is_public, is_deleted=doc.is_deleted,
        created_by=django_user.username,
        created_at=doc.created_at.isoformat() if doc.created_at else "",
        updated_at=doc.updated_at.isoformat() if doc.updated_at else "",
    )
