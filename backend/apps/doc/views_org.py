# coding:utf-8
"""组织架构管理 API"""

import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http.response import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils.translation import gettext_lazy as _

from backend.apps.doc.models import OrgNode, OrgUser


def _get_member_org_path(user):
    """获取用户主属组织的完整路径（使用节点名称）。"""
    try:
        ou = OrgUser.objects.filter(user=user, is_primary=True).select_related('org_node').first()
        if ou and ou.org_node:
            node = ou.org_node
            return _resolve_node_path_names(node.path) if node.path else node.name
    except Exception:
        pass
    return ''


def _resolve_node_path_names(path):
    """将物化路径（如 /1/5/12）解析为节点名称路径（如 总部 / 人事部 / 薪资管理组）。"""
    if not path:
        return ''
    ids = [int(x) for x in path.strip('/').split('/') if x]
    nodes = {n.id: n.name for n in OrgNode.objects.filter(pk__in=ids)}
    return ' / '.join(nodes.get(nid, str(nid)) for nid in ids)


def _check_org_admin(user, node):
    """检查用户是否是节点（或其任意祖先节点）的部门管理员。超管始终返回 True。"""
    if user.is_superuser:
        return True
    if not user.is_authenticated:
        return False
    # 检查当前节点
    if node.admin_id == user.id:
        return True
    # 沿父节点向上追溯
    current = node.parent
    while current:
        if current.admin_id == user.id:
            return True
        current = current.parent
    return False


def _get_subtree_member_count(node):
    """统计本节点及所有子孙节点的成员总数。"""
    descendant_ids = OrgNode.objects.filter(
        Q(pk=node.id) | Q(path__startswith=node.path + '/')
    ).values_list('id', flat=True)
    return OrgUser.objects.filter(org_node_id__in=descendant_ids).count()


def _serialize_node(node, user=None):
    """序列化单个节点。user 为当前请求用户，用于计算 is_admin。"""
    data = {
        'id': node.id,
        'name': node.name,
        'parent_id': node.parent_id,
        'path': node.path,
        'depth': node.depth,
        'sort_order': node.sort_order,
        'admin_id': node.admin_id,
        'member_count': _get_subtree_member_count(node),
    }
    if user and user.is_authenticated:
        data['is_admin'] = _check_org_admin(user, node)
    return data


def _build_subtree(node, user=None):
    """递归构建树节点数据。"""
    data = _serialize_node(node, user)
    children = OrgNode.objects.filter(parent=node).order_by('sort_order', 'id')
    data['children'] = [_build_subtree(c, user) for c in children]
    return data


def _rebuild_path(node):
    """重建节点及其所有后代的物化路径。"""
    if node.parent:
        node.path = f'{node.parent.path}/{node.id}'
        node.depth = node.parent.depth + 1
    else:
        node.path = f'/{node.id}'
        node.depth = 0
    node.save(update_fields=['path', 'depth'])
    for child in OrgNode.objects.filter(parent=node):
        _rebuild_path(child)


# ========== 树结构接口 ==========

@login_required
@require_GET
def api_org_tree(request):
    """返回组织架构树（含用户数统计）。"""
    roots = OrgNode.objects.filter(parent__isnull=True).order_by('sort_order', 'id')
    tree = [_build_subtree(r, request.user) for r in roots]
    return JsonResponse({'status': True, 'tree': tree})


@login_required
@require_GET
def api_org_node_detail(request, node_id):
    """获取单个节点详情（含成员列表）。"""
    try:
        node = OrgNode.objects.get(pk=node_id)
    except OrgNode.DoesNotExist:
        return JsonResponse({'status': False, 'message': '节点不存在'}, status=404)
    members = OrgUser.objects.filter(org_node=node).select_related('user__profile')
    member_list = []
    for m in members:
        u = m.user
        profile = getattr(u, 'profile', None)
        member_list.append({
            'id': u.id,
            'username': u.username,
            'display_name': u.first_name or u.username,
            'avatar_url': profile.avatar.url if profile and profile.avatar else '',
            'is_primary': m.is_primary,
            'org_path': _get_member_org_path(u),
            'joined_at': m.joined_at.strftime('%Y-%m-%d %H:%M'),
        })
    return JsonResponse({
        'status': True,
        'node': _serialize_node(node, request.user),
        'members': member_list,
    })


# ========== 节点 CRUD ==========

@login_required
@require_POST
def api_org_node_create(request):
    """创建组织节点。"""
    data = json.loads(request.body)
    name = data.get('name', '').strip()
    parent_id = data.get('parent_id')
    if not name or len(name) > 64:
        return JsonResponse({'status': False, 'message': '节点名称长度需在1-64字符之间'})
    parent = None
    if parent_id:
        try:
            parent = OrgNode.objects.get(pk=parent_id)
        except OrgNode.DoesNotExist:
            return JsonResponse({'status': False, 'message': '父节点不存在'})
        if not _check_org_admin(request.user, parent):
            return JsonResponse({'status': False, 'message': '无权限操作此节点'}, status=403)
    if OrgNode.objects.filter(parent=parent, name=name).exists():
        return JsonResponse({'status': False, 'message': '同级下已存在同名节点'})
    with transaction.atomic():
        node = OrgNode.objects.create(
            name=name, parent=parent,
            sort_order=OrgNode.objects.filter(parent=parent).count() * 100,
        )
        _rebuild_path(node)
    return JsonResponse({'status': True, 'node': _serialize_node(node)})


