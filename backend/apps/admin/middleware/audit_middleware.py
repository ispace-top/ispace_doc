"""
v1.0 审计日志中间件

记录文档 CUD 操作、权限变更、角色变更到 AuditLog 表。
"""

import json

from django.utils.deprecation import MiddlewareMixin
from backend.apps.admin.models import AuditLog


class AuditLogMiddleware(MiddlewareMixin):
    """捕获标记的请求并写入审计日志。

    视图通过 request._audit_log 字典标记需要记录的操作：
        request._audit_log = {
            'action': 'delete',
            'target_type': 'doc',
            'target_id': 123,
            'detail': '删除文档《xxx》',
        }
    """

    def process_response(self, request, response):
        audit_data = getattr(request, '_audit_log', None)
        if audit_data and request.user and request.user.is_authenticated:
            AuditLog.objects.create(
                user=request.user,
                action=audit_data.get('action', ''),
                target_type=audit_data.get('target_type', ''),
                target_id=audit_data.get('target_id'),
                detail=audit_data.get('detail', ''),
                ip_address=AuditLogMiddleware._get_ip(request),
            )
        return response

    @staticmethod
    def _get_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
