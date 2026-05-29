from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


# 文档条目模型
class Doc(models.Model):
    name = models.CharField(verbose_name="标题",max_length=255)
    pre_content = models.TextField(verbose_name="Markdown 源码",null=True,blank=True)
    content = models.TextField(verbose_name="HTML 渲染内容",null=True,blank=True)
    parent_doc = models.IntegerField(default=0,verbose_name="父文档 ID")
    top_doc = models.IntegerField(default=0,verbose_name="根文档 ID")
    sort = models.IntegerField(verbose_name='同级排序权重',default=9999)
    create_user = models.ForeignKey(User,on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)
    status = models.IntegerField(choices=((0,0),(1,1)),default=1,verbose_name='发布状态')
    editor_mode = models.IntegerField(default=0,verbose_name='编辑器类型')  # 0=Markdown(Vditor) 1=电子表格(Luckysheet)
    open_children = models.BooleanField(default=False,verbose_name="侧栏默认展开")
    show_children = models.BooleanField(verbose_name="显示所有后代",default=False)
    # v1.0 软删除字段
    is_deleted = models.BooleanField(default=False, verbose_name="是否已删除")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="删除时间")
    deleted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='deleted_docs', verbose_name="删除人")
    # v1.0 大纲 JSON（服务端预生成，前端直接渲染）
    outline = models.TextField(null=True, blank=True, verbose_name='大纲 JSON')
    # v2.0 结构化绘图数据（思维导图 / Draw.io / Excalidraw）
    content_json = models.JSONField(null=True, blank=True, default=dict, verbose_name="结构化绘图数据")
    # 替代原 Project.role == 0 的公开访问开关
    is_public = models.BooleanField(default=True, verbose_name="允许公开访问")
    # is_public=True 且密码非空 → 密码访问模式
    access_password = models.CharField(max_length=128, blank=True, default="", verbose_name="公开访问密码")
    # 文档水印（从 Project 下放到 Doc）
    is_watermark = models.BooleanField(verbose_name="启用水印", default=False)
    watermark_type = models.IntegerField(verbose_name="水印样式", default=1)
    watermark_value = models.CharField(verbose_name="水印文字", null=True, blank=True, default='', max_length=250)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '文档条目'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['parent_doc','status']),
            models.Index(fields=['sort']),
            models.Index(fields=['is_deleted', 'deleted_at']),
            models.Index(fields=['is_public']),
        ]
        # ordering = ['-create_time','sort']

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("doc_by_id",
                       kwargs={
                           "doc_id":self.pk}
                       )


# 文档版本历史
class DocHistory(models.Model):
    doc = models.ForeignKey(Doc,on_delete=models.CASCADE)
    pre_content = models.TextField(verbose_name='历史版本 Markdown 源码',null=True,blank=True)
    create_user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    create_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.doc

    class Meta:
        verbose_name = '文档版本历史'
        verbose_name_plural = verbose_name


# 文档点赞模型
class DocLike(models.Model):
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('doc', 'user')
        verbose_name = '文档点赞'
        verbose_name_plural = verbose_name