@login_required
@require_POST
def api_org_node_rename(request, node_id):
    """重命名组织节点。"""
    try:
        node = OrgNode.objects.get(pk=node_id)
    except OrgNode.DoesNotExist:
        return JsonResponse({'status': False, 'message': '节点不存在'}, status=404)
    if not _check_org_admin(request.user, node):
        return JsonResponse({'status': False, 'message': '无权限操作此节点'}, status=403)
    data = json.loads(request.body)
    new_name = data.get('name', '').strip()
    if not new_name or len(new_name) > 64:
        return JsonResponse({'status': False, 'message': '节点名称长度需在1-64字符之间'})
    if OrgNode.objects.filter(parent=node.parent, name=new_name).exclude(pk=node_id).exists():
        return JsonResponse({'status': False, 'message': '同级下已存在同名节点'})
    node.name = new_name
    node.save(update_fields=['name'])
    return JsonResponse({'status': True, 'message': '重命名成功'})


@login_required
@require_POST
def api_org_node_delete(request, node_id):
    """删除组织节点。子节点迁移至父节点（可选），或随父节点一同删除。"""
    try:
        node = OrgNode.objects.get(pk=node_id)
    except OrgNode.DoesNotExist:
        return JsonResponse({'status': False, 'message': '节点不存在'}, status=404)
    if not _check_org_admin(request.user, node):
        return JsonResponse({'status': False, 'message': '无权限操作此节点'}, status=403)
    data = json.loads(request.body)
    migrate_children_to_parent = data.get('migrate_children', True)
    if node.children.exists():
        if migrate_children_to_parent and node.parent:
            new_parent = node.parent
            with transaction.atomic():
                for child in node.children.all():
                    child.parent = new_parent
                    child.save(update_fields=['parent'])
                    _rebuild_path(child)
                node.delete()
        elif not migrate_children_to_parent:
            with transaction.atomic():
                for child in node.children.all():
                    child.delete()  # 级联删除子节点及关联
                node.delete()
        else:
            return JsonResponse({'status': False, 'message': '该节点为根节点且有子节点，无法迁移至父节点'}, status=400)
        return JsonResponse({'status': True, 'message': '删除成功'})
    node.delete()
    return JsonResponse({'status': True, 'message': '删除成功'})


@login_required
@require_GET
def api_org_search(request):
    """搜索组织节点（按名称模糊匹配），用于权限管理中的目标选择器。"""
    q = request.GET.get('q', '').strip()
    if not q or len(q) < 1:
        nodes = OrgNode.objects.all()[:20]
        results = []
        for n in nodes:
            results.append({
                'id': n.id,
                'name': n.name,
                'path': n.path or '',
                'depth': n.depth,
                'parent_id': n.parent_id,
                'member_count': _get_subtree_member_count(n),
                'has_children': n.children.exists(),
            })
        return JsonResponse({'status': True, 'results': results})
    nodes = OrgNode.objects.filter(name__icontains=q)[:20]
    results = []
    for n in nodes:
        results.append({
            'id': n.id,
            'name': n.name,
            'path': n.path or '',
            'depth': n.depth,
            'parent_id': n.parent_id,
            'member_count': _get_subtree_member_count(n),
            'has_children': n.children.exists(),
        })
    return JsonResponse({'status': True, 'results': results})


@login_required
@require_GET
def api_org_members_list(request, node_id):
    """获取组织节点（含所有子孙节点）的所有成员 ID 列表（用于批量授权）。"""
    try:
        node = OrgNode.objects.get(pk=node_id)
    except OrgNode.DoesNotExist:
        return JsonResponse({'status': False, 'message': '组织节点不存在'}, status=404)
    # 获取本节点及所有子孙节点
    descendant_ids = OrgNode.objects.filter(
        Q(pk=node_id) | Q(path__startswith=node.path + '/')
    ).values_list('id', flat=True)
    member_ids = list(OrgUser.objects.filter(
        org_node_id__in=descendant_ids
    ).values_list('user_id', flat=True).distinct())
    return JsonResponse({'status': True, 'member_ids': member_ids, 'count': len(member_ids)})


# ========== 成员管理 ==========

