# coding:utf-8
# iSpaceDoc user profile views
from django.shortcuts import render,redirect
from django.http.response import JsonResponse,Http404,HttpResponseNotAllowed,HttpResponse
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required # 登录需求装饰器
from django.views.decorators.http import require_http_methods,require_GET,require_POST # 视图请求方法装饰器
from django.core.paginator import Paginator,PageNotAnInteger,EmptyPage,InvalidPage # 后端分页
from django.core.exceptions import PermissionDenied,ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from backend.apps.doc.models import Doc,DocTemp,UserProfile,BrowseHistory
from django.contrib.auth.models import User
from django.db.models import Q
from django.db import transaction
from django.urls import reverse
from loguru import logger
from backend.apps.admin.models import UserOptions,SysSetting
import datetime
import traceback
import re
import json
import random
import os
import uuid
import base64
import hashlib
from django.conf import settings


# 分组列表页面
@login_required()
def group_list_page(request):
    from backend.apps.doc.models import Group, GroupMember
    owned = Group.objects.filter(owner=request.user)
    joined = Group.objects.filter(memberships__user=request.user).exclude(owner=request.user)
    groups = list(owned) + list(joined)
    breadcrumb_items = [
        {"name": _('个人中心'), 'url': '/user/center/'},
        {"name": _('分组列表'), 'url': ''},
    ]
    return render(request, 'app_doc/user/my_groups.html', locals())


# 组织架构树页面 → 重定向到个人中心统一入口
@login_required()
def org_tree_page(request):
    return redirect('/user_center/?tab=my_org')


# 个人中心
@login_required()
def user_center(request):
    from backend.apps.doc.models import MyCollect
    # 获取当前tab
    current_tab = request.GET.get('tab', 'profile')
    # redirect tabs that have dedicated fully-functional pages
    tab_redirects = {
        'manage_doc': 'manage_doc',
        'manage_doc_temp': 'manage_doctemp',
    }
    if current_tab in tab_redirects:
        return redirect(tab_redirects[current_tab])
    # tabs that need data fetched client-side (API-based)
    api_tabs = ['security', 'notify', 'my_groups', 'my_org']
    # 确保用户档案存在
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=request.user)
    # 获取用户统计信息
    user_doc_count = Doc.objects.filter(create_user=request.user).count()
    user_collect_count = MyCollect.objects.filter(create_user=request.user).count()
    user_orgs = _get_user_orgs(request.user)
    breadcrumb_items = [{"name": _('个人中心'), 'url': ''}]
    return render(request,'app_doc/user/my_home.html',locals())


