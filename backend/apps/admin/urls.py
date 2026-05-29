from django.urls import path,re_path
from backend.apps.admin import views

urlpatterns = [
    path('users/',views.admin_user,name="user_manage"),  # 用户管理页面
    path('users/profile/',views.admin_user_profile, name="user_profile"), # 用户资料页面
    path('api/users', views.AdminUserList.as_view(), name="api_admin_users"),  # 用户列表接口
    path('api/user/<int:id>',views.AdminUserDetail.as_view(), name="api_admin_user"), # 用户接口

    path('password/change/',views.change_pwd,name="modify_pwd"),  # 普通用户修改密码

    path('documents/',views.admin_doc,name='doc_manage'), # 文档管理
    # 文档历史记录管理及接口
    path('documents/<int:id>/history/', views.admin_doc_history, name='doc_history_manage'),  # 文档历史记录管理
    path('api/doc_history/<int:id>/', views.AdminDocHistory.as_view(), name="api_doc_history"),  # 文档历史记录接口
    path('api/doc_history_detail/', views.AdminDocHistoryDetail.as_view(), name="api_doc_history_detail"),  # 文档历史记录详情接口
    path('templates/',views.admin_doctemp,name='doctemp_manage'), # 文档模板管理
    path('settings/',views.admin_setting,name="sys_setting"), # 应用设置
    path('settings/site/',views.admin_site_config,name="site_config"), # 站点配置
    path('password/forgot/',views.forget_pwd,name='forget_pwd'), # 忘记密码
    path('email/verify-code/',views.send_email_vcode,name='send_email_vcode'), # 忘记密码发送邮件验证码
    path('email/test/', views.send_email_test, name='send_email_test'),  # 发送测试邮件
    path('system/update/',views.check_update,name='check_update'), # 检测版本更新
    path('system/about/',views.admin_about,name='admin_about'), # 关于我们
    path('dashboard/',views.admin_center,name="admin_center"), # 后台管理
    path('dashboard/menu/',views.admin_center_menu,name="admin_center_menu"), # 后台管理菜单数据
    path('dashboard/overview/',views.admin_overview,name="admin_overview"), # 后台管理仪表盘
    # 注册邀请码及接口
    path('register-codes/', views.admin_register_code, name='register_code_manage'),  # 注册邀请码管理
    path('api/register_code/', views.AdminRegisterCodeApi.as_view(), name="api_admin_register_code"),  # 注册邀请码接口
    # 图片管理及接口
    path('files/images/', views.admin_image, name="image_manage"),  # 图片管理页面
    path('api/imgs/', views.AdminImageList.as_view(), name="api_admin_imgs"),  # 图片列表接口
    path('api/img/<int:id>/', views.AdminImageDetail.as_view(), name="api_admin_img"),  # 图片详情接口
    # 附件管理及接口
    path('files/attachments/', views.admin_attachment, name="attachment_manage"),  # 附件管理页面
    path('api/attachments/', views.AdminAttachmentList.as_view(), name="api_admin_attachments"),  # 附件列表接口
    path('api/attachment/<int:id>/', views.AdminAttachmentDetail.as_view(), name="api_admin_attachment"),  # 附件详情接口
    # 站点备份
    path('system/backup/',views.admin_backup,name="admin_backup"),
    # 站点数据管理
    path('system/cache/clear/', views.admin_clear_cache, name="admin_clear_cache"),  # 清除缓存
    path('system/index/rebuild/', views.admin_rebuild_index, name="admin_rebuild_index"),  # 重建索引
    path('system/logo/upload/', views.admin_upload_logo, name="admin_upload_logo"),  # Logo 上传
    # v1.0 管理后台新增页面
    path('groups/', views.admin_group, name='admin_group_manage'),  # 分组管理
    path('organization/', views.admin_org, name='admin_org_manage'),  # 组织架构管理
    path('documents/trash/', views.admin_doc_trash, name='admin_doc_trash'),  # 文档回收站
    path('audit-logs/', views.admin_audit_log, name='admin_audit_log'),  # 审计日志
    # v1.0 管理后台 API
    path('api/groups/manage/', views.api_admin_groups, name='api_admin_groups'),  # 分组管理API
    path('api/trash/manage/', views.api_admin_trash, name='api_admin_trash'),  # 回收站API
    path('api/org/manage/', views.api_admin_org_manage, name='api_admin_org_manage'),  # 组织管理API
    path('api/audit-logs/', views.api_admin_audit_logs, name='api_admin_audit_logs'),  # 审计日志API
    # v1.0 管理后台新增页面
    path('login-history/', views.admin_login_records, name='admin_login_records'),  # 登录记录
    path('comments/manage/', views.admin_comments, name='admin_comments'),  # 评论管理
    path('notifications/manage/', views.admin_notifications, name='admin_notifications'),  # 通知管理
    # v1.0 管理后台新增 API
    path('api/login-records/', views.api_admin_login_records, name='api_admin_login_records'),  # 登录记录API
    path('api/comments/', views.api_admin_comments, name='api_admin_comments'),  # 评论管理API
    path('api/notifications/', views.api_admin_notifications, name='api_admin_notifications'),  # 通知管理API
    path('system/health/', views.admin_health, name='admin_health'),  # 系统健康
    path('api/health/', views.api_admin_health, name='api_admin_health'),  # 系统健康API
    # v2.0 存储配置管理
    path('system/storage/', views.admin_storage, name='admin_storage'),
    path('api/infra/config/', views.api_admin_infra_config, name='api_admin_infra_config'),
    # v2.0 WebHook 管理
    path('system/webhooks/', views.admin_webhook, name='admin_webhook'),
    # v2.0 系统日志
    path('system/logs/', views.admin_syslog, name='admin_syslog'),
    path('api/syslog/', views.api_admin_syslog, name='api_admin_syslog'),
    # v2.0 数据库配置查看
    path('system/database/', views.admin_database, name='admin_database'),
    # v2.0 认证配置管理
    path('system/auth/', views.admin_auth, name='admin_auth'),
    path('api/auth/configs/', views.api_admin_auth_configs, name='api_admin_auth_configs'),
    re_path(r'^api/auth/test/(?P<provider>[\w]+)/$', views.api_admin_auth_test, name='api_admin_auth_test'),
    path('api/auth/bindings/', views.api_admin_auth_bindings, name='api_admin_auth_bindings'),
    re_path(r'^api/auth/bindings/(?P<bid>[\w\-]+)/$', views.api_admin_auth_unbind, name='api_admin_auth_unbind'),
    # v2.0 通知渠道管理
    path('system/notification-channels/', views.admin_notification_channels, name='admin_notification_channels'),
    path('api/notification/channels/', views.api_admin_notification_channels, name='api_admin_notification_channels'),
    re_path(r'^api/notification/channels/(?P<channel_id>[\w]+)/$', views.api_admin_notification_channel_action, name='api_admin_notification_channel_action'),
    path('api/notification/routes/', views.api_admin_notification_routes, name='api_admin_notification_routes'),
]