"""v2.0 REST API 统一路由（9.1.1）。

URL 设计遵循 RESTful 规范，/api/ 前缀，资源名复数。
"""
from django.urls import path, include

from . import views

urlpatterns = [
    # -- 文档 CRUD + 树 --
    path("documents/", views.doc_list, name="v2_doc_list"),
    path("documents/tree/", views.doc_tree, name="v2_doc_tree"),
    path("documents/create/", views.doc_create, name="v2_doc_create"),
    path("documents/<str:doc_id>/", views.doc_detail, name="v2_doc_detail"),
    path("documents/<str:doc_id>/update/", views.doc_update, name="v2_doc_update"),
    path("documents/<str:doc_id>/delete/", views.doc_delete, name="v2_doc_delete"),
    # -- 评论 --
    path("documents/<str:doc_id>/comments/", views.comment_list, name="v2_comment_list"),
    path("documents/<str:doc_id>/comments/create/", views.comment_create, name="v2_comment_create"),
    path("comments/<str:comment_id>/delete/", views.comment_delete, name="v2_comment_delete"),
    # -- 权限 --
    path("documents/<str:doc_id>/permissions/", views.permission_list, name="v2_perm_list"),
    path("documents/<str:doc_id>/permissions/grant/", views.permission_grant, name="v2_perm_grant"),
    path("documents/<str:doc_id>/permissions/<str:perm_id>/revoke/", views.permission_revoke, name="v2_perm_revoke"),
    path("documents/<str:doc_id>/permissions/batch/", views.permission_batch, name="v2_perm_batch"),
    # -- 通知 --
    path("notifications/", views.notification_list, name="v2_notification_list"),
    path("notifications/read/", views.notification_mark_read, name="v2_notification_read"),
    path("notifications/unread-count/", views.notification_unread_count, name="v2_notification_unread"),
    # -- 附件 --
    path("attachments/", views.attachment_list, name="v2_attachment_list"),
    path("documents/<str:doc_id>/attachments/", views.attachment_list, name="v2_doc_attachment_list"),
    # -- 组织架构 / 分组 --
    path("org/tree/", views.org_tree, name="v2_org_tree"),
    path("groups/", views.group_list, name="v2_group_list"),
]