# 个人中心菜单
def user_center_menu(request):
    menu_data = [
        {
            "id": 1,
            "title": _("我的概览"),
            "type": 1,
            "icon": "layui-icon layui-icon-console",
            "href": reverse('manage_overview'),
        },
        {
            "id": "my_doc",
            "title": _("我的文档"),
            "icon": "layui-icon layui-icon-file-b",
            "type": 0,
            "href": "",
            "children": [
                {
                    "id": "doc_manage",
                    "title": _("文档管理"),
                    "icon": "layui-icon layui-icon-face-smile",
                    "type": 1,
                    "openType": "_iframe",
                    "href": reverse("manage_doc")
                },
                {
                    "id": "doc_template",
                    "title": _("文档模板"),
                    "icon": "layui-icon layui-icon-face-cry",
                    "type": 1,
                    "openType": "_iframe",
                    "href": reverse("manage_doctemp")
                },
                {
                    "id": "doc_tag",
                    "title": _("文档标签"),
                    "icon": "layui-icon layui-icon-face-cry",
                    "type": 1,
                    "openType": "_iframe",
                    "href": reverse("manage_doc_tag")
                },
                {
                    "id": "doc_share",
                    "title": _("我的分享"),
                    "icon": "layui-icon layui-icon-face-cry",
                    "type": 1,
                    "openType": "_iframe",
                    "href": reverse("manage_doc_share")
                },
                {
                    "id": "doc_recycle",
                    "title": _("文档回收站"),
                    "icon": "layui-icon layui-icon-face-cry",
                    "type": 1,
                    "openType": "_iframe",
                    "href": reverse("doc_recycle")
                }
            ]
        },
        {
            "id": "my_fodder",
            "title": _("我的素材"),
            "icon": "layui-icon layui-icon-upload-drag",
            "type": 0,
            "href": "",
            "children": [
                {
                    "id": "my_img",
                    "title": _("我的图片"),
                    "icon": "layui-icon layui-icon-face-smile",
                    "type": 1,
                    "openType": "_iframe",
                    "href": reverse("manage_image")
                },
                {
                    "id": "my_attachment",
                    "title": _("我的附件"),
                    "icon": "layui-icon layui-icon-face-cry",
                    "type": 1,
                    "openType": "_iframe",
                    "href": reverse("manage_attachment")
                },
            ]
        },
        {
            "id": "my_collect",
            "title": _("我的收藏"),
            "icon": "layui-icon layui-icon-star",
            "type": 1,
            "openType": "_iframe",
            "href": reverse("user_center") + "?tab=my_collects"
        },
        {
            "id": "self_settings",
            "title": _("个人管理"),
            "icon": "layui-icon layui-icon-set-fill",
            "type": 0,
            "href": "",
            "children": [
                {
                    "id": 601,
                    "title": _("个人设置"),
                    "icon": "layui-icon layui-icon-face-smile",
                    "type": 1,
                    "openType": "_iframe",
                    "href": reverse("manage_self")
                },
                {
                    "id": 602,
                    "title": _("Token管理"),
                    "icon": "layui-icon layui-icon-face-cry",
                    "type": 1,
                    "openType": "_iframe",
                    "href": reverse("manage_token")
                },
            ]
        },

    ]
    return JsonResponse(menu_data,safe=False)


# ========== v1.0 用户 API ==========

@require_GET
def api_user_search(request):
    """用户搜索（@提及、授权对象选择），支持按姓名或用户名模糊匹配。"""
    q = request.GET.get('q', '').strip()
    if not q or len(q) < 1:
        # 无搜索词时返回前 20 个活跃用户
        users = User.objects.filter(is_active=True, is_superuser=False).select_related('profile')[:20]
        results = []
        for u in users:
            profile = getattr(u, 'profile', None)
            avatar_data = _get_avatar_data(u, profile)
            orgs = _get_user_orgs(u) if profile else []
            results.append({
                'id': u.id,
                'username': u.username,
                'first_name': u.first_name or '',
                'display_name': u.first_name or u.username,
                **avatar_data,
                'org_path': orgs[0]['path'] if orgs else '',
                'orgs': orgs,
            })
        return JsonResponse({'results': results})
    users = User.objects.filter(
        Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q),
        is_active=True, is_superuser=False,
    ).select_related('profile')[:20]
    results = []
    for u in users:
        profile = getattr(u, 'profile', None)
        avatar_data = _get_avatar_data(u, profile)
        orgs = _get_user_orgs(u) if profile else []
        results.append({
            'id': u.id,
            'username': u.username,
            'first_name': u.first_name or '',
            'display_name': u.first_name or u.username,
            **avatar_data,
            'org_path': orgs[0]['path'] if orgs else '',
            'orgs': orgs,
        })
    return JsonResponse({'results': results})


@require_GET
def api_user_profile(request, user_id):
    """用户信息浮窗数据。"""
    try:
        u = User.objects.select_related('profile').get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'error': '用户不存在'}, status=404)
    profile = getattr(u, 'profile', None)
    avatar_data = _get_avatar_data(u, profile)
    return JsonResponse({
        'id': u.id,
        'username': u.username,
        'display_name': u.first_name or u.username,
        **avatar_data,
        'gender': dict(UserProfile.GENDER_CHOICES).get(profile.gender, '未知') if profile else '未知',
        'bio': profile.bio if profile else '',
        'orgs': _get_user_orgs(u) if profile else [],
        'date_joined': u.date_joined.strftime('%Y-%m-%d'),
    })


