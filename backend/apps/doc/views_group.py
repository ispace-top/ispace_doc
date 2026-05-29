# coding:utf-8
"""分组管理 API"""

import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http.response import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils.translation import gettext_lazy as _

from backend.apps.doc.models import Group, GroupMember


def _is_group_manager(group, user):
    """检查用户是否为分组的 owner 或 admin。"""
    if group.owner_id == user.id:
        return True
    return GroupMember.objects.filter(group=group, user=user, is_admin=True).exists()


# ========== 分组 CRUD ==========

@login_required
@require_POST
def api_group_create(request):
    """创建分组。"""
    data = json.loads(request.body)
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()[:256]
    if not name or len(name) > 64:
        return JsonResponse({'status': False, 'message': '分组名称长度需在1-64字符之间'})
    if Group.objects.filter(name=name).exists():
        return JsonResponse({'status': False, 'message': '分组名称已存在'})
    group = Group.objects.create(name=name, description=description, owner=request.user)
    return JsonResponse({
        'status': True,
        'group': {
            'id': group.id, 'name': group.name, 'description': group.description,
            'owner_id': group.owner_id, 'member_count': group.member_count,
            'created_at': group.created_at.strftime('%Y-%m-%d %H:%M'),
        }
    })


@login_required
@require_GET
def api_group_list(request):
    """获取用户创建或加入的分组列表。"""
    owned = Group.objects.filter(owner=request.user)
    joined = Group.objects.filter(memberships__user=request.user).exclude(owner=request.user)
    groups = list(owned) + list(joined)
    result = []
    for g in groups:
        result.append({
            'id': g.id, 'name': g.name, 'description': g.description,
            'owner_id': g.owner_id, 'member_count': g.member_count,
            'created_at': g.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_owner': g.owner_id == request.user.id,
        })
    return JsonResponse({'status': True, 'groups': result})


@login_required
@require_POST
def api_group_update(request, group_id):
    """修改分组名称和描述（仅 owner）。"""
    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        return JsonResponse({'status': False, 'message': '分组不存在'}, status=404)
    if not _is_group_manager(group, request.user):
        return JsonResponse({'status': False, 'message': '仅分组管理员可修改'}, status=403)
    data = json.loads(request.body)
    name = data.get('name', '').strip()
    if name and name != group.name:
        if Group.objects.filter(name=name).exists():
            return JsonResponse({'status': False, 'message': '分组名称已存在'})
        group.name = name
    if 'description' in data:
        group.description = data['description'].strip()[:256]
    group.save(update_fields=['name', 'description'])
    return JsonResponse({'status': True, 'message': '修改成功'})


@login_required
@require_POST
def api_group_delete(request, group_id):
    """删除分组（仅 owner）。"""
    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        return JsonResponse({'status': False, 'message': '分组不存在'}, status=404)
    if group.owner_id != request.user.id:
        return JsonResponse({'status': False, 'message': '仅分组管理员可删除'}, status=403)
    group.delete()
    return JsonResponse({'status': True, 'message': '删除成功'})


# ========== 成员管理 ==========

@login_required
@require_GET
def api_group_members(request, group_id):
    """获取分组成员列表。"""
    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        return JsonResponse({'status': False, 'message': '分组不存在'}, status=404)
    members = GroupMember.objects.filter(group=group).select_related('user__profile')
    result = []
    for m in members:
        u = m.user
        profile = getattr(u, 'profile', None)
        result.append({
            'id': u.id, 'username': u.username,
            'display_name': u.first_name or u.username,
            'avatar_url': profile.avatar.url if profile and profile.avatar else '',
            'is_admin': m.is_admin,
            'joined_at': m.joined_at.strftime('%Y-%m-%d %H:%M'),
        })
    return JsonResponse({'status': True, 'members': result, 'owner_id': group.owner_id})