@login_required
@require_POST
def api_org_add_members(request, node_id):
    """添加人员到组织节点。"""
    try:
        node = OrgNode.objects.get(pk=node_id)
    except OrgNode.DoesNotExist:
        return JsonResponse({'status': False, 'message': '节点不存在'}, status=404)
    if not _check_org_admin(request.user, node):
        return JsonResponse({'status': False, 'message': '无权限操作此节点'}, status=403)
    data = json.loads(request.body)
    user_ids = data.get('user_ids', [])
    is_primary = data.get('is_primary', False)
    if not user_ids:
        return JsonResponse({'status': False, 'message': '请选择用户'})
    added = 0
    for uid in user_ids:
        _, created = OrgUser.objects.get_or_create(org_node=node, user_id=uid)
        if created:
            added += 1
            # 系统通知：被添加到组织节点
            try:
                added_user = User.objects.get(pk=uid)
                from backend.apps.doc.services import NotificationService
                NotificationService.send(
                    recipient=added_user, notification_type='perm_change',
                    title=f'你已被添加到「{node.name}」部门',
                    sender=request.user, send_email=True,
                    body=f'{request.user.first_name or request.user.username} 将你添加到了「{node.name}」部门',
                    link='/user_center/?tab=my_org',
                )
            except User.DoesNotExist:
                pass
        if is_primary:
            OrgUser.objects.filter(user_id=uid).update(is_primary=False)
            OrgUser.objects.filter(org_node=node, user_id=uid).update(is_primary=True)
    if added > 0:
        # 失效该组织节点关联文档的权限缓存
        from backend.apps.doc.services import PermissionService
        PermissionService.invalidate_for_org(node_id)
    return JsonResponse({'status': True, 'message': f'成功添加 {added} 人'})


@login_required
@require_POST
def api_org_remove_member(request, node_id):
    """从组织节点移除人员。"""
    try:
        node = OrgNode.objects.get(pk=node_id)
    except OrgNode.DoesNotExist:
        return JsonResponse({'status': False, 'message': '节点不存在'}, status=404)
    if not _check_org_admin(request.user, node):
        return JsonResponse({'status': False, 'message': '无权限操作此节点'}, status=403)
    data = json.loads(request.body)
    user_id = data.get('user_id')
    if not user_id:
        return JsonResponse({'status': False, 'message': '请指定用户'})
    deleted, _ = OrgUser.objects.filter(org_node=node, user_id=user_id).delete()
    if deleted:
        # 失效该组织节点关联文档的权限缓存
        from backend.apps.doc.services import PermissionService
        PermissionService.invalidate_for_org(node_id)
        # 系统通知：被移出组织节点
        try:
            removed_user = User.objects.get(pk=user_id)
            from backend.apps.doc.services import NotificationService
            NotificationService.send(
                recipient=removed_user, notification_type='perm_change',
                title=f'你已被移出「{node.name}」部门',
                sender=request.user, send_email=True,
                body=f'{request.user.first_name or request.user.username} 将你移出了「{node.name}」部门',
            )
        except User.DoesNotExist:
            pass
        return JsonResponse({'status': True, 'message': '已移除'})
    return JsonResponse({'status': False, 'message': '该用户不在此部门中'})


@login_required
@require_POST
def api_org_set_primary(request, node_id):
    """设置用户的主属部门。"""
    data = json.loads(request.body)
    user_id = data.get('user_id')
    if not user_id:
        return JsonResponse({'status': False, 'message': '请指定用户'})
    if not OrgUser.objects.filter(org_node_id=node_id, user_id=user_id).exists():
        return JsonResponse({'status': False, 'message': '用户不在此部门'})
    OrgUser.objects.filter(user_id=user_id).update(is_primary=False)
    OrgUser.objects.filter(org_node_id=node_id, user_id=user_id).update(is_primary=True)
    return JsonResponse({'status': True, 'message': '已设置为主属部门'})


# ========== 部门管理员 ==========

@login_required
@require_POST
def api_org_appoint_admin(request, node_id):
    """任命部门管理员。被任命者必须是该部门或其子部门成员。"""
    try:
        node = OrgNode.objects.get(pk=node_id)
    except OrgNode.DoesNotExist:
        return JsonResponse({'status': False, 'message': '节点不存在'}, status=404)
    if not _check_org_admin(request.user, node):
        return JsonResponse({'status': False, 'message': '无权限操作此节点'}, status=403)
    data = json.loads(request.body)
    user_id = data.get('user_id')
    if not user_id:
        return JsonResponse({'status': False, 'message': '请指定用户'})
    node.admin_id = user_id
    node.save(update_fields=['admin'])
    return JsonResponse({'status': True, 'message': '已任命部门管理员'})


@login_required
@require_POST
def api_org_revoke_admin(request, node_id):
    """撤销部门管理员。"""
    try:
        node = OrgNode.objects.get(pk=node_id)
    except OrgNode.DoesNotExist:
        return JsonResponse({'status': False, 'message': '节点不存在'}, status=404)
    if not _check_org_admin(request.user, node):
        return JsonResponse({'status': False, 'message': '无权限操作此节点'}, status=403)
    node.admin_id = None
    node.save(update_fields=['admin'])
    return JsonResponse({'status': True, 'message': '已撤销部门管理员'})
