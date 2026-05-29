# coding:utf-8
"""通知系统 API"""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from backend.apps.doc.models import Notification
from backend.apps.doc.services import NotificationService
from backend.apps.doc.api_response import ApiResponse


@login_required
@require_GET
def notification_page(request):
    """通知列表页面。"""
    return render(request, 'app_doc/notification_page.html')


@login_required
@require_GET
def api_notification_list(request):
    """获取当前用户的通知列表。

    Query params:
        page: 页码 (default 1)
        page_size: 每页条数 (default 20)
        notification_type: 筛选类型 (system/comment/reply/mention/doc_change/doc_like/perm_apply)
        unread_only: 仅未读 (true/false)
    """
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    notification_type = request.GET.get('notification_type', '')
    unread_only = request.GET.get('unread_only', 'false').lower() == 'true'

    qs = Notification.objects.filter(recipient=request.user)
    if notification_type:
        types = [t.strip() for t in notification_type.split(',') if t.strip()]
        qs = qs.filter(notification_type__in=types)
    if unread_only:
        qs = qs.filter(is_read=False)

    # 未读优先排序
    qs = qs.order_by('is_read', '-created_at')

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    items = []
    for n in page_obj:
        avatar_data = _get_avatar_data(n.sender) if n.sender else {}
        items.append({
            'id': n.id,
            'notification_type': n.notification_type,
            'title': n.title,
            'body': n.body,
            'link': n.link,
            'is_read': n.is_read,
            'sender_id': n.sender_id if n.sender else None,
            'sender_name': n.sender.first_name or n.sender.username if n.sender else '',
            'sender_avatar_url': avatar_data.get('avatar_url', ''),
            'sender_initial': avatar_data.get('avatar_initial', ''),
            'sender_color': avatar_data.get('avatar_color', ''),
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
            'relative_time': _relative_time(n.created_at),
        })

    return ApiResponse.success(data={
        'items': items,
        'total': paginator.count,
        'page': page_obj.number,
        'has_next': page_obj.has_next(),
        'unread_count': NotificationService.get_unread_count(request.user),
    })


@login_required
@require_POST
def api_notification_mark_read(request):
    """标记通知为已读。body: {"id": 123} 单条；
    {"mark_all": true} 全部已读。
    """
    import json
    data = json.loads(request.body)
    if data.get('mark_all'):
        NotificationService.mark_all_read(request.user)
        return ApiResponse.success(message='已全部标记为已读')
    nid = data.get('id')
    if nid:
        NotificationService.mark_read(nid, request.user)
        return ApiResponse.success(message='已标记为已读')
    return ApiResponse.invalid_param('请指定通知ID')


@login_required
@require_GET
def api_notification_unread_count(request):
    """获取未读通知数量（用于轮询）。"""
    count = NotificationService.get_unread_count(request.user)
    return ApiResponse.success(data={'unread_count': count})


@login_required
@require_POST
def api_notification_clear_all(request):
    """清空当前用户所有通知。"""
    Notification.objects.filter(recipient=request.user).delete()
    return ApiResponse.success(message='已清空全部通知')


def _get_avatar_data(user):
    """返回头像数据，用于通知中展示发送者头像。"""
    if not user:
        return {}
    try:
        profile = getattr(user, 'profile', None)
    except Exception:
        profile = None
    if profile and profile.avatar:
        return {'avatar_url': profile.avatar.url, 'avatar_initial': '', 'avatar_color': ''}
    display_name = user.first_name or user.username
    initial = display_name[0].upper() if display_name else '?'
    colors = ['#4A90D9', '#E67E22', '#27AE60', '#E74C3C', '#8E44AD',
              '#2C3E50', '#16A085', '#D35400', '#2980B9', '#C0392B']
    idx = sum(ord(c) for c in user.username) % len(colors)
    return {'avatar_url': '', 'avatar_initial': initial, 'avatar_color': colors[idx]}


def _relative_time(dt):
    """返回相对时间字符串。"""
    import datetime
    now = datetime.datetime.now()
    diff = now - dt
    if diff.days > 365:
        return f'{diff.days // 365}年前'
    if diff.days > 30:
        return f'{diff.days // 30}个月前'
    if diff.days > 0:
        return f'{diff.days}天前'
    if diff.seconds >= 3600:
        return f'{diff.seconds // 3600}小时前'
    if diff.seconds >= 60:
        return f'{diff.seconds // 60}分钟前'
    return '刚刚'
