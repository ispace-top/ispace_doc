"""v2.0 全新数据模型。
"""
import uuid

from django.conf import settings
from django.db import models


# ================================================================
# 8.1.1 Document 文档模型
# ================================================================

class IspDocument(models.Model):
    class Status(models.IntegerChoices):
        DRAFT = 0, "草稿"
        PUBLISHED = 1, "已发布"
        ARCHIVED = 2, "已归档"

    class EditorMode(models.IntegerChoices):
        VDITOR = 2, "Vditor"
        ICEEDITOR = 3, "iceEditor"
        LUCKY_SHEET = 4, "Luckysheet"
        MINDMAP = 5, "思维导图"
        DRAWIO = 6, "Draw.io"
        EXCALIDRAW = 7, "Excalidraw"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500, verbose_name="标题")
    content = models.TextField(null=True, blank=True, verbose_name="正文")
    content_json = models.JSONField(null=True, blank=True, default=dict, verbose_name="结构化数据")
    content_plain = models.TextField(null=True, blank=True, verbose_name="纯文本")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="children", verbose_name="父文档")
    sort_order = models.IntegerField(default=9999, verbose_name="排序")
    status = models.IntegerField(choices=Status.choices, default=Status.PUBLISHED, verbose_name="状态")
    editor_mode = models.IntegerField(choices=EditorMode.choices, default=EditorMode.VDITOR,
                                      verbose_name="编辑器模式")
    is_public = models.BooleanField(default=True, verbose_name="公开可见")
    is_deleted = models.BooleanField(default=False, verbose_name="软删除", db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="删除时间")
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="deleted_documents",
                                   verbose_name="删除人")
    is_watermark = models.BooleanField(default=False, verbose_name="水印开关")
    watermark_type = models.IntegerField(default=1, verbose_name="水印类型")
    watermark_value = models.CharField(max_length=250, null=True, blank=True, default="",
                                       verbose_name="水印内容")
    outline = models.TextField(null=True, blank=True, verbose_name="大纲 JSON")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="created_documents", verbose_name="创建者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "isp_documents"
        verbose_name = "文档"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["parent", "status"]),
            models.Index(fields=["sort_order"]),
            models.Index(fields=["is_deleted", "deleted_at"]),
            models.Index(fields=["is_public"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self):
        return self.title


# ================================================================
# 8.1.7 Attachment / Image 文件模型
# ================================================================

class IspAttachment(models.Model):
    """附件 — isp_attachments。
       关联 StorageBackend key 支持多云存储。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(IspDocument, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="attachments", verbose_name="所属文档")
    file_name = models.CharField(max_length=500, verbose_name="文件名")
    file_size = models.BigIntegerField(default=0, verbose_name="文件大小")
    content_type = models.CharField(max_length=128, blank=True, default="", verbose_name="MIME 类型")
    storage_key = models.CharField(max_length=500, verbose_name="存储 Key")
    storage_backend = models.CharField(max_length=32, default="local", verbose_name="存储后端")
    download_url = models.CharField(max_length=1000, blank=True, default="", verbose_name="下载地址")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="uploaded_attachments", verbose_name="上传者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    class Meta:
        db_table = "isp_attachments"
        verbose_name = "附件"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["document"]),
            models.Index(fields=["storage_key"]),
            models.Index(fields=["uploaded_by"]),
        ]

    def __str__(self):
        return self.file_name


class IspImage(models.Model):
    """图片 — isp_images。

    替代旧 Image 模型，关联 StorageBackend key。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=500, verbose_name="文件名")
    file_size = models.BigIntegerField(default=0, verbose_name="文件大小")
    width = models.IntegerField(null=True, blank=True, verbose_name="宽度")
    height = models.IntegerField(null=True, blank=True, verbose_name="高度")
    storage_key = models.CharField(max_length=500, verbose_name="存储 Key")
    storage_backend = models.CharField(max_length=32, default="local", verbose_name="存储后端")
    url = models.CharField(max_length=1000, blank=True, default="", verbose_name="访问地址")
    group = models.ForeignKey("IspImageGroup", null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="images", verbose_name="分组")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="uploaded_images", verbose_name="上传者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    class Meta:
        db_table = "isp_images"
        verbose_name = "图片"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["group"]),
            models.Index(fields=["uploaded_by"]),
        ]

    def __str__(self):
        return self.file_name