@login_required
@require_POST
def api_user_profile_edit(request):
    """编辑个人资料。"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    data = json.loads(request.body)
    if 'first_name' in data:
        request.user.first_name = data['first_name'][:30]
        request.user.save(update_fields=['first_name'])
    if 'gender' in data and data['gender'] in ('M', 'F', 'U'):
        profile.gender = data['gender']
    if 'phone' in data:
        phone_val = data['phone'][:20] or None
        if phone_val and UserProfile.objects.filter(phone=phone_val).exclude(user=request.user).exists():
            return JsonResponse({'status': False, 'message': '手机号已被其他用户使用'})
        profile.phone = phone_val
    if 'bio' in data:
        profile.bio = data['bio'][:512]
    profile.save()
    return JsonResponse({'status': True, 'message': '保存成功'})


def _get_user_orgs(user):
    """获取用户所有归属组织的完整路径（用名称表示），按主属优先排序。"""
    from backend.apps.doc.models import OrgUser, OrgNode
    orgs = []
    try:
        ous = OrgUser.objects.filter(user=user).select_related('org_node').order_by('-is_primary', 'id')
        for ou in ous:
            if ou.org_node:
                node = ou.org_node
                # 从物化路径解析 ID 列表，一次查询获取所有祖先名称
                path_ids = [int(x) for x in node.path.strip('/').split('/') if x]
                name_map = {n.id: n.name for n in OrgNode.objects.filter(id__in=path_ids)}
                names = [name_map.get(pid, str(pid)) for pid in path_ids]
                path = ' / '.join(names) if names else node.name
                orgs.append({
                    'name': node.name,
                    'path': path,
                    'is_primary': ou.is_primary,
                })
    except Exception:
        pass
    return orgs


# ========== 密码修改 API ==========

@login_required
@require_POST
def api_change_password(request):
    """修改当前用户密码。"""
    data = json.loads(request.body)
    old_pwd = data.get('old_password', '')
    new_pwd1 = data.get('new_password1', '')
    new_pwd2 = data.get('new_password2', '')
    if not old_pwd or not new_pwd1:
        return JsonResponse({'status': False, 'message': '请填写所有密码字段'})
    if new_pwd1 != new_pwd2:
        return JsonResponse({'status': False, 'message': '两次输入的新密码不一致'})
    if len(new_pwd1) < 6:
        return JsonResponse({'status': False, 'message': '新密码长度不能少于6位'})
    if not request.user.check_password(old_pwd):
        return JsonResponse({'status': False, 'message': '当前密码不正确'})
    request.user.set_password(new_pwd1)
    request.user.save()
    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, request.user)
    return JsonResponse({'status': True, 'message': '密码修改成功'})


# ========== 登录记录 API ==========

@login_required
@require_GET
def api_login_records(request):
    """获取当前用户的最近登录记录。"""
    from backend.apps.admin.models import LoginRecord
    records = LoginRecord.objects.filter(user=request.user).order_by('-created_at')[:20]
    result = []
    for r in records:
        result.append({
            'ip': r.ip_address or '',
            'ua': _parse_ua_brief(r.user_agent or ''),
            'success': r.success,
            'reason': r.failure_reason,
            'time': r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    return JsonResponse({'status': True, 'records': result})


def _parse_ua_brief(ua_string):
    """解析 User-Agent 为简短的设备/浏览器描述。"""
    if not ua_string:
        return ''
    brief = ua_string
    if 'Windows NT' in ua_string:
        brief = 'Windows'
    elif 'Mac OS X' in ua_string:
        brief = 'Mac'
    elif 'Linux' in ua_string and 'Android' not in ua_string:
        brief = 'Linux'
    elif 'Android' in ua_string:
        brief = 'Android'
    elif 'iPhone' in ua_string or 'iPad' in ua_string:
        brief = 'iOS'
    if 'Chrome' in ua_string and 'Edg' not in ua_string:
        brief += ' / Chrome'
    elif 'Edg' in ua_string:
        brief += ' / Edge'
    elif 'Firefox' in ua_string:
        brief += ' / Firefox'
    elif 'Safari' in ua_string and 'Chrome' not in ua_string:
        brief += ' / Safari'
    return brief


# ========== 我的分组 & 组织 API ==========

@login_required
@require_GET
def api_my_groups(request):
    """获取当前用户所属的分组列表（包括自己创建的和加入的）。"""
    from backend.apps.doc.models import Group, GroupMember
    result = []
    seen_ids = set()

    # 用户创建的分组（owner）
    owned = Group.objects.filter(owner=request.user)
    for g in owned:
        result.append({
            'id': g.id,
            'name': g.name,
            'description': g.description,
            'member_count': g.member_count,
            'owner_name': request.user.first_name or request.user.username,
            'owner_id': g.owner_id,
            'is_owner': True,
            'joined_at': g.created_at.strftime('%Y-%m-%d'),
        })
        seen_ids.add(g.id)

    # 用户作为成员加入的分组（排除已作为 owner 的）
    memberships = GroupMember.objects.filter(user=request.user).exclude(group_id__in=seen_ids).select_related('group__owner')
    for m in memberships:
        g = m.group
        result.append({
            'id': g.id,
            'name': g.name,
            'description': g.description,
            'member_count': g.member_count,
            'owner_name': g.owner.first_name or g.owner.username if g.owner else '',
            'owner_id': g.owner_id,
            'is_owner': False,
            'is_admin': m.is_admin,
            'joined_at': m.joined_at.strftime('%Y-%m-%d'),
        })
    return JsonResponse({'status': True, 'groups': result})


@login_required
@require_GET
def api_my_drafts(request):
    """获取当前用户的最近草稿（最多5条）。"""
    drafts = Doc.objects.filter(create_user=request.user, status=0).order_by('-modify_time')[:5]
    result = [{
        'id': d.id,
        'name': d.name,
        'modify_time': d.modify_time.strftime('%Y-%m-%d %H:%M'),
    } for d in drafts]
    return JsonResponse({'status': True, 'drafts': result})


@login_required
@require_GET
def api_my_orgs(request):
    """获取当前用户所属的组织节点列表。"""
    from backend.apps.doc.models import OrgUser, OrgNode
    from backend.apps.doc.views_org import _check_org_admin
    ous = OrgUser.objects.filter(user=request.user).select_related('org_node')
    # 收集所有 path 中的节点 ID，批量获取名称
    all_ids = set()
    for ou in ous:
        node = ou.org_node
        if node.path:
            all_ids.update(int(x) for x in node.path.strip('/').split('/') if x)
    node_names = {n.id: n.name for n in OrgNode.objects.filter(pk__in=all_ids)}

    def _resolve_path(p):
        if not p:
            return ''
        ids = [int(x) for x in p.strip('/').split('/') if x]
        return ' / '.join(node_names.get(nid, str(nid)) for nid in ids)

    result = []
    for ou in ous:
        node = ou.org_node
        result.append({
            'id': node.id,
            'name': node.name,
            'path': node.path,
            'path_display': _resolve_path(node.path) or node.name,
            'is_primary': ou.is_primary,
            'is_admin': _check_org_admin(request.user, node),
            'depth': node.depth,
        })
    result.sort(key=lambda x: (not x['is_primary'], x['depth']))
    return JsonResponse({'status': True, 'orgs': result})


# ========== 通知设置 API ==========

@login_required
@require_GET
def api_notify_settings(request):
    """获取当前用户的通知设置。"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    import json as _json
    try:
        settings_data = _json.loads(profile.notify_settings or '{}')
    except _json.JSONDecodeError:
        settings_data = {}
    defaults = {
        'email_enabled': True,
        'email_comment': True,
        'email_mention': True,
        'email_perm_change': True,
        'email_perm_apply': True,
        'email_doc_change': True,
        'email_daily_summary': False,
        'daily_summary_hour': 9,
        'wecom_userid': '',
        'dingtalk_userid': '',
        'oa_userid': '',
    }
    for k, v in defaults.items():
        if k not in settings_data:
            settings_data[k] = v
    return JsonResponse({'status': True, 'settings': settings_data})


