from django.urls import path,re_path,include
from django.views.generic import RedirectView
from backend.apps.doc import views,views_user,views_search,util_upload_img,views_import,views_group,views_org,views_permission,views_notification
from backend.apps.doc.storage import views as storage_views

urlpatterns = [
    path('',views.doc_home,name='pro_list'),# 文档首页（name 保留兼容）
    #################文档相关
    path('pages/<int:doc_id>/', views.doc_id, name='doc_by_id'),  # 文档浏览页（新版规范 URL）
    path('pages/<int:pro_id>/<int:doc_id>/', views.doc, name='doc'),  # 文档浏览页（旧版兼容，pro_id 忽略）
    path('pages/<int:pro_id>/<int:doc_id>/comments/', views.document_comments_handler, name='doc_comments'),  # 获取/发表评论（旧版兼容）
    path('pages/<int:doc_id>/comments/', views.document_comments_handler, name='doc_comments_v2'),  # 获取/发表评论（新版）
    path('pages/<int:pro_id>/<int:doc_id>/inline-comments/', views.inline_comments, name='inline_comments'),  # 划词评论（旧版兼容）
    path('pages/<int:doc_id>/inline-comments/', views.inline_comments, name='inline_comments_v2'),  # 划词评论（新版）
    path('comments/inline/<int:comment_id>/delete/', views.delete_inline_comment, name='delete_inline_comment'),  # 删除划词评论
    #################文档相关
    path('documents/<int:doc_id>/', views.doc_id, name="doc_id"),  # 文档浏览页(通过文档ID)
    path('documents/create/', views.create_new_document, name="create_doc"),  # 新建文档
    path('documents/<int:doc_id>/edit/', views.edit_existing_document, name="modify_doc"),  # 修改文档
    path('documents/delete/',views.remove_document,name="del_doc"), # 删除文档
    path('documents/<int:doc_id>/children/', views.get_document_children_count, name='check_doc_children'),  # 检查下级文档
    path('documents/restore/', views.restore_deleted_document, name='restore_doc'),  # 恢复文档
    path('delete-verify/image/', views.graphic_verify_code, name='delete_code_img'),  # 删除验证码图片
    path('delete-verify/check/', views.verify_delete_code, name='delete_code_verify'),  # 校验删除验证码
    path('documents/manage/',views.manage_doc,name="manage_doc"), # 管理文档
    path('documents/<int:doc_id>/diff/<int:his_id>/',views.compare_document_history,name='diff_doc'), # 对比文档历史版本
    path('documents/<int:doc_id>/history/',views.manage_doc_history,name='manage_doc_history'), # 管理文档历史版本
    path('documents/move/', views.relocate_document, name='move_doc'), # 移动文档
    path('documents/recycle/', views.doc_recycle,name='doc_recycle'), # 文档回收站
    path('documents/quick-publish/',views.quick_publish_document,name='fast_pub_doc'), # 一键发布文档
    path('documents/<int:doc_id>/export/md/',views.download_markdown_export,name='download_doc_md'), # 下载文档Markdown文件
    path('documents/<int:doc_id>/export/pdf/',views.download_pdf_export,name='download_doc_pdf'), # 下载文档PDF文件
    path('documents/<int:doc_id>/export/html/',views.download_html_export,name='download_doc_html'), # 下载文档HTML文件
    path('import/docx/',views_import.import_doc_docx,name="import_doc_docx"), # 导入docx文档
    #################文档分享相关
    path('shared-links/create/', views.share_document, name='share_doc'),  # 私密文档分享
    path('shared-links/verify/', views.share_doc_check, name='share_doc_check'),  # 私密文档验证
    path('shared-links/manage/',views.manage_doc_share,name="manage_doc_share"), # 分享文档管理
    #################文档模板相关
    path('content-templates/manage/',views.manage_doctemp,name='manage_doctemp'), # 文档模板列表
    path('content-templates/create/',views.create_content_template,name="create_doctemp"), # 创建文档模板
    path('content-templates/get/',views.fetch_content_template,name='get_doctemp'), # 获取某一个文档模板内容
    path('content-templates/delete/',views.delete_content_template,name="del_doctemp"), # 删除某一个文档模板
    path('content-templates/edit/',views.edit_content_template,name="modify_doctemp"), # 修改文档模板
    #################文件管理相关
    path('files/images/',views.manage_image,name="manage_image"), # 图片管理
    path('files/image-groups/',views.manage_img_group,name="manage_img_group"), # 图片分组管理
    path('files/attachments/',views.manage_attachment,name='manage_attachment'), # 附件管理
    ##############文档标签
    path('content-tags/manage/',views.manage_doc_tag,name="manage_doc_tag"), # 文档标签管理
    path('content-tags/<int:tag_id>/documents/',views.tag_docs,name="tag_docs"), # 标签文档页
    path('content-tags/<int:tag_id>/documents/<int:doc_id>/',views.tag_doc,name="tag_doc"), # 标签文档页
    ################其他功能相关
    path('my/',views_user.user_center,name="user_center"), # 个人中心
    path('my/groups/',views_user.group_list_page,name="group_list_page"), # 分组列表页
    path('my/organization/',views_user.org_tree_page,name="org_tree_page"), # 组织架构树页
    path('my/sidebar-menu/',views_user.user_center_menu,name="user_center_menu"), # 个人中心菜单数据
    path('api/users/search/', views_user.api_user_search, name='api_user_search'),  # 用户搜索
    path('api/users/<int:user_id>/profile/', views_user.api_user_profile, name='api_user_profile'),  # 用户信息浮窗
    path('api/user/profile/edit/', views_user.api_user_profile_edit, name='api_user_profile_edit'),  # 编辑个人资料
    path('api/user/avatar/upload/', views_user.api_avatar_upload, name='api_avatar_upload'),  # 头像上传
    path('api/user/change-password/', views_user.api_change_password, name='api_change_password'),  # 修改密码
    path('api/user/login-records/', views_user.api_login_records, name='api_login_records'),  # 登录记录
    path('api/user/my-groups/', views_user.api_my_groups, name='api_my_groups'),  # 我的分组
    path('api/user/my-drafts/', views_user.api_my_drafts, name='api_my_drafts'),  # 我的草稿
    path('api/user/my-orgs/', views_user.api_my_orgs, name='api_my_orgs'),  # 我的组织
    path('api/user/notify-settings/', views_user.api_notify_settings, name='api_notify_settings'),  # 获取通知设置
    path('api/user/notify-settings/save/', views_user.api_notify_settings_save, name='api_notify_settings_save'),  # 保存通知设置
    path('api/user/browse-history/', views_user.api_browse_history, name='api_browse_history'),  # 浏览记录
    path('api/user/doctemp-list/', views_user.api_user_doctemp_list, name='api_user_doctemp_list'),  # 文档模板列表
    path('api/user/doctemp-delete/', views_user.api_user_doctemp_delete, name='api_user_doctemp_delete'),  # 删除文档模板
    path('api/user/token-info/', views_user.api_user_token_info, name='api_user_token_info'),  # Token信息
    path('files/upload/image/',util_upload_img.upload_img,name="upload_doc_img"), # 上传图片
    path('files/upload/ice-image/',util_upload_img.upload_ice_img,name="upload_ice_img"), # iceeditor上传图片
    path('search/',views.search,name="search"), # 搜索功能
    # path('doc_search/', include('haystack.urls')),  # 全文检索框架
    path('search/query/', views_search.DocSearchView(),name="doc_search"),  # 全文检索框架
    path('my/overview/',views.manage_overview,name="manage_overview"), # 个人中心概览
    path('my/settings/',views.manage_self,name="manage_self"), # 个人设置
    path('my/bookmarks/toggle/',views.toggle_favorite,name="my_collect"), # 我的收藏
    path('my/bookmarks/manage/',views.manage_favorites,name="manage_collect"), # 收藏管理
    path('system/version/',views.get_version,name="get_version"), # 获取当前版本
    path('api/usergroups/userlist', views.UserGroupUserList.as_view(), name="api_usergroups_userlist"),  # 用户分组的用户列表接口
    #################分组管理API
    path('api/groups/', views_group.api_group_create, name='api_group_create'),  # 创建分组
    path('api/groups/list/', views_group.api_group_list, name='api_group_list'),  # 我的分组列表
    path('api/groups/<int:group_id>/', views_group.api_group_update, name='api_group_update'),  # 修改分组
    path('api/groups/<int:group_id>/delete/', views_group.api_group_delete, name='api_group_delete'),  # 删除分组
    path('api/groups/<int:group_id>/members/', views_group.api_group_members, name='api_group_members'),  # 成员列表
    path('api/groups/<int:group_id>/members/add/', views_group.api_group_add_members, name='api_group_add_members'),  # 添加成员
    path('api/groups/<int:group_id>/members/remove/', views_group.api_group_remove_member, name='api_group_remove_member'),  # 移除成员
    path('api/groups/<int:group_id>/transfer/', views_group.api_group_transfer_owner, name='api_group_transfer_owner'),  # 转让管理员
    path('api/groups/<int:group_id>/leave/', views_group.api_group_leave, name='api_group_leave'),  # 退出分组
    path('api/groups/search/', views_group.api_group_search, name='api_group_search'),  # 搜索分组
    path('api/groups/<int:group_id>/members/ids/', views_group.api_group_members_list, name='api_group_member_ids'),  # 分组成员ID列表
    path('api/groups/<int:group_id>/members/set-admin/', views_group.api_group_set_admin, name='api_group_set_admin'),  # 设置/取消管理员
    #################组织架构API
    path('api/org/tree/', views_org.api_org_tree, name='api_org_tree'),  # 组织树
    path('api/org/nodes/search/', views_org.api_org_search, name='api_org_search'),  # 搜索组织节点
    path('api/org/nodes/<int:node_id>/members/ids/', views_org.api_org_members_list, name='api_org_member_ids'),  # 组织成员ID列表
    path('api/org/nodes/create/', views_org.api_org_node_create, name='api_org_node_create'),  # 创建节点
    path('api/org/nodes/<int:node_id>/', views_org.api_org_node_detail, name='api_org_node_detail'),  # 节点详情
    path('api/org/nodes/<int:node_id>/rename/', views_org.api_org_node_rename, name='api_org_node_rename'),  # 重命名
    path('api/org/nodes/<int:node_id>/delete/', views_org.api_org_node_delete, name='api_org_node_delete'),  # 删除节点
    path('api/org/nodes/<int:node_id>/members/add/', views_org.api_org_add_members, name='api_org_add_members'),  # 添加成员
    path('api/org/nodes/<int:node_id>/members/remove/', views_org.api_org_remove_member, name='api_org_remove_member'),  # 移除成员
    path('api/org/nodes/<int:node_id>/members/primary/', views_org.api_org_set_primary, name='api_org_set_primary'),  # 设置主属部门
    path('api/org/nodes/<int:node_id>/admin/appoint/', views_org.api_org_appoint_admin, name='api_org_appoint_admin'),  # 任命管理员
    path('api/org/nodes/<int:node_id>/admin/revoke/', views_org.api_org_revoke_admin, name='api_org_revoke_admin'),  # 撤销管理员
    #################文档权限API
    path('api/docs/<int:doc_id>/permissions/', views_permission.api_doc_permissions, name='api_doc_permissions'),  # 权限列表
    path('api/docs/<int:doc_id>/permissions/grant/', views_permission.api_doc_permission_grant, name='api_doc_permission_grant'),  # 授权
    path('api/docs/<int:doc_id>/permissions/revoke/', views_permission.api_doc_permission_revoke, name='api_doc_permission_revoke'),  # 撤销
    path('api/docs/<int:doc_id>/permissions/batch/', views_permission.api_doc_permission_batch, name='api_doc_permission_batch'),  # 批量授权
    path('api/docs/<int:doc_id>/permissions/apply/', views_permission.api_doc_permission_apply, name='api_doc_permission_apply'),  # 申请权限
    path('api/docs/<int:doc_id>/permissions/mine/', views_permission.api_doc_my_permission, name='api_doc_my_permission'),  # 我的权限
    path('api/docs/permissions/summary/', views_permission.api_doc_permissions_summary, name='api_doc_permissions_summary'),  # 批量权限摘要
    path('api/docs/<int:doc_id>/move/', views.api_doc_move, name='api_doc_move'),  # 拖拽移动/排序
    path('api/docs/<int:doc_id>/access/', views_permission.api_doc_access_mode, name='api_doc_access_mode'),  # 文档访问模式
    #################通知API
    path('api/notifications/', views_notification.api_notification_list, name='api_notification_list'),  # 通知列表
    path('api/notifications/read/', views_notification.api_notification_mark_read, name='api_notification_mark_read'),  # 标记已读
    path('api/notifications/unread-count/', views_notification.api_notification_unread_count, name='api_notification_unread_count'),  # 未读数
    path('api/notifications/clear-all/', views_notification.api_notification_clear_all, name='api_notification_clear_all'),  # 清空全部通知
    path('notifications/', views_notification.notification_page, name='notification_page'),  # 通知列表页
    #################文档评论
    path('comments/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),  # 删除评论
    path('documents/<int:doc_id>/like/', views.toggle_document_like, name='doc_like_toggle'),  # 文档点赞
    #################WebHook
    path('api/webhook/', include('backend.apps.doc.webhook.urls')),  # WebHook 管理 API
    #################图标
    path('api/icons/', include('backend.apps.doc.icon.urls')),  # 图标搜索 API
    #################搜索 API（v2.0）
    path('api/search/', include('backend.apps.doc.search.urls')),  # 全文搜索 API
    #################附件预览
    path('api/preview/', include('backend.apps.doc.preview.urls')),  # 附件预览 API
    #################分片上传
    path('api/upload/chunked/', include('backend.apps.doc.chunked_upload.urls')),  # 分片上传 API
    #################可视化绘图
    path('api/drawing/', include('backend.apps.doc.drawing.urls')),  # 绘图 API（思维导图/Draw.io/Excalidraw）
    #################目录同步
    path('api/sync/', include('backend.apps.doc.sync.urls')),  # 通讯录同步 API
    #################存储增强（1.3.2 / 1.4.2 / 1.7.2）
    path('api/storage/presigned-upload/', storage_views.presigned_upload_url, name='storage_presigned_upload'),
    path('api/storage/upload-progress/<str:upload_id>/', storage_views.upload_progress_stream, name='storage_upload_progress'),
    path('api/storage/process-image/', storage_views.process_image_url, name='storage_process_image'),
    #################v2.0 REST API（必须在具体路由之后）
    path('api/', include('backend.apps.doc.api_v2.router')),  # v2.0 统一 REST API
    #################向后兼容重定向（旧版 /docs/ → 新版 /pages/）
    re_path(r'^docs/(?P<pro_id>\d+)/(?P<doc_id>\d+)/comments/$', RedirectView.as_view(pattern_name='doc_comments', permanent=True)),
    re_path(r'^docs/(?P<doc_id>\d+)/comments/$', RedirectView.as_view(pattern_name='doc_comments_v2', permanent=True)),
    re_path(r'^docs/(?P<pro_id>\d+)/(?P<doc_id>\d+)/inline-comments/$', RedirectView.as_view(pattern_name='inline_comments', permanent=True)),
    re_path(r'^docs/(?P<doc_id>\d+)/inline-comments/$', RedirectView.as_view(pattern_name='inline_comments_v2', permanent=True)),
    re_path(r'^docs/(?P<pro_id>\d+)/(?P<doc_id>\d+)/$', RedirectView.as_view(pattern_name='doc', permanent=True)),
    re_path(r'^docs/(?P<doc_id>\d+)/$', RedirectView.as_view(pattern_name='doc_by_id', permanent=True)),
]