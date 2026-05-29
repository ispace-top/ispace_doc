# coding:utf-8
"""文档权限管理 API"""

import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from django.views.decorators.http import require_GET, require_POST
from django.utils.translation import gettext_lazy as _

from backend.apps.doc.models import Doc, DocPermission, Group, OrgNode
from backend.apps.doc.services import PermissionService, _PERM_RANK
from backend.apps.doc.api_response import ApiResponse


def _check_doc_admin(user, doc):
    """检查用户是否是文档管理员（所有者或有 admin 权限）。"""
    if user.is_superuser:
        return True
    if doc.create_user_id == user.id:
        return True
    return PermissionService.get_effective_permission(user, doc) == 'admin'


def _count_non_superuser_admins(doc):
    """统计文档的非超管管理员数量（含创建者 + 被授权 admin 的非超管用户）。"""
    count = 0
    # 创建者如果不是超管，算管理员
    from django.contrib.auth.models import User as AuthUser
    try:
        creator = AuthUser.objects.only('is_superuser').get(pk=doc.create_user_id)
    except AuthUser.DoesNotExist:
        creator = None
    if creator and not creator.is_superuser:
        count += 1
    # 统计被授予 admin 权限的非超管用户
    admin_user_ids = DocPermission.objects.filter(
        doc=doc, target_type='user', permission='admin'
    ).values_list('target_id', flat=True)
    for uid in admin_user_ids:
        try:
            u = AuthUser.objects.only('is_superuser').get(pk=uid)
            if not u.is_superuser:
                count += 1
        except AuthUser.DoesNotExist:
            pass
    return count


def _parse_permission_target(data):
    """从请求数据中解析授权目标对象。"""
    target_type = data.get('target_type')
    target_id = data.get('target_id')
    if target_type not in ('user', 'group', 'org'):
        return None, None, '无效的授权对象类型'
    if not target_id:
        return None, None, '请指定授权对象'
    return target_type, target_id, None


# ========== 权限查询 ==========

@login_required
@require_GET
def api_doc_permissions(request, doc_id):
    """获取文档的所有权限授权列表。"""
    try:
        doc = Doc.objects.only('create_user_id', 'top_doc', 'status').get(pk=doc_id)
    except Doc.DoesNotExist:
        return ApiResponse.not_found('文档不存在')
    if not _check_doc_admin(request.user, doc):
        return ApiResponse.forbidden('无权限查看此文档的授权设置')

    perms = DocPermission.objects.filter(doc=doc).select_related('granted_by')
    result = []
    for p in perms:
        display_name = ''
        if p.target_type == 'user':
            try:
                u = User.objects.only('first_name', 'username', 'is_superuser').get(pk=p.target_id)
                # 系统管理员默认拥有所有文档最高权限，不显示在授权列表中
                if u.is_superuser:
                    continue
                display_name = u.first_name or u.username
            except User.DoesNotExist:
                display_name = f'用户#{p.target_id}'
        elif p.target_type == 'group':
            try:
                g = Group.objects.only('name').get(pk=p.target_id)
                display_name = g.name
            except Group.DoesNotExist:
                display_name = f'分组#{p.target_id}'
        elif p.target_type == 'org':
            try:
                n = OrgNode.objects.only('name').get(pk=p.target_id)
                display_name = n.name
            except OrgNode.DoesNotExist:
                display_name = f'组织#{p.target_id}'
        result.append({
            'id': p.id,
            'target_type': p.target_type,
            'target_id': p.target_id,
            'display_name': display_name,
            'permission': p.permission,
            'apply_to_children': p.apply_to_children,
            'granted_by_name': p.granted_by.first_name or p.granted_by.username if p.granted_by else '',
            'granted_at': p.granted_at.strftime('%Y-%m-%d %H:%M'),
        })
    return ApiResponse.success(data={'permissions': result})


# ========== 授权 / 修改权限 ==========