class IspImageGroup(models.Model):
    """图片分组 — isp_image_groups。"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64, verbose_name="分组名称")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="image_groups", verbose_name="创建者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "isp_image_groups"
        verbose_name = "图片分组"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


# ================================================================
# 8.1.3 DocPermission 权限模型
# ================================================================

class IspDocPermission(models.Model):
    """文档权限 — isp_doc_permissions。

    替代旧 DocPermission，通过 target_type/target_id 通用关联。
    """

    class Permission(models.TextChoices):
        VIEW = "view", "查看"
        EDIT = "edit", "编辑"
        ADMIN = "admin", "管理"

    class TargetType(models.TextChoices):
        USER = "user", "用户"
        GROUP = "group", "分组"
        ORG = "org", "组织节点"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(IspDocument, on_delete=models.CASCADE,
                                 related_name="permissions", verbose_name="文档")
    target_type = models.CharField(max_length=16, choices=TargetType.choices, verbose_name="目标类型")
    target_id = models.IntegerField(verbose_name="目标 ID")
    permission = models.CharField(max_length=16, choices=Permission.choices, verbose_name="权限级别")
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="isp_granted_permissions",
                                   verbose_name="授权人")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "isp_doc_permissions"
        verbose_name = "文档权限"
        verbose_name_plural = verbose_name
        unique_together = ("document", "target_type", "target_id")
        indexes = [
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["document", "permission"]),
        ]

    def __str__(self):
        return f"{self.document_id} → {self.target_type}:{self.target_id} ({self.permission})"


# ================================================================
# 8.1.4 Comment 评论模型（统一）
# ================================================================

class IspComment(models.Model):
    """统一评论 — isp_comments。

    合并旧 DocComment 和 InlineComment，通过 anchor_id 区分划词评论。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(IspDocument, on_delete=models.CASCADE,
                                 related_name="comments", verbose_name="文档")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE,
                               related_name="replies", verbose_name="父评论")
    content = models.TextField(verbose_name="评论内容")
    anchor_id = models.CharField(max_length=64, null=True, blank=True, default="",
                                 verbose_name="锚点 ID（划词评论）")
    anchor_text = models.CharField(max_length=500, null=True, blank=True, default="",
                                   verbose_name="锚点文本")
    is_resolved = models.BooleanField(default=False, verbose_name="已解决")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="comments", verbose_name="评论者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "isp_comments"
        verbose_name = "评论"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["document", "created_at"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["anchor_id"]),
        ]

    def __str__(self):
        return f"{self.created_by}: {self.content[:50]}"


# ================================================================
# 8.1.5 Notification 通知模型
# ================================================================

class IspNotification(models.Model):
    """通知 — isp_notifications。

    替代旧 Notification，关联 WebHook 事件类型。
    """

    class EventType(models.TextChoices):
        DOC_CREATED = "doc.created", "文档创建"
        DOC_UPDATED = "doc.updated", "文档更新"
        DOC_PUBLISHED = "doc.published", "文档发布"
        DOC_DELETED = "doc.deleted", "文档删除"
        DOC_RESTORED = "doc.restored", "文档恢复"
        COMMENT_CREATED = "comment.created", "评论新增"
        COMMENT_REPLIED = "comment.replied", "评论回复"
        PERM_GRANTED = "perm.granted", "权限授予"
        PERM_REVOKED = "perm.revoked", "权限撤销"
        PERM_APPLY = "perm.apply", "权限申请"
        LIKE_ADDED = "like.added", "点赞"
        USER_MENTION = "user.mention", "@提及"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="isp_notifications", verbose_name="接收者")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="isp_sent_notifications",
                               verbose_name="发送者")
    event_type = models.CharField(max_length=32, choices=EventType.choices, verbose_name="事件类型")
    title = models.CharField(max_length=500, verbose_name="标题")
    body = models.TextField(null=True, blank=True, default="", verbose_name="正文")
    link = models.CharField(max_length=500, blank=True, default="", verbose_name="跳转链接")
    context = models.JSONField(null=True, blank=True, default=dict, verbose_name="上下文数据")
    is_read = models.BooleanField(default=False, verbose_name="已读", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "isp_notifications"
        verbose_name = "通知"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self):
        return f"[{self.event_type}] {self.title}"