@login_required
@require_POST
def api_group_add_members(request, group_id):
    """添加成员到分组（仅 owner）。"""
    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        return JsonResponse({'status': False, 'message': '分组不存在'}, status=404)
    if not _is_group_manager(group, request.user):
        return JsonResponse({'status': False, 'message': '仅分组管理员可操作'}, status=403)
    data = json.loads(request.body)
    user_ids = data.get('user_ids', [])
    if not user_ids:
        return JsonResponse({'status': False, 'message': '请选择用户'})
    users = User.objects.filter(pk__in=user_ids, is_active=True)
    added = 0
    for u in users:
        _, created = GroupMember.objects.get_or_create(group=group, user=u)
        if created:
            added += 1
            # 系统通知：被添加到分组
            from backend.apps.doc.services import NotificationService
            NotificationService.send(
                recipient=u, notification_type='perm_change',
                title=f'你已被添加到分组「{group.name}」',
                sender=request.user, send_email=True,
                body=f'{request.user.first_name or request.user.username} 将你添加到了分组「{group.name}」',
                link=f'/my/groups/',
            )
    if added > 0:
        group.member_count = GroupMember.objects.filter(group=group).count()
        group.save(update_fields=['member_count'])
        # 失效该分组关联文档的权限缓存
        from backend.apps.doc.services import PermissionService
        PermissionService.invalidate_for_group(group_id)
    return JsonResponse({'status': True, 'message': f'成功添加 {added} 人'})


@login_required
@require_POST
def api_group_remove_member(request, group_id):
    """移除分组中的成员（仅 owner）。"""
    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        return JsonResponse({'status': False, 'message': '分组不存在'}, status=404)
    if not _is_group_manager(group, request.user):
        return JsonResponse({'status': False, 'message': '仅分组管理员可操作'}, status=403)
    data = json.loads(request.body)
    user_id = data.get('user_id')
    if not user_id:
        return JsonResponse({'status': False, 'message': '请指定用户'})
    if user_id == group.owner_id:
        return JsonResponse({'status': False, 'message': '不能移除分组创建者'})
    # 管理员不能移除其他管理员（仅 owner 可操作）
    is_current_user_owner = group.owner_id == request.user.id
    if not is_current_user_owner and GroupMember.objects.filter(group=group, user_id=user_id, is_admin=True).exists():
        return JsonResponse({'status': False, 'message': '仅创建者可移除其他管理员'}, status=403)
    deleted, _ = GroupMember.objects.filter(group=group, user_id=user_id).delete()
    if deleted:
        group.member_count = GroupMember.objects.filter(group=group).count()
        group.save(update_fields=['member_count'])
        # 失效该分组关联文档的权限缓存
        from backend.apps.doc.services import PermissionService
        PermissionService.invalidate_for_group(group_id)
        # 系统通知：被移出分组
        try:
            removed_user = User.objects.get(pk=user_id)
            from backend.apps.doc.services import NotificationService
            NotificationService.send(
                recipient=removed_user, notification_type='perm_change',
                title=f'你已被移出分组「{group.name}」',
                sender=request.user, send_email=True,
                body=f'{request.user.first_name or request.user.username} 将你移出了分组「{group.name}」',
            )
        except User.DoesNotExist:
            pass
        return JsonResponse({'status': True, 'message': '已移除'})
    return JsonResponse({'status': False, 'message': '该用户不在分组中'})


@login_required
@require_GET
def api_group_search(request):
    """搜索分组（按名称模糊匹配），用于权限管理中的目标选择器。"""
    q = request.GET.get('q', '').strip()
    if not q or len(q) < 1:
        groups = Group.objects.all()[:20]
        results = []
        for g in groups:
            results.append({
                'id': g.id,
                'name': g.name,
                'description': g.description or '',
                'member_count': g.member_count or 0,
                'owner_name': g.owner.first_name or g.owner.username if g.owner_id else '',
            })
        return JsonResponse({'status': True, 'results': results})
    groups = Group.objects.filter(name__icontains=q)[:20]
    results = []
    for g in groups:
        results.append({
            'id': g.id,
            'name': g.name,
            'description': g.description or '',
            'member_count': g.member_count or 0,
            'owner_name': g.owner.first_name or g.owner.username if g.owner_id else '',
        })
    return JsonResponse({'status': True, 'results': results})