@login_required
@require_POST
def api_notify_settings_save(request):
    """保存当前用户的通知设置。"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    import json as _json
    data = _json.loads(request.body)
    allowed_keys = {'email_enabled', 'email_comment', 'email_mention', 'email_perm_change',
                    'email_perm_apply', 'email_doc_change', 'email_daily_summary',
                    'daily_summary_hour',
                    'wecom_userid', 'dingtalk_userid', 'oa_userid'}
    settings_data = {}
    for k in allowed_keys:
        if k in data:
            settings_data[k] = data[k]
    profile.notify_settings = _json.dumps(settings_data, ensure_ascii=False)
    profile.save(update_fields=['notify_settings'])
    return JsonResponse({'status': True, 'message': '设置已保存'})


def _get_avatar_data(user, profile=None):
    """返回头像 URL 和首字头像降级数据。"""
    if profile is None:
        profile = getattr(user, 'profile', None)
    if profile and profile.avatar:
        return {'avatar_url': profile.avatar.url, 'avatar_initial': '', 'avatar_color': ''}
    display_name = user.first_name or user.username
    initial = display_name[0].upper() if display_name else '?'
    colors = ['#4A90D9', '#E67E22', '#27AE60', '#E74C3C', '#8E44AD',
              '#2C3E50', '#16A085', '#D35400', '#2980B9', '#C0392B']
    color_index = sum(ord(c) for c in user.username) % len(colors)
    return {'avatar_url': '', 'avatar_initial': initial, 'avatar_color': colors[color_index]}


# 头像上传允许的图片格式（范围比通用图片上传更宽）
AVATAR_ALLOWED_SUFFIXES = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'tif'}


@login_required
@require_POST
def api_avatar_upload(request):
    """头像上传，裁剪为 1:1 正方形并生成 200x200 缩略图。"""
    from backend.apps.doc.storage.security import validate_content_type

    try:
        avatar_file = request.FILES.get('avatar')
        if not avatar_file:
            return JsonResponse({'status': False, 'message': '未选择文件'})
        suffix = avatar_file.name.rsplit('.', 1)[-1].lower()
        if suffix not in AVATAR_ALLOWED_SUFFIXES:
            return JsonResponse({'status': False, 'message': '不支持的图片格式，请上传 JPG/PNG/GIF/BMP/WebP 格式的图片'})
        if avatar_file.size > 5 * 1024 * 1024:
            return JsonResponse({'status': False, 'message': '图片大小不能超过5MB'})

        # 读取文件头进行 MIME 类型检测
        file_header = avatar_file.read(512)
        avatar_file.seek(0)
        is_allowed, _ = validate_content_type(file_header, list(AVATAR_ALLOWED_SUFFIXES))
        if not is_allowed:
            return JsonResponse({'status': False, 'message': '文件内容与扩展名不匹配，请上传真实图片文件'})

        from PIL import Image
        img = Image.open(avatar_file)
        # 居中裁剪为正方形
        w, h = img.size
        size = min(w, h)
        left = (w - size) // 2
        top = (h - size) // 2
        img = img.crop((left, top, left + size, top + size))
        # 缩放到 200x200
        img = img.resize((200, 200), Image.LANCZOS)

        # 如果图片有透明通道（RGBA），转换为 RGB 以保存为 JPEG
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img

        # 保存到头像目录
        from io import BytesIO
        from django.core.files.uploadedfile import InMemoryUploadedFile

        buf = BytesIO()
        img.save(buf, 'JPEG', quality=85)
        buf.seek(0)

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        filename = f'{uuid.uuid4().hex[:12]}.jpg'

        # 使用 Django ImageField 保存，由配置的 storage backend 处理
        profile.avatar.save(filename, InMemoryUploadedFile(
            buf, None, filename, 'image/jpeg', buf.getbuffer().nbytes, None
        ), save=False)
        profile.save(update_fields=['avatar'])
        return JsonResponse({'status': True, 'url': profile.avatar.url})
    except ImportError:
        return JsonResponse({'status': False, 'message': '服务器未安装 Pillow 库，无法处理头像'})
    except Exception as e:
        logger.exception("头像上传失败")
        return JsonResponse({'status': False, 'message': f'上传失败: {str(e)}'})


@login_required
@require_GET
def api_browse_history(request):
    """返回当前用户最近浏览的文档和项目列表（基于数据库持久化存储），支持分页。"""
    from django.urls import reverse

    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 50)), 50)

    # 从数据库读取浏览记录
    history_qs = BrowseHistory.objects.filter(user=request.user).order_by('-viewed_at')
    total = history_qs.count()
    if total == 0:
        return JsonResponse({'status': True, 'items': [], 'has_more': False, 'total': 0})

    start = (page - 1) * page_size
    page_records = history_qs[start:start + page_size]

    doc_ids = [r.content_id for r in page_records if r.content_type == 'doc']

    doc_map = {}
    if doc_ids:
        for d in Doc.objects.filter(id__in=doc_ids).select_related('create_user'):
            doc_map[d.id] = d

    def _is_alive(d):
        return d.status == 1 and not d.is_deleted

    items = []
    for r in page_records:
        if r.content_type == 'doc':
            d = doc_map.get(r.content_id)
            if d:
                if _is_alive(d):
                    items.append({
                        'type': 'doc',
                        'id': d.id,
                        'name': d.name,
                        'user_id': d.create_user_id,
                        'user_name': d.create_user.first_name or d.create_user.username if d.create_user else '',
                        'modify_time': d.modify_time.strftime('%Y-%m-%d %H:%M'),
                        'url': reverse('doc_by_id', args=[d.id]),
                        'is_deleted': False,
                    })
                else:
                    items.append({
                        'type': 'doc',
                        'id': d.id,
                        'name': d.name,
                        'user_name': '',
                        'modify_time': (d.deleted_at or d.modify_time).strftime('%Y-%m-%d %H:%M'),
                        'url': '',
                        'is_deleted': True,
                    })
            else:
                items.append({
                    'type': 'doc',
                    'id': r.content_id,
                    'name': '已删除文档',
                    'user_name': '',
                    'modify_time': '',
                    'url': '',
                    'is_deleted': True,
                })

    return JsonResponse({'status': True, 'items': items, 'has_more': (start + page_size) < total, 'total': total})


# ========== 文档模板 API ==========

@login_required
@require_POST
def api_user_doctemp_list(request):
    """返回当前用户的文档模板列表（分页+搜索）。"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    kw = request.POST.get('kw', '')
    page = int(request.POST.get('page', 1))
    page_size = min(int(request.POST.get('page_size', 10)), 50)
    if kw:
        queryset = DocTemp.objects.filter(create_user=request.user,
            content__icontains=kw).order_by('-modify_time')
    else:
        queryset = DocTemp.objects.filter(create_user=request.user).order_by('-modify_time')
    paginator = Paginator(queryset, page_size)
    try:
        items_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        items_page = paginator.page(1) if paginator.num_pages > 0 else []
    items = []
    for t in items_page:
        items.append({
            'id': t.id,
            'name': t.name,
            'content': t.content[:200],
            'create_time': t.create_time.strftime('%Y-%m-%d %H:%M'),
            'modify_time': t.modify_time.strftime('%Y-%m-%d %H:%M'),
        })
    return JsonResponse({
        'status': True, 'items': items,
        'total': paginator.count, 'page': page,
        'has_more': page < paginator.num_pages,
    })