# ================================================================
# 8.1.2 UserProfile 用户扩展模型
# ================================================================

class IspUserProfile(models.Model):
    """用户档案 — isp_user_profiles。

    替代旧 UserProfile，支持多 OAuth provider 绑定。
    """

    GENDER_CHOICES = (("M", "男"), ("F", "女"), ("U", "未知"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="isp_profile", verbose_name="用户")
    avatar = models.CharField(max_length=500, blank=True, default="", verbose_name="头像 URL")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default="U", verbose_name="性别")
    phone = models.CharField(max_length=20, null=True, blank=True, unique=True, verbose_name="手机号")
    bio = models.TextField(max_length=512, blank=True, default="", verbose_name="简介")
    notify_settings = models.JSONField(default=dict, verbose_name="通知设置")
    last_active = models.DateTimeField(null=True, blank=True, verbose_name="最后活跃时间")

    class Meta:
        db_table = "isp_user_profiles"
        verbose_name = "用户档案"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.user.username


class IspOAuthBinding(models.Model):
    """OAuth 绑定 — isp_oauth_bindings。

    一个用户可以绑定多个第三方登录方式。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="oauth_bindings", verbose_name="用户")
    provider = models.CharField(max_length=32, verbose_name="提供者")  # wecom/dingtalk/oidc/ldap
    provider_user_id = models.CharField(max_length=256, verbose_name="第三方用户 ID")
    provider_user_name = models.CharField(max_length=256, blank=True, default="", verbose_name="第三方用户名")
    extra_data = models.JSONField(default=dict, verbose_name="额外数据")
    bound_at = models.DateTimeField(auto_now_add=True, verbose_name="绑定时间")

    class Meta:
        db_table = "isp_oauth_bindings"
        verbose_name = "OAuth 绑定"
        verbose_name_plural = verbose_name
        unique_together = ("provider", "provider_user_id")
        indexes = [
            models.Index(fields=["user", "provider"]),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.provider}:{self.provider_user_id}"


# ================================================================
# 8.1.6 组织架构与分组
# ================================================================

class IspOrgNode(models.Model):
    """组织节点 — isp_org_nodes。

    替代旧 OrgNode，支持外部同步来源标识。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, verbose_name="节点名称")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                               related_name="children", verbose_name="父节点")
    path = models.CharField(max_length=512, blank=True, default="", verbose_name="物化路径")
    depth = models.PositiveSmallIntegerField(default=0, verbose_name="深度")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    external_source = models.CharField(max_length=32, blank=True, default="",
                                       verbose_name="外部来源", db_index=True)
    external_id = models.CharField(max_length=128, blank=True, default="", verbose_name="外部 ID")
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="managed_nodes",
                              verbose_name="管理员")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "isp_org_nodes"
        verbose_name = "组织节点"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=["parent", "name"], name="isp_unique_sibling_name")
        ]

    def __str__(self):
        return self.name