@login_required
@require_POST
def api_doc_permission_grant(request, doc_id):
    """授予或更新文档权限。已存在的权限记录会被覆盖为新的权限级别。"""
    try:
        doc = Doc.objects.only('create_user_id', 'top_doc', 'status', 'name').get(pk=doc_id)
    except Doc.DoesNotExist:
        return ApiResponse.not_found('文档不存在')
    if not _check_doc_admin(request.user, doc):
        return ApiResponse.forbidden('仅文档管理员可授权')

    data = json.loads(request.body)
    target_type, target_id, err = _parse_permission_target(data)
    if err:
        return ApiResponse.invalid_param(err)
    perm_level = data.get('permission', 'view')
    if perm_level not in ('view', 'edit', 'admin'):
        return ApiResponse.invalid_param('权限级别无效')

    # 系统管理员默认拥有所有文档最高权限，不允许授权
    if target_type == 'user':
        try:
            target_user = User.objects.only('is_superuser').get(pk=target_id)
            if target_user.is_superuser:
                return ApiResponse.invalid_param('不能为系统管理员设置权限')
        except User.DoesNotExist:
            return ApiResponse.invalid_param('用户不存在')

    apply_to_children = data.get('apply_to_children', False)

    # 最少管理员约束：如果是在降级已有的 admin 权限，检查是否还有别的管理员
    if perm_level != 'admin':
        existing = DocPermission.objects.filter(
            doc=doc, target_type=target_type, target_id=target_id
        ).first()
        if existing and existing.permission == 'admin':
            if _count_non_superuser_admins(doc) <= 1:
                return ApiResponse.invalid_param('不能移除最后一个非系统管理员的管理员权限')

    perm, created = DocPermission.objects.update_or_create(
        doc=doc, target_type=target_type, target_id=target_id,
        defaults={
            'permission': perm_level,
            'apply_to_children': apply_to_children,
            'granted_by': request.user,
        }
    )
    # 失效该文档的权限缓存
    from backend.apps.doc.services import PermissionService
    PermissionService.invalidate_cache(doc_id)
    # 如果是用户级别的授权，发送通知给被授权者
    if target_type == 'user' and target_id != request.user.id:
        from backend.apps.doc.services import NotificationService
        try:
            grantee = User.objects.get(pk=target_id)
            NotificationService.send(
                recipient=grantee, notification_type='perm_change',
                title=f'你获得了文档《{doc.name}》的{perm.get_permission_display()}权限',
                sender=request.user, send_email=True,
                link=f'/pages/{doc.top_doc}/{doc_id}/',
                context={'doc_name': doc.name, 'perm_detail': perm.get_permission_display()},
            )
        except User.DoesNotExist:
            pass
    return ApiResponse.success(
        data={'permission_id': perm.id},
        message='已授权' if created else '权限已更新',
    )


# ========== 撤销权限 ==========

@login_required
@require_POST
def api_doc_permission_revoke(request, doc_id):
    """撤销某条权限记录。"""
    try:
        doc = Doc.objects.only('create_user_id', 'top_doc', 'name').get(pk=doc_id)
    except Doc.DoesNotExist:
        return ApiResponse.not_found('文档不存在')
    if not _check_doc_admin(request.user, doc):
        return ApiResponse.forbidden('仅文档管理员可撤销授权')

    data = json.loads(request.body)
    perm_id = data.get('permission_id')
    target_type = data.get('target_type')
    target_id = data.get('target_id')

    # 查找待撤销的权限（用于通知和最少管理员校验）
    revoked_perms = []
    if perm_id:
        revoked_perms = list(DocPermission.objects.filter(pk=perm_id, doc=doc).values('target_type', 'target_id', 'permission'))
    elif target_type and target_id:
        revoked_perms = list(DocPermission.objects.filter(doc=doc, target_type=target_type, target_id=target_id).values('target_type', 'target_id', 'permission'))
    else:
        return ApiResponse.invalid_param('请指定要撤销的权限')

    # 最少管理员约束：检查撤销后是否还有非超管管理员
    is_revoking_admin = any(p['permission'] == 'admin' for p in revoked_perms)
    if is_revoking_admin:
        current_admin_count = _count_non_superuser_admins(doc)
        if current_admin_count <= 1:
            return ApiResponse.invalid_param('不能撤销最后一个非系统管理员的管理员权限')

    if perm_id:
        DocPermission.objects.filter(pk=perm_id, doc=doc).delete()
    else:
        DocPermission.objects.filter(doc=doc, target_type=target_type, target_id=target_id).delete()

    # 失效该文档的权限缓存
    from backend.apps.doc.services import PermissionService
    PermissionService.invalidate_cache(doc_id)

    # 发送权限撤销通知给被操作的用户
    from backend.apps.doc.services import NotificationService
    from backend.apps.doc.models import User
    for p in revoked_perms:
        if p['target_type'] == 'user' and p['target_id'] != request.user.id:
            try:
                grantee = User.objects.get(pk=p['target_id'])
                NotificationService.send(
                    recipient=grantee, notification_type='perm_change',
                    title=f'你失去了文档《{doc.name}》的{p["permission"]}权限',
                    sender=request.user, send_email=True,
                    body=f'{request.user.first_name or request.user.username} 撤销了你在文档《{doc.name}》的权限',
                    link=f'/pages/{doc.top_doc}/{doc_id}/',
                    context={'doc_name': doc.name, 'perm_detail': p["permission"]},
                )
            except User.DoesNotExist:
                pass

    return ApiResponse.success(message='已撤销授权')