# 内容模板
class DocTemp(models.Model):
    name = models.CharField(verbose_name="模板标题",max_length=50)
    content = models.TextField(verbose_name="模板正文")
    create_user = models.ForeignKey(User,on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '内容模板'
        verbose_name_plural = verbose_name

# 文档分享
class DocShare(models.Model):
    token = models.CharField(verbose_name="分享令牌",max_length=100,blank=True,null=True)
    doc = models.ForeignKey(Doc,on_delete=models.CASCADE)
    share_type = models.IntegerField(choices=((0,0),(1,1)),default=0)
    share_value = models.CharField(max_length=10,verbose_name="访问口令",blank=True,null=True)
    is_enable = models.BooleanField(default=True,verbose_name="是否启用")
    create_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.doc.name

    class Meta:
        verbose_name = '分享链接'
        verbose_name_plural = verbose_name

# 标签
class Tag(models.Model):
    name = models.CharField(verbose_name='标签名称',max_length=10)
    create_user = models.ForeignKey(User,on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '内容标签'
        verbose_name_plural = verbose_name


# 文档-标签关联
class DocTag(models.Model):
    tag = models.ForeignKey(Tag,on_delete=models.CASCADE)
    doc = models.ForeignKey(Doc,on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "{}-{}".format(self.tag.name,self.doc.name)

    class Meta:
        verbose_name = '文档-标签关联'
        verbose_name_plural = verbose_name


# 图片分组目录
class ImageGroup(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    group_name = models.CharField(verbose_name="分组名",max_length=50,default="默认分组")

    def __str__(self):
        return self.group_name

    class Meta:
        verbose_name = '图片分组目录'
        verbose_name_plural = verbose_name


# 图片素材
class Image(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    file_path = models.CharField(verbose_name="存储路径",max_length=250)
    file_name = models.CharField(verbose_name="文件名",max_length=250,null=True,blank=True)
    group = models.ForeignKey(ImageGroup,on_delete=models.SET_NULL,null=True,verbose_name="所属分组")
    remark = models.CharField(verbose_name="备注描述",null=True,blank=True,max_length=250,default="图片描述")
    create_time = models.DateTimeField(verbose_name='上传时间',auto_now_add=True)
    modify_time = models.DateTimeField(verbose_name='最后修改',auto_now=True)

    class Meta:
        verbose_name = '图片素材'
        verbose_name_plural = verbose_name


# 文件附件
class Attachment(models.Model):
    file_name = models.CharField(max_length=200,verbose_name="文件名",default='untitled_attachment.zip')
    file_size = models.CharField(max_length=100,verbose_name="文件体积",blank=True,null=True)
    file_path = models.FileField(upload_to='attachment/%Y/%m/',verbose_name='存储路径')
    user = models.ForeignKey(User,on_delete=models.CASCADE,)
    create_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name

    class Meta:
        verbose_name = '文件附件'
        verbose_name_plural = verbose_name


# 用户收藏
class MyCollect(models.Model):
    collect_type = models.IntegerField(verbose_name="收藏对象类别")
    collect_id = models.IntegerField(verbose_name="收藏目标 ID")
    create_user = models.ForeignKey(User,on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.collect_type

    class Meta:
        verbose_name = '用户收藏'


# 文档讨论
class DocComment(models.Model):
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE, verbose_name="所属文档")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="评论人")
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies', verbose_name="上级评论")
    content = models.TextField(verbose_name="正文")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="发表时间")
    modify_time = models.DateTimeField(auto_now=True, verbose_name="最后编辑时间")
    is_active = models.BooleanField(default=True, verbose_name="显示状态")
    reply_count = models.PositiveIntegerField(default=0, verbose_name="回复计数")
    mentioned_users = models.ManyToManyField(User, blank=True, related_name='mentioned_in_comments', verbose_name="提及的用户列表")

    def __str__(self):
        return '{}: {}'.format(self.user.username, self.content[:50])

    class Meta:
        verbose_name = '文档讨论'
        verbose_name_plural = verbose_name
        ordering = ['create_time']


# ========== v1.0 新增模型 ==========

# 用户档案（扩展 Django 内置 User）
class UserProfile(models.Model):
    GENDER_CHOICES = (('M', '男'), ('F', '女'), ('U', '未知'))
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', verbose_name="头像", null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U', verbose_name="性别")
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="手机号")
    bio = models.TextField(max_length=512, blank=True, default='', verbose_name="个性说明")
    last_active = models.DateTimeField(null=True, blank=True, verbose_name="最后活跃时间")
    notify_settings = models.TextField(blank=True, default='{}', verbose_name="通知设置JSON")
    # v2.0 第三方平台绑定标识
    wecom_userid = models.CharField(max_length=128, blank=True, default='', verbose_name="企业微信 UserID", db_index=True)
    dingtalk_userid = models.CharField(max_length=128, blank=True, default='', verbose_name="钉钉 UserID", db_index=True)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = '用户档案'
        verbose_name_plural = verbose_name


# 分组
class Group(models.Model):
    name = models.CharField(max_length=64, unique=True, verbose_name="分组名称")
    description = models.TextField(max_length=256, blank=True, default='', verbose_name="描述")
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='owned_groups', verbose_name="创建者/管理员")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    member_count = models.PositiveIntegerField(default=0, verbose_name="成员数量")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '分组'
        verbose_name_plural = verbose_name


# 分组-用户关联
class GroupMember(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    is_admin = models.BooleanField(default=False, verbose_name="是否为管理员")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="加入时间")

    def __str__(self):
        return f'{self.group.name} - {self.user.username}'

    class Meta:
        verbose_name = '分组成员'
        verbose_name_plural = verbose_name
        unique_together = ('group', 'user')


# 组织架构节点
class OrgNode(models.Model):
    name = models.CharField(max_length=64, verbose_name="节点名称")
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children', verbose_name="父节点")
    path = models.CharField(max_length=256, blank=True, default='', verbose_name="物化路径")
    depth = models.PositiveSmallIntegerField(default=0, verbose_name="深度")
    sort_order = models.IntegerField(default=0, verbose_name="同级排序")
    admin = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='managed_org_nodes', verbose_name="部门管理员")
    # v2.0 外部同步来源标识
    external_source = models.CharField(max_length=32, blank=True, default='', verbose_name="外部来源", db_index=True)
    external_id = models.CharField(max_length=128, blank=True, default='', verbose_name="外部 ID")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '组织节点'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=['parent', 'name'], name='unique_sibling_name')
        ]