class IspOrgUser(models.Model):
    """组织成员 — isp_org_users。

    替代旧 OrgUser。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_node = models.ForeignKey(IspOrgNode, on_delete=models.CASCADE,
                                 related_name="members", verbose_name="组织节点")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="org_assignments", verbose_name="用户")
    is_primary = models.BooleanField(default=False, verbose_name="主属部门")
    position = models.CharField(max_length=64, blank=True, default="", verbose_name="职位")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="加入时间")

    class Meta:
        db_table = "isp_org_users"
        verbose_name = "组织成员"
        verbose_name_plural = verbose_name
        unique_together = ("org_node", "user")

    def __str__(self):
        return f"{self.org_node.name} → {self.user.username}"


class IspGroup(models.Model):
    """用户分组 — isp_groups。

    替代旧 Group 模型（Django 内置 Group 名称冲突已规避）。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, unique=True, verbose_name="分组名称")
    description = models.TextField(max_length=512, blank=True, default="", verbose_name="描述")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name="owned_isp_groups", verbose_name="创建者")
    member_count = models.PositiveIntegerField(default=0, verbose_name="成员数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "isp_groups"
        verbose_name = "用户分组"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class IspGroupMember(models.Model):
    """分组成员 — isp_group_members。

    替代旧 GroupMember。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(IspGroup, on_delete=models.CASCADE,
                              related_name="memberships", verbose_name="分组")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="group_assignments", verbose_name="用户")
    is_admin = models.BooleanField(default=False, verbose_name="管理员")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="加入时间")

    class Meta:
        db_table = "isp_group_members"
        verbose_name = "分组成员"
        verbose_name_plural = verbose_name
        unique_together = ("group", "user")

    def __str__(self):
        return f"{self.group.name} → {self.user.username}"


# ================================================================
# 8.1.8 文档版本历史
# ================================================================

class IspDocumentVersion(models.Model):
    """文档版本历史 — isp_document_versions。

    替代旧 DocHistory，每次文档保存时生成快照。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(IspDocument, on_delete=models.CASCADE,
                                  related_name="versions", verbose_name="所属文档")
    version_number = models.PositiveIntegerField(default=1, verbose_name="版本号")
    markdown_content = models.TextField(null=True, blank=True, verbose_name="Markdown 内容快照")
    html_content = models.TextField(null=True, blank=True, verbose_name="HTML 内容快照")
    change_summary = models.CharField(max_length=256, blank=True, default="", verbose_name="变更摘要")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="document_versions",
                                    verbose_name="编辑人")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "isp_document_versions"
        verbose_name = "文档版本历史"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["document", "-version_number"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-version_number"]

    def __str__(self):
        return f"{self.document.title} v{self.version_number}"


# ================================================================
# 8.1.9 内容模板
# ================================================================

class IspContentTemplate(models.Model):
    """内容模板 — isp_content_templates。

    替代旧 DocTemp，支持分类和可见范围。
    """

    class Visibility(models.TextChoices):
        PRIVATE = "private", "仅自己"
        SHARED = "shared", "团队共享"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=128, verbose_name="模板标题")
    body = models.TextField(verbose_name="模板正文")
    category = models.CharField(max_length=64, blank=True, default="", verbose_name="分类")
    visibility = models.CharField(max_length=16, choices=Visibility.choices,
                                   default=Visibility.PRIVATE, verbose_name="可见范围")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="content_templates", verbose_name="创建者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "isp_content_templates"
        verbose_name = "内容模板"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["created_by", "category"]),
            models.Index(fields=["visibility"]),
        ]

    def __str__(self):
        return self.title


# ================================================================
# 8.1.10 分享链接
# ================================================================

class IspShareLink(models.Model):
    """分享链接 — isp_share_links。

    替代旧 DocShare，支持有效期和访问次数限制。
    """

    class AccessLevel(models.TextChoices):
        PUBLIC = "public", "公开访问"
        CODE_REQUIRED = "code", "口令访问"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=128, unique=True, verbose_name="分享令牌")
    document = models.ForeignKey(IspDocument, on_delete=models.CASCADE,
                                  related_name="share_links", verbose_name="所属文档")
    access_level = models.CharField(max_length=16, choices=AccessLevel.choices,
                                     default=AccessLevel.PUBLIC, verbose_name="访问模式")
    access_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="访问口令")
    is_active = models.BooleanField(default=True, verbose_name="启用")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="过期时间")
    view_count = models.PositiveIntegerField(default=0, verbose_name="浏览次数")
    max_views = models.PositiveIntegerField(null=True, blank=True, verbose_name="最大浏览数")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="share_links", verbose_name="创建者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "isp_share_links"
        verbose_name = "分享链接"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["document", "is_active"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.document.title} — {self.token[:8]}"