@login_required
@require_GET
def api_group_members_list(request, group_id):
    """获取分组的所有成员 ID 列表（用于批量授权）。"""
    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        return JsonResponse({'status': False, 'message': '分组不存在'}, status=404)
    member_ids = list(GroupMember.objects.filter(group=group).values_list('user_id', flat=True))
    # Include the owner
    if group.owner_id and group.owner_id not in member_ids:
        member_ids.append(group.owner_id)
    return JsonResponse({'status': True, 'member_ids': member_ids, 'count': len(member_ids)})


@login_required
@require_POST
def api_group_set_admin(request, group_id):
    """设置或取消分组管理员（仅 owner 可操作）。"""
    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        return JsonResponse({'status': False, 'message': '分组不存在'}, status=404)
    if group.owner_id != request.user.id:
        return JsonResponse({'status': False, 'message': '仅分组创建者可设置管理员'}, status=403)
    data = json.loads(request.body)
    user_id = data.get('user_id')
    is_admin = data.get('is_admin', False)
    if not user_id or user_id == group.owner_id:
        return JsonResponse({'status': False, 'message': '不能对创建者执行此操作'})
    try:
        member = GroupMember.objects.get(group=group, user_id=user_id)
    except GroupMember.DoesNotExist:
        return JsonResponse({'status': False, 'message': '该用户不在分组中'})
    member.is_admin = is_admin
    member.save(update_fields=['is_admin'])
    from backend.apps.doc.services import PermissionService
    PermissionService.invalidate_for_group(group_id)
    msg = '已设为管理员' if is_admin else '已取消管理员'
    return JsonResponse({'status': True, 'message': msg, 'is_admin': is_admin})


@login_required
@require_POST
def api_group_transfer_owner(request, group_id):
    """转让分组管理员给组内成员（仅 owner）。"""
    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        return JsonResponse({'status': False, 'message': '分组不存在'}, status=404)
    if group.owner_id != request.user.id:
        return JsonResponse({'status': False, 'message': '仅分组管理员可操作'}, status=403)
    data = json.loads(request.body)
    new_owner_id = data.get('user_id')
    if not new_owner_id or new_owner_id == request.user.id:
        return JsonResponse({'status': False, 'message': '请指定组内其他成员'})
    if not GroupMember.objects.filter(group=group, user_id=new_owner_id).exists():
        return JsonResponse({'status': False, 'message': '目标用户不在分组中，请先添加为成员'})
    group.owner_id = new_owner_id
    group.save(update_fields=['owner'])
    # 系统通知：新管理员
    try:
        new_owner = User.objects.get(pk=new_owner_id)
        from backend.apps.doc.services import NotificationService
        NotificationService.send(
            recipient=new_owner, notification_type='perm_change',
            title=f'你已成为分组「{group.name}」的管理员',
            sender=request.user, send_email=True,
            body=f'{request.user.first_name or request.user.username} 将分组「{group.name}」的管理员转让给了你',
            link='/my/groups/',
        )
    except User.DoesNotExist:
        pass
    return JsonResponse({'status': True, 'message': '已转让'})


@login_required
@require_POST
def api_group_leave(request, group_id):
    """退出分组（非 owner 成员可自行退出）。"""
    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        return JsonResponse({'status': False, 'message': '分组不存在'}, status=404)
    if group.owner_id == request.user.id:
        return JsonResponse({'status': False, 'message': '分组创建者不能退出，请先转让管理员或删除分组'})
    deleted, _ = GroupMember.objects.filter(group=group, user=request.user).delete()
    if deleted:
        group.member_count = GroupMember.objects.filter(group=group).count()
        group.save(update_fields=['member_count'])
        from backend.apps.doc.services import PermissionService
        PermissionService.invalidate_for_group(group_id)
        return JsonResponse({'status': True, 'message': '已退出分组'})
    return JsonResponse({'status': False, 'message': '你不在此分组中'})