# 组织-用户关联
class OrgUser(models.Model):
    org_node = models.ForeignKey(OrgNode, on_delete=models.CASCADE, related_name='org_users')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='org_memberships')
    is_primary = models.BooleanField(default=False, verbose_name="是否主属部门")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="加入时间")

    def __str__(self):
        return f'{self.org_node.name} - {self.user.username}'

    class Meta:
        verbose_name = '组织成员'
        verbose_name_plural = verbose_name
        unique_together = ('org_node', 'user')


# 文档权限
class DocPermission(models.Model):
    PERM_CHOICES = (('view', '可见'), ('edit', '可编辑'), ('admin', '管理员'))
    TARGET_TYPE_CHOICES = (('user', '用户'), ('group', '分组'), ('org', '组织节点'))

    doc = models.ForeignKey(Doc, on_delete=models.CASCADE, related_name='permissions', verbose_name="文档")
    target_type = models.CharField(max_length=10, choices=TARGET_TYPE_CHOICES, verbose_name="授权对象类型")
    target_id = models.PositiveIntegerField(verbose_name="授权对象 ID")
    permission = models.CharField(max_length=10, choices=PERM_CHOICES, verbose_name="权限级别")
    apply_to_children = models.BooleanField(default=False, verbose_name="同步所有子节点")
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='granted_permissions', verbose_name="授权人")
    granted_at = models.DateTimeField(auto_now_add=True, verbose_name="授权时间")

    def __str__(self):
        return f'DocPermission({self.doc_id}): {self.target_type}:{self.target_id} -> {self.permission}'

    class Meta:
        verbose_name = '文档权限'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['doc', 'target_type', 'target_id']),
            models.Index(fields=['target_type', 'target_id']),
        ]


# 通知
class Notification(models.Model):
    TYPE_CHOICES = (
        ('system', '系统通知'),
        ('comment', '文档评论'),
        ('reply', '评论回复'),
        ('mention', '@提及'),
        ('doc_change', '文档变更'),
        ('doc_like', '文档点赞'),
        ('perm_apply', '权限申请'),
        ('perm_change', '权限变更'),
    )

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="接收者")
    sender = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='sent_notifications', verbose_name="发送者")
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="通知类型")
    title = models.CharField(max_length=128, verbose_name="通知标题")
    body = models.TextField(blank=True, default='', verbose_name="通知内容")
    link = models.URLField(max_length=500, blank=True, default='', verbose_name="关联链接")
    is_read = models.BooleanField(default=False, verbose_name="是否已读")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]


# 划词评论
class InlineComment(models.Model):
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE, related_name='inline_comments', verbose_name="所属文档")
    anchor_start = models.PositiveIntegerField(verbose_name="起始字符偏移")
    anchor_end = models.PositiveIntegerField(verbose_name="结束字符偏移")
    anchor_hash = models.CharField(max_length=32, verbose_name="选中文本 MD5")
    selected_text = models.CharField(max_length=500, verbose_name="选中文本原文")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inline_comments', verbose_name="评论者")
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies', verbose_name="父评论")
    content = models.TextField(blank=True, default='', verbose_name="评论内容")
    is_active = models.BooleanField(default=True, verbose_name="是否有效")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return f'InlineComment({self.doc_id}): {self.selected_text[:30]}'

    class Meta:
        verbose_name = '划词评论'
        verbose_name_plural = verbose_name
        ordering = ['anchor_start']


class BrowseHistory(models.Model):
    """浏览记录持久化存储"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    content_type = models.CharField(max_length=10, choices=[('doc', '文档')], verbose_name='内容类型')
    content_id = models.IntegerField(verbose_name='内容ID')
    extra_id = models.IntegerField(null=True, blank=True, verbose_name='额外ID')  # doc 对应的 top_doc
    viewed_at = models.DateTimeField(auto_now=True, verbose_name='浏览时间')

    class Meta:
        verbose_name = '浏览记录'
        verbose_name_plural = verbose_name
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['user', '-viewed_at']),
        ]


# 导入 WebHook 模型（使其被 Django 迁移系统发现）
from backend.apps.doc.webhook.models import WebHookConfig, WebHookDelivery  # noqa: E402, F401
from backend.apps.doc.chunked_upload.models import ChunkedUpload  # noqa: E402, F401

# v2.0 全新数据模型（isp_ 前缀表）
from backend.apps.doc.models_v2 import (  # noqa: E402, F401
    IspDocument, IspAttachment, IspImage, IspImageGroup,
    IspDocPermission, IspComment, IspNotification,
    IspUserProfile, IspOAuthBinding,
    IspOrgNode, IspOrgUser, IspGroup, IspGroupMember,
)