# ================================================================
# 8.1.11 内容标签
# ================================================================

class IspContentTag(models.Model):
    """内容标签 — isp_content_tags。

    替代旧 Tag，支持颜色标记和使用计数。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=32, unique=True, verbose_name="标签名")
    color = models.CharField(max_length=7, blank=True, default="", verbose_name="标签颜色")
    usage_count = models.PositiveIntegerField(default=0, verbose_name="引用次数")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="content_tags", verbose_name="创建者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "isp_content_tags"
        verbose_name = "内容标签"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class IspDocumentTagRef(models.Model):
    """文档-标签关联 — isp_document_tags。

    替代旧 DocTag。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(IspDocument, on_delete=models.CASCADE,
                                  related_name="tag_refs", verbose_name="文档")
    tag = models.ForeignKey(IspContentTag, on_delete=models.CASCADE,
                            related_name="document_refs", verbose_name="标签")
    tagged_at = models.DateTimeField(auto_now_add=True, verbose_name="标记时间")

    class Meta:
        db_table = "isp_document_tags"
        verbose_name = "文档-标签关联"
        verbose_name_plural = verbose_name
        unique_together = ("document", "tag")
        indexes = [
            models.Index(fields=["tag"]),
            models.Index(fields=["document"]),
        ]

    def __str__(self):
        return f"{self.tag.name} → {self.document.title}"


# ================================================================
# 8.1.12 用户收藏
# ================================================================

class IspUserBookmark(models.Model):
    """用户收藏 — isp_user_bookmarks。

    替代旧 MyCollect，通过 Generic FK 支持多种收藏对象。
    """

    class BookmarkType(models.TextChoices):
        DOCUMENT = "doc", "文档"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="bookmarks", verbose_name="用户")
    bookmark_type = models.CharField(max_length=16, choices=BookmarkType.choices,
                                      verbose_name="收藏类型")
    target_id = models.CharField(max_length=64, verbose_name="收藏目标 ID")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收藏时间")

    class Meta:
        db_table = "isp_user_bookmarks"
        verbose_name = "用户收藏"
        verbose_name_plural = verbose_name
        unique_together = ("user", "bookmark_type", "target_id")
        indexes = [
            models.Index(fields=["user", "bookmark_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} bookmarked {self.bookmark_type}:{self.target_id}"


# ================================================================
# 8.1.13 文档点赞
# ================================================================

class IspDocumentLike(models.Model):
    """文档点赞 — isp_document_likes。

    替代旧 DocLike。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(IspDocument, on_delete=models.CASCADE,
                                  related_name="likes", verbose_name="文档")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="document_likes", verbose_name="用户")
    liked_at = models.DateTimeField(auto_now_add=True, verbose_name="点赞时间")

    class Meta:
        db_table = "isp_document_likes"
        verbose_name = "文档点赞"
        verbose_name_plural = verbose_name
        unique_together = ("document", "user")

    def __str__(self):
        return f"{self.user.username} likes {self.document.title}"


# ================================================================
# 8.1.14 浏览记录
# ================================================================

class IspBrowseRecord(models.Model):
    """浏览记录 — isp_browse_records。

    替代旧 BrowseHistory，支持多种内容类型。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="browse_records", verbose_name="用户")
    target_type = models.CharField(max_length=16, choices=[("doc", "文档")],
                                    verbose_name="内容类型")
    target_id = models.CharField(max_length=64, verbose_name="内容 ID")
    context_id = models.CharField(max_length=64, null=True, blank=True,
                                   default="", verbose_name="上下文 ID")
    viewed_at = models.DateTimeField(auto_now=True, verbose_name="浏览时间")

    class Meta:
        db_table = "isp_browse_records"
        verbose_name = "浏览记录"
        verbose_name_plural = verbose_name
        ordering = ["-viewed_at"]
        indexes = [
            models.Index(fields=["user", "-viewed_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self):
        return f"{self.user.username} viewed {self.target_type}:{self.target_id}"