@login_required
@require_POST
def api_user_doctemp_delete(request):
    """删除当前用户的文档模板。"""
    doctemp_id = request.POST.get('doctemp_id', '')
    if not doctemp_id:
        return JsonResponse({'status': False, 'message': '参数错误'})
    try:
        t = DocTemp.objects.get(id=int(doctemp_id))
        if t.create_user != request.user:
            return JsonResponse({'status': False, 'message': '无权操作'})
        t.delete()
        return JsonResponse({'status': True, 'message': '删除成功'})
    except DocTemp.DoesNotExist:
        return JsonResponse({'status': False, 'message': '模板不存在'})
    except Exception:
        logger.exception("删除文档模板出错")
        return JsonResponse({'status': False, 'message': '请求出错'})


# ========== Token API ==========

@login_required
@require_GET
def api_user_token_info(request):
    """返回当前用户的 API Token 信息。"""
    try:
        from backend.apps.api.models import UserToken
        token = UserToken.objects.get(user=request.user)
        return JsonResponse({
            'status': True,
            'token': token.token,
        })
    except UserToken.DoesNotExist:
        return JsonResponse({'status': True, 'token': None})
    except Exception:
        logger.exception("获取Token信息出错")
        return JsonResponse({'status': False, 'message': '获取失败'})