# ========== 批量授权 ==========

@login_required
@require_POST
def api_doc_permission_batch(request, doc_id):
    """批量授予/更新文档权限。"""
    try:
        doc = Doc.objects.only('create_user_id', 'top_doc').get(pk=doc_id)
    except Doc.DoesNotExist:
        return ApiResponse.not_found('文档不存在')
    if not _check_doc_admin(request.user, doc):
        return ApiResponse.forbidden('仅文档管理员可操作')

    data = json.loads(request.body)
    items = data.get('items', [])
    if not items:
        return ApiResponse.invalid_param('请提供授权项')

    created = 0
    updated = 0
    superuser_ids = set(
        User.objects.filter(is_superuser=True).values_list('id', flat=True)
    )
    for item in items:
        tt = item.get('target_type')
        tid = item.get('target_id')
        pl = item.get('permission', 'view')
        if tt not in ('user', 'group', 'org') or not tid or pl not in ('view', 'edit', 'admin'):
            continue
        # 不允许为系统管理员授权
        if tt == 'user' and tid in superuser_ids:
            continue
        ac = item.get('apply_to_children', False)
        _, is_new = DocPermission.objects.update_or_create(
            doc=doc, target_type=tt, target_id=tid,
            defaults={'permission': pl, 'apply_to_children': ac, 'granted_by': request.user},
        )
        if is_new:
            created += 1
        else:
            updated += 1

    return ApiResponse.success(message=f'新建 {created} 条，更新 {updated} 条')


# ========== 检查当前用户权限 ==========

@login_required
@require_GET
def api_doc_my_permission(request, doc_id):
    """查询当前用户对某文档的最终权限。"""
    try:
        doc = Doc.objects.only('create_user_id', 'top_doc', 'status').get(pk=doc_id)
    except Doc.DoesNotExist:
        return ApiResponse.not_found('文档不存在')
    perm = PermissionService.get_effective_permission(request.user, doc)
    can_admin = _check_doc_admin(request.user, doc)
    return ApiResponse.success(data={
        'permission': perm,
        'can_admin': can_admin,
        'is_owner': doc.create_user_id == request.user.id,
        'is_superuser': request.user.is_superuser,
    })


def _get_doc_admins(doc):
    """获取文档管理员列表（创建者 + 被授予 admin 权限的用户）。"""
    from django.contrib.auth.models import User as AuthUser
    admins = []
    added_ids = set()
    # 创建者
    try:
        creator = AuthUser.objects.only('id', 'first_name', 'username').get(pk=doc.create_user_id)
        admins.append(creator)
        added_ids.add(creator.id)
    except AuthUser.DoesNotExist:
        pass
    # 被授权的 admin
    admin_perm_user_ids = DocPermission.objects.filter(
        doc=doc, target_type='user', permission='admin'
    ).values_list('target_id', flat=True)
    for uid in admin_perm_user_ids:
        if uid in added_ids:
            continue
        try:
            u = AuthUser.objects.only('id', 'first_name', 'username').get(pk=uid)
            admins.append(u)
            added_ids.add(uid)
        except AuthUser.DoesNotExist:
            pass
    return admins


# ========== 权限申请 ==========

@login_required
@require_POST
def api_doc_permission_apply(request, doc_id):
    """申请文档查看权限。向文档管理员发送通知。"""
    try:
        doc = Doc.objects.only('create_user_id', 'top_doc', 'name').get(pk=doc_id)
    except Doc.DoesNotExist:
        return ApiResponse.not_found('文档不存在')

    # 如果已有权限，直接返回
    existing = PermissionService.get_effective_permission(request.user, doc)
    if existing is not None:
        return ApiResponse.error(4, '你已有此文档的访问权限')

    # 检查是否重复申请（24小时内同一文档不重复发送）
    from django.utils import timezone
    from datetime import timedelta
    from backend.apps.doc.models import Notification
    recent = Notification.objects.filter(
        recipient=request.user,
        notification_type='perm_apply',
        link__contains=f'/pages/{doc.top_doc}/{doc_id}',
        created_at__gte=timezone.now() - timedelta(hours=24),
    ).exists()
    if recent:
        return ApiResponse.error(4, '你已在24小时内提交过申请，请耐心等待')

    # 读取申请理由（可选）
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}
    reason = data.get('reason', '').strip() if isinstance(data, dict) else ''

    admins = _get_doc_admins(doc)
    if not admins:
        return ApiResponse.error(4, '该文档暂无管理员，无法申请')

    from backend.apps.doc.services import NotificationService
    requester_name = request.user.first_name or request.user.username
    import urllib.parse
    for admin in admins:
        if admin.id == request.user.id:
            continue
        body_text = f'用户 {requester_name} 申请查看文档《{doc.name}》的权限。'
        if reason:
            body_text += f'\n申请理由：{reason}'
        body_text += '\n点击立即授予查看权限。'
        link = f'/pages/{doc_id}/?grant_perm={request.user.id}&requester_name={urllib.parse.quote(requester_name)}'
        if reason:
            link += f'&apply_reason={urllib.parse.quote(reason)}'
        NotificationService.send(
            recipient=admin,
            notification_type='perm_apply',
            title=f'{requester_name} 申请查看文档《{doc.name}》',
            sender=request.user, send_email=True,
            body=body_text,
            link=link,
            context={'doc_name': doc.name, 'reason': reason},
        )
    return ApiResponse.success(message='已发送权限申请')


@login_required
@require_GET
def api_doc_permissions_summary(request):
    """批量获取用户对多篇文档的权限摘要。

    GET /api/docs/permissions/summary/?doc_ids=1,2,3

    返回: {doc_id: {permission, is_owner, is_public}, ...}
    """
    from backend.apps.doc.services import PermissionService
    from backend.apps.doc.api_response import ApiResponse

    doc_ids_str = request.GET.get("doc_ids", "")
    if not doc_ids_str:
        return ApiResponse.error(1, "缺少 doc_ids 参数")

    try:
        doc_ids = [int(x.strip()) for x in doc_ids_str.split(",") if x.strip()]
    except ValueError:
        return ApiResponse.error(1, "doc_ids 格式无效")

    if not doc_ids:
        return ApiResponse.error(1, "doc_ids 为空")

    docs = Doc.objects.filter(id__in=doc_ids)
    perms = PermissionService.batch_get_permissions(request.user, docs)

    summary = {}
    for doc in docs:
        summary[str(doc.id)] = {
            "permission": perms.get(doc.id),
            "is_owner": doc.create_user_id == request.user.id,
            "is_public": doc.is_public,
        }

    return ApiResponse.success(data={"permissions": summary, "total": len(summary)})


@login_required
def api_doc_access_mode(request, doc_id):
    """获取或更新文档访问模式（公开/密码访问/授权访问）。

    GET  /api/docs/<doc_id>/access/ → {"is_public": true, "access_password": ""}
    POST /api/docs/<doc_id>/access/ → body: {"is_public": true/false, "access_password": ""}
    """
    from django.shortcuts import get_object_or_404

    doc = get_object_or_404(Doc, id=doc_id)

    if request.method == "GET":
        return ApiResponse.success(data={
            "is_public": doc.is_public,
            "access_password": doc.access_password or "",
        })

    if request.method == "POST":
        if not _check_doc_admin(request.user, doc):
            return ApiResponse.error(403, "无权修改此文档的访问模式")

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}

        is_public = data.get("is_public", None)
        access_password = data.get("access_password", None)

        if is_public is not None:
            doc.is_public = is_public
        if access_password is not None:
            doc.access_password = access_password.strip()

        doc.save(update_fields=["is_public", "access_password"])
        # 访问模式变更后失效权限缓存，确保授权检查即时生效
        PermissionService.invalidate_cache(doc_id)
        return ApiResponse.success(data={
            "is_public": doc.is_public,
            "access_password": doc.access_password or "",
        }, message="访问模式已更新")

    return ApiResponse.error(405, "Method not allowed")
