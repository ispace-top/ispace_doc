# coding:utf-8
from django.shortcuts import render,redirect
from django.urls import reverse
from django.http.response import JsonResponse,Http404,HttpResponseNotAllowed,HttpResponse
from django.http import QueryDict
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required # 登录需求装饰器
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods,require_GET,require_POST # 视图请求方法装饰器
from django.core.paginator import Paginator,PageNotAnInteger,EmptyPage,InvalidPage # 后端分页
from django.core.exceptions import PermissionDenied,ObjectDoesNotExist
from django.core.serializers import serialize
from backend.apps.doc.models import Doc,DocTemp,DocComment,DocHistory,DocLike,DocTag,DocShare,MyCollect,InlineComment,BrowseHistory,Tag
from django.contrib.auth.models import User
from rest_framework.views import APIView # 视图
from rest_framework.response import Response # 响应
from rest_framework.pagination import PageNumberPagination # 分页
from rest_framework.authentication import SessionAuthentication # 认证
from django.db.models import Q, Count
from django.db import transaction
from django.utils.html import strip_tags,escape
from django.utils.translation import gettext_lazy as _
from loguru import logger
from backend.apps.api.serializers_app import *
from backend.apps.doc.outline_utils import parse_outline
from backend.apps.admin.models import UserOptions,SysSetting


from backend.apps.admin.utils import is_zip_bomb
from backend.apps.api.auth_app import AppAuth,AppMustAuth # 自定义认证
import datetime
import traceback
import re
import json
import random
import os
import os.path
import base64
import hashlib
import tempfile
import markdown
from backend.apps.doc.report_html2pdf import convert as html2pdf


def _record_browse_history(request, content_type, content_id, extra_id=None):
    """记录浏览记录：已登录用户写入数据库，游客写入 session"""
    if request.user.is_authenticated:
        BrowseHistory.objects.update_or_create(
            user=request.user,
            content_type=content_type,
            content_id=content_id,
            defaults={'extra_id': extra_id, 'viewed_at': datetime.datetime.now()}
        )
    # 同时维护 session 作为热缓存（不跨设备但速度快）
    recent = request.session.get('recent_views', [])
    recent = [r for r in recent if not (r[0] == content_type and r[1] == content_id)]
    entry = [content_type, content_id]
    if extra_id is not None:
        entry.append(extra_id)
    recent.insert(0, entry)
    request.session['recent_views'] = recent[:1000]
import tempfile


# HTML转义
def _sanitize_json(data):
    payloads = {
        '\'':'&apos;',
        '"':'&quot;',
        '<':'&lt;',
        '>':'&gt;'
    }
    if type(data) == dict:
        new = {}
        for key,values in data.items():
            new[key] = _sanitize_json(values)
    elif type(data) == list:
        new = []
        for i in data:
            new.append(_sanitize_json(i))
    elif type(data) == int or type(data) == float:
        new = data
    elif type(data) == str:
        new = data
        for key,value in payloads.items():
            new = new.replace(key,value)
    elif type(data) ==bytes:
        new = data
    else:
        # print('>>> unknown type:')
        # print(type(data))
        new = data
    return new


def _escape_html(data):
    if len(data) == 0:
        return ""
    payloads = {
        '\'':'&apos;',
        '"':'&quot;',
        '<':'&lt;',
        '>':'&gt;'
    }
    new = data
    for key, value in payloads.items():
        new = new.replace(key, value)
    return new


# 替换前端传来的非法字符
def _sanitize_title(title):
  rstr = r"[\/\\\:\*\?\"\<\>\|\[\]]" # '/ \ : * ? " < > |'
  new_title = re.sub(rstr, "_", title) # 替换为下划线
  return new_title

# 文档文本生成摘要（不带markdown标记和html标签）
def _strip_markdown_preview(docs):
    for doc in docs:
        try:
            if doc.editor_mode == 1:
                doc.pre_content = "此为表格文档，进入文档查看详细内容"
            else: # 其他文档
                doc.pre_content = strip_tags(markdown.markdown(doc.pre_content))[:201]
        except Exception as e:
            doc.pre_content = doc.pre_content[:201]

# 获取文档目录树
def _build_doc_tree(doc_id=None):
    """构建文档树并返回 (层次化树列表, 扁平化列表, 总数)。
    若传入 doc_id，则仅构建该文档所属的子树范围。
    """
    # 获取所有已发布的可见文档
    base_qs = Doc.objects.filter(status=1, is_deleted=False)
    if doc_id:
        # 找到根节点：向上追溯到 parent_doc=0
        root_id = doc_id
        current = Doc.objects.only('parent_doc').get(pk=doc_id)
        while current.parent_doc and current.parent_doc != 0:
            root_id = current.parent_doc
            current = Doc.objects.only('parent_doc').get(pk=root_id)
        # 从根节点获取整个子树
        root_docs = Doc.objects.filter(pk=root_id)
    else:
        root_docs = base_qs.filter(parent_doc=0)

    parent_ids = set(base_qs.exclude(parent_doc=0).values_list('parent_doc', flat=True))

    def _build_children(parent_id):
        children = list(
            base_qs.filter(parent_doc=parent_id)
            .values('id', 'name', 'open_children', 'editor_mode')
            .order_by('sort')
        )
        result = []
        for c in children:
            item = {
                'id': c['id'],
                'name': c['name'],
                'open_children': c['open_children'],
                'editor_mode': c['editor_mode'],
            }
            if c['id'] in parent_ids:
                item['children'] = _build_children(c['id'])
            else:
                item['children'] = []
            result.append(item)
        return result

    tree = []
    flat_list = []
    for d in root_docs.values('id', 'name', 'open_children', 'editor_mode').order_by('sort'):
        item = {
            'id': d['id'],
            'name': d['name'],
            'open_children': d['open_children'],
            'editor_mode': d['editor_mode'],
        }
        if d['id'] in parent_ids:
            item['children'] = _build_children(d['id'])
        else:
            item['children'] = []
        tree.append(item)

    def _flatten(items):
        for it in items:
            flat_list.append({'id': it['id'], 'name': it['name']})
            _flatten(it.get('children', []))

    _flatten(tree)
    return tree, flat_list, len(flat_list)


# 文档首页
@logger.catch()
def doc_home(request):
    """文档首页 - 列表展示所有可见的已发布文档"""
    kw = request.GET.get('kw', '')  # 搜索词
    sort = request.GET.get('sort', '')  # 排序,0/''表示按时间升序，1表示按时间降序，2表示按热度

    # 排序方式
    if sort in [0, '0']:
        sort_str = 'modify_time'
    elif sort == '':
        try:
            index_project_sort = SysSetting.objects.get(name='index_project_sort')
            sort_str = '-modify_time' if index_project_sort.value == '-1' else 'modify_time'
        except:
            sort_str = 'modify_time'
    else:
        sort_str = '-modify_time'

    # 是否搜索
    is_kw = bool(kw)
    # 是否认证
    is_auth = request.user.is_authenticated

    # 基础查询：已发布且未删除的文档
    doc_qs = Doc.objects.filter(status=1, is_deleted=False)

    if is_auth:
        # 认证用户：公开文档 + 自己创建的文档 + 有显式 DocPermission 的文档
        from backend.apps.doc.models import DocPermission
        perm_doc_ids = DocPermission.objects.filter(
            target_type='user', target_id=request.user.id
        ).values_list('doc_id', flat=True)
        doc_list = doc_qs.filter(
            Q(is_public=True) | Q(create_user=request.user) | Q(id__in=perm_doc_ids)
        ).select_related('create_user')
    else:
        # 游客：仅公开文档
        doc_list = doc_qs.filter(is_public=True).select_related('create_user')

    # 关键词搜索
    if kw:
        doc_list = doc_list.filter(
            Q(name__icontains=kw) | Q(content__icontains=kw) | Q(pre_content__icontains=kw)
        )

    # 排序
    if sort in [2, '2']:  # 按热度（点赞数）排序
        doc_list = doc_list.annotate(like_count=Count('doclike')).order_by('-like_count', '-modify_time')
    else:
        doc_list = doc_list.order_by(sort_str)

    # 分页（12条/页）
    paginator = Paginator(doc_list, 12)
    page = request.GET.get('page', 1)
    try:
        docs = paginator.page(page)
    except PageNotAnInteger:
        docs = paginator.page(1)
    except EmptyPage:
        docs = paginator.page(paginator.num_pages)

    # 最近收藏（仅文档类型 collect_type=1）
    recent_favorites = []
    if is_auth:
        collects = MyCollect.objects.filter(
            create_user=request.user, collect_type=1
        ).order_by('-create_time')[:20]
        doc_ids = [c.collect_id for c in collects]
        doc_map = {}
        if doc_ids:
            for d in Doc.objects.filter(id__in=doc_ids).only('id', 'name', 'top_doc'):
                doc_map[d.id] = d
        for c in collects:
            d = doc_map.get(c.collect_id)
            if d:
                recent_favorites.append({
                    'name': d.name,
                    'type': '文档',
                    'url': '/pages/{}/'.format(d.id),
                    'time': c.create_time,
                })

    # 最近浏览（仅文档类型）
    recent_views = []

    def _is_alive(d):
        return d.status == 1 and not d.is_deleted

    if is_auth:
        # 认证用户从数据库读取
        history_qs = BrowseHistory.objects.filter(
            user=request.user, content_type='doc'
        ).order_by('-viewed_at')[:50]
        if history_qs:
            doc_ids_rv = [r.content_id for r in history_qs]
            doc_map_rv = {}
            if doc_ids_rv:
                for d in Doc.objects.filter(id__in=doc_ids_rv):
                    doc_map_rv[d.id] = d
            for r in history_qs:
                d = doc_map_rv.get(r.content_id)
                if d and _is_alive(d):
                    recent_views.append({
                        'name': d.name,
                        'user': d.create_user.username,
                        'modify_time': d.modify_time,
                        'url': '/pages/{}/'.format(d.id),
                        'is_deleted': False,
                    })
                elif d:
                    recent_views.append({
                        'name': d.name,
                        'user': '',
                        'modify_time': d.deleted_at or d.modify_time,
                        'url': '',
                        'is_deleted': True,
                    })
                else:
                    recent_views.append({
                        'name': '已删除文档',
                        'user': '',
                        'modify_time': '',
                        'url': '',
                        'is_deleted': True,
                    })
    else:
        # 游客从 session 读取
        raw_views = request.session.get('recent_views', [])
        if raw_views:
            doc_ids_rv = [r[1] for r in raw_views if r[0] == 'doc']
            doc_map_rv = {}
            if doc_ids_rv:
                for d in Doc.objects.filter(id__in=doc_ids_rv):
                    doc_map_rv[d.id] = d
            for r in raw_views:
                if r[0] == 'doc':
                    d = doc_map_rv.get(r[1])
                    if d and _is_alive(d):
                        recent_views.append({
                            'name': d.name,
                            'user': d.create_user.username,
                            'modify_time': d.modify_time,
                            'url': '/pages/{}/'.format(d.id),
                            'is_deleted': False,
                        })
                    elif d:
                        recent_views.append({
                            'name': d.name,
                            'user': '',
                            'modify_time': d.deleted_at or d.modify_time,
                            'url': '',
                            'is_deleted': True,
                        })
                    else:
                        recent_views.append({
                            'name': '已删除文档',
                            'user': '',
                            'modify_time': '',
                            'url': '',
                            'is_deleted': True,
                        })

    return render(request, 'app_doc/doc_home.html', locals())

# 文档浏览页
@require_http_methods(['GET'])
def doc(request,pro_id,doc_id):
    try:
        if pro_id != '' and doc_id != '':
            # 获取文档信息
            doc = Doc.objects.get(id=int(doc_id),status__in=[0,1],is_deleted=False) # 文档信息
            # 获取文档目录树（基于文档ID构建子树）
            toc_tree, toc_list, toc_cnt = _build_doc_tree(doc.id)

            # 获取文档收藏状态
            if request.user.is_authenticated:
                is_collect_doc = MyCollect.objects.filter(collect_type=1, collect_id=doc_id,
                                                          create_user=request.user).exists()
            else:
                is_collect_doc = False

            # v1.0 权限检查：调用 PermissionService 三线合并计算
            from backend.apps.doc.services import PermissionService
            effective_perm = PermissionService.get_effective_permission(request.user, doc)
            if effective_perm is None:
                effective_perm = 'none'
            doc_effective_perm = effective_perm

            # 非公开文档且无权限的用户不能访问
            if not doc.is_public and effective_perm == 'none':
                if request.user.is_authenticated:
                    # Show no-permission page with doc info and apply button
                    from backend.apps.doc.views_permission import _get_doc_admins
                    admins = _get_doc_admins(doc)
                    admin_list = [{'id': a.id, 'display_name': a.first_name or a.username} for a in admins]
                    # Check if user already applied in last 24h
                    from django.utils import timezone
                    from datetime import timedelta
                    from backend.apps.doc.models import Notification
                    already_requested = Notification.objects.filter(
                        recipient=request.user, notification_type='perm_apply',
                        link__contains=f'/pages/{doc.id}',
                        created_at__gte=timezone.now() - timedelta(hours=24),
                    ).exists()
                    return render(request, 'app_doc/access_denied.html', {
                        'doc_id': doc.id, 'doc_name': doc.name,
                        'admins': admin_list, 'already_requested': already_requested,
                    })
                return render(request, '404.html')

            # 获取文档内容
            try:
                doc = Doc.objects.get(id=int(doc_id),status__in=[0,1],is_deleted=False) # 文档信息
                doc_tags = DocTag.objects.filter(doc=doc) # 文档标签信息
                doc_tags_str = ','.join([i.tag.name for i in doc_tags])
                # 提取文档中的 @mention 并解析为 {username: user_id} 映射（v1.1.2）
                import re, json
                mention_pattern = r'@([\w.@+-]+)'
                mentioned_usernames = re.findall(mention_pattern, doc.pre_content or '')
                doc_mention_users_json = '{}'
                if mentioned_usernames:
                    mentioned_set = set(mentioned_usernames)
                    mentioned_users = User.objects.filter(username__in=mentioned_set, is_active=True).values('id', 'username')
                    doc_mention_users = {u['username']: u['id'] for u in mentioned_users}
                    doc_mention_users_json = json.dumps(doc_mention_users)
                if doc.status == 0 and doc.create_user != request.user:
                    raise ObjectDoesNotExist
                elif doc.status == 0 and doc.create_user == request.user:
                    if not doc.name.startswith(str(_('【预览草稿】'))):
                        doc.name  = _('【预览草稿】')+ doc.name

            except ObjectDoesNotExist:
                return render(request, '404.html')
            # 获取文档分享信息
            try:
                doc_share = DocShare.objects.get(doc=doc)
                is_share = True
            except ObjectDoesNotExist:
                is_share = False
            # 获取文集下一级文档
            # project_docs = Doc.objects.filter(top_doc=doc.top_doc, parent_doc=0, status=1).order_by('sort')
            # 计算上一篇/下一篇文档
            prev_doc = None
            next_doc = None
            for i, item in enumerate(toc_list):
                if item['id'] == doc.id:
                    if i > 0:
                        prev_doc = toc_list[i - 1]
                    if i < len(toc_list) - 1:
                        next_doc = toc_list[i + 1]
                    break
            # 构建完整面包屑：根文档 → 祖先文档链 → 当前文档
            ancestor_ids = []
            pid = doc.parent_doc
            while pid and pid != 0:
                ancestor_ids.append(pid)
                pid = Doc.objects.filter(id=pid).values_list('parent_doc', flat=True).first() or 0
            breadcrumb_items = []
            if ancestor_ids:
                ancestor_docs = Doc.objects.filter(id__in=ancestor_ids).in_bulk()
                for aid in reversed(ancestor_ids):
                    ad = ancestor_docs.get(aid)
                    if ad:
                        breadcrumb_items.append({
                            'name': ad.name,
                            'url': '/pages/{}/'.format(ad.id)
                        })
            if doc.parent_doc and doc.parent_doc != 0:
                breadcrumb_items.append({'name': doc.name, 'url': ''})
            else:
                breadcrumb_items.append({'name': doc.name, 'url': ''})
            # 获取文档编辑历史（最近10条）
            doc_history = list(DocHistory.objects
                .filter(doc=doc)
                .select_related('create_user')
                .order_by('-create_time')[:10]
                .values('id', 'create_user__username', 'create_user__first_name', 'create_time'))
            # 获取文档点赞状态
            like_count = DocLike.objects.filter(doc=doc).count()
            user_liked = DocLike.objects.filter(doc=doc, user=request.user).exists() if request.user.is_authenticated else False
            # 记录最近浏览
            _record_browse_history(request, 'doc', doc.id, doc.top_doc)
            return render(request,'app_doc/doc.html',locals())
        else:
            return HttpResponse(_('请求参数不正确'))
    except Exception as e:
        logger.exception("文档页面访问异常")
        return render(request,'404.html')


# 文档浏览页，可通过文档ID 访问
@require_http_methods(['GET'])
def doc_id(request,doc_id):
    try:
        # 获取文档内容
        try:
            doc = Doc.objects.get(id=int(doc_id),status__in=[0,1],is_deleted=False) # 文档信息
            doc_tags = DocTag.objects.filter(doc=doc) # 文档标签信息
            doc_tags_str = ','.join([i.tag.name for i in doc_tags])
            pro_id = 0
            if doc.status == 0 and doc.create_user != request.user:
                raise ObjectDoesNotExist
            elif doc.status == 0 and doc.create_user == request.user:
                if not doc.name.startswith(str(_('【预览草稿】'))):
                    doc.name  = _('【预览草稿】')+ doc.name

        except ObjectDoesNotExist:
            return render(request, '404.html')

        # 获取文档目录树（基于文档ID构建子树）
        toc_tree, toc_list, toc_cnt = _build_doc_tree(doc.id)

        # 获取文档收藏状态
        if request.user.is_authenticated:
            is_collect_doc = MyCollect.objects.filter(collect_type=1, collect_id=doc_id,
                                                      create_user=request.user).exists()
        else:
            is_collect_doc = False

        # v1.0 权限检查
        from backend.apps.doc.services import PermissionService
        effective_perm = PermissionService.get_effective_permission(request.user, doc)
        if effective_perm is None:
            effective_perm = 'none'
        doc_effective_perm = effective_perm

        # 非公开文档且无权限的用户不能访问
        if not doc.is_public and effective_perm == 'none':
            if request.user.is_authenticated:
                from backend.apps.doc.views_permission import _get_doc_admins
                admins = _get_doc_admins(doc)
                admin_list = [{'id': a.id, 'display_name': a.first_name or a.username} for a in admins]
                from django.utils import timezone
                from datetime import timedelta
                from backend.apps.doc.models import Notification
                already_requested = Notification.objects.filter(
                    recipient=request.user, notification_type='perm_apply',
                    link__contains=f'/pages/{doc.id}',
                    created_at__gte=timezone.now() - timedelta(hours=24),
                ).exists()
                return render(request, 'app_doc/access_denied.html', {
                    'doc_id': doc.id, 'doc_name': doc.name,
                    'admins': admin_list, 'already_requested': already_requested,
                })
            return render(request, '404.html')

        # 获取文档内容
        try:
            doc = Doc.objects.get(id=int(doc_id),status__in=[0,1],is_deleted=False) # 文档信息
            doc_tags = DocTag.objects.filter(doc=doc) # 文档标签信息
            doc_tags_str = ','.join([i.tag.name for i in doc_tags])
            # 提取文档中的 @mention 并解析为 {username: user_id} 映射
            import re, json
            mention_pattern = r'@([\w.@+-]+)'
            mentioned_usernames = re.findall(mention_pattern, doc.pre_content or '')
            doc_mention_users_json = '{}'
            if mentioned_usernames:
                mentioned_set = set(mentioned_usernames)
                mentioned_users = User.objects.filter(username__in=mentioned_set, is_active=True).values('id', 'username')
                doc_mention_users = {u['username']: u['id'] for u in mentioned_users}
                doc_mention_users_json = json.dumps(doc_mention_users)
            if doc.status == 0 and doc.create_user != request.user:
                raise ObjectDoesNotExist
            elif doc.status == 0 and doc.create_user == request.user:
                if not doc.name.startswith(str(_('【预览草稿】'))):
                    doc.name  = _('【预览草稿】')+ doc.name

        except ObjectDoesNotExist:
            return render(request, '404.html')
        # 获取文档分享信息
        try:
            doc_share = DocShare.objects.get(doc=doc)
            is_share = True
        except ObjectDoesNotExist:
            is_share = False
        # 构建完整面包屑：根文档 → 祖先文档链 → 当前文档
        ancestor_ids = []
        pid = doc.parent_doc
        while pid and pid != 0:
            ancestor_ids.append(pid)
            pid = Doc.objects.filter(id=pid).values_list('parent_doc', flat=True).first() or 0
        breadcrumb_items = []
        if ancestor_ids:
            ancestor_docs = Doc.objects.filter(id__in=ancestor_ids).in_bulk()
            for aid in reversed(ancestor_ids):
                ad = ancestor_docs.get(aid)
                if ad:
                    breadcrumb_items.append({
                        'name': ad.name,
                        'url': '/pages/{}/'.format(ad.id)
                    })
        if doc.parent_doc and doc.parent_doc != 0:
            breadcrumb_items.append({'name': doc.name, 'url': ''})
        else:
            breadcrumb_items.append({'name': doc.name, 'url': ''})
        # 获取文档编辑历史（最近10条）
        doc_history = list(DocHistory.objects
            .filter(doc=doc)
            .select_related('create_user')
            .order_by('-create_time')[:10]
            .values('id', 'create_user__username', 'create_user__first_name', 'create_time'))
        # 获取文档点赞状态
        like_count = DocLike.objects.filter(doc=doc).count()
        user_liked = DocLike.objects.filter(doc=doc, user=request.user).exists() if request.user.is_authenticated else False
        # 记录最近浏览
        _record_browse_history(request, 'doc', doc.id, doc.top_doc)
        return render(request,'app_doc/doc.html',locals())
    except Exception as e:
        logger.exception("文档页面访问异常")
        return render(request,'404.html')


# 创建文档
@login_required()
@require_http_methods(['GET',"POST"])
@logger.catch()
def create_new_document(request):
    # 获取用户的编辑器模式
    try:
        user_opt = UserOptions.objects.get(user=request.user)
        editor_mode = user_opt.editor_mode
    except ObjectDoesNotExist:
        editor_mode = 0  # Markdown
    if request.method == 'GET':
        # 获取url切换的编辑器模式，重定向到内联编辑器页面
        eid = request.GET.get('eid',editor_mode)
        if eid in [0, 1, '0', '1']:
            editor_mode = int(eid)
        # 兼容旧链接：转发文集ID和父文档ID参数
        pid = request.GET.get('pid', '')
        parent_doc = request.GET.get('parent_doc', '')
        redirect_url = '/?create=1&eid=' + str(editor_mode)
        if pid:
            redirect_url += '&pid=' + pid
        if parent_doc:
            redirect_url += '&parent_doc=' + parent_doc
        return redirect(redirect_url)
    elif request.method == 'POST':
        try:
            project = request.POST.get('project','') # 文集ID
            parent_doc = request.POST.get('parent_doc','') # 上级文档ID
            doc_name = request.POST.get('doc_name','') # 文档标题
            doc_tags = request.POST.get('doc_tag','') # 文档标签
            doc_content = request.POST.get('content','') # 文档内容
            pre_content = request.POST.get('pre_content','') # 文档Markdown内容
            sort = request.POST.get('sort','') # 文档排序
            editor_mode = request.POST.get('editor_mode',editor_mode)    #获取文档编辑器
            status = request.POST.get('status',1) # 文档状态
            open_children = request.POST.get('open_children', False)  # 展示下级目录
            show_children = request.POST.get('show_children', False)  # 展示下级目录
            if open_children == 'on':
                open_children = True
            else:
                open_children = False
            if show_children == 'on':
                show_children = True
            else:
                show_children = False
            if doc_name != '':
                if parent_doc and str(parent_doc) != '0':
                    # 如果指定了上级文档，检查用户对上级文档的权限
                    from backend.apps.doc.services import PermissionService
                    try:
                        parent = Doc.objects.get(id=int(parent_doc))
                        parent_perm = PermissionService.get_effective_permission(request.user, parent)
                        if parent_perm not in ('edit', 'admin') and parent.create_user != request.user and not request.user.is_superuser:
                            return JsonResponse({'status': False, 'data': _('无权在该文档下创建子文档')})
                    except Doc.DoesNotExist:
                        return JsonResponse({'status': False, 'data': _('上级文档不存在')})
                # 开启事务
                with transaction.atomic():
                    save_id = transaction.savepoint()
                    try:
                        # 创建文档
                        em = int(editor_mode)
                        source = pre_content if em in (0, 2) else doc_content
                        outline = parse_outline(source, em)
                        doc = Doc.objects.create(
                            name=doc_name,
                            content = doc_content,
                            pre_content= pre_content,
                            parent_doc= int(parent_doc) if parent_doc != '' else 0,
                            top_doc= 0,
                            sort = sort if sort != '' else 9999,
                            create_user=request.user,
                            status = status,
                            editor_mode = em,
                            open_children = open_children,
                            show_children = show_children,
                            outline = outline
                        )
                        # 自动授予创建者 admin 权限
                        from backend.apps.doc.models import DocPermission
                        DocPermission.objects.create(
                            doc=doc, target_type='user', target_id=request.user.id,
                            permission='admin', granted_by=request.user,
                        )
                        # 设置文档标签
                        for t in doc_tags.split(","):
                            if t != '':
                                tag = Tag.objects.get_or_create(name=t,create_user=request.user)
                                DocTag.objects.get_or_create(tag=tag[0],doc=doc)

                        # 文档 @提及通知（仅发布时发送，草稿不发送）
                        mentions = _parse_mentions(pre_content or '')
                        if mentions and int(status) == 1:
                            from backend.apps.doc.services import NotificationService
                            mentioned_users = User.objects.filter(
                                username__in=set(mentions), is_active=True
                            )
                            doc_url = f'/pages/{doc.id}/'
                            for mu in mentioned_users:
                                NotificationService.send(
                                    recipient=mu, notification_type='mention',
                                    title='文档中有人 @了你',
                                    sender=request.user, send_email=True,
                                    body=f'{request.user.first_name or request.user.username} 在文档《{doc_name}》中 @了你',
                                    link=doc_url,
                                    context={'doc_name': doc_name},
                                )

                        return JsonResponse({'status': True, 'data': {'pro': project, 'doc': doc.id}})
                    except Exception as e:
                        logger.exception("创建文档时发生异常")
                        # 回滚事务
                        transaction.savepoint_rollback(save_id)
                    transaction.savepoint_commit(save_id)
                    return JsonResponse({'status': False, 'data': _('文档创建未成功')})
            else:
                return JsonResponse({'status':False,'data':_('请确认文档标题正确')})
        except Exception as e:
            logger.exception("创建文档时发生异常")
            return JsonResponse({'status':False,'data':_('无法处理该请求')})
    else:
        return JsonResponse({'status':False,'data':_('方法不允许')})


# 修改文档
@login_required()
@require_http_methods(['GET',"POST"])
def edit_existing_document(request,doc_id):
    editor_type = _("修改文档")
    if request.method == 'GET':
        try:
            doc = Doc.objects.get(id=doc_id)
            proj_id = doc.top_doc
            # 权限检查：无权限则返回403，有权限则重定向到内联编辑器页面
            from backend.apps.doc.services import PermissionService
            effective_perm = PermissionService.get_effective_permission(request.user, doc)
            if (request.user == doc.create_user) or \
                    (effective_perm in ('edit', 'admin')) or \
                    request.user.is_superuser:
                return redirect('/pages/' + str(doc_id) + '/?edit=1')
            else:
                return render(request,'403.html')
        except Exception as e:
            logger.exception("修改文档页面访问异常")
            return render(request,'404.html')
    elif request.method == 'POST':
        try:
            doc_id = request.POST.get('doc_id','') # 文档ID
            project_id = request.POST.get('project', '') # 文集ID
            parent_doc = request.POST.get('parent_doc', '') # 上级文档ID
            doc_name = request.POST.get('doc_name', '') # 文档名称
            doc_tags = request.POST.get('doc_tag','') # 文档标签
            doc_content = request.POST.get('content', '') # 文档内容
            pre_content = request.POST.get('pre_content', '') # 文档Markdown格式内容
            sort = request.POST.get('sort', '') # 文档排序
            editor_mode = request.POST.get('editor_mode',0)    #获取文档编辑器
            status = request.POST.get('status',1) # 文档状态
            is_auto_save = request.POST.get('is_auto_save','0') # 自动保存标记，为1时不写DocHistory
            open_children = request.POST.get('open_children',False) # 展示下级目录
            show_children = request.POST.get('show_children', False)  # 展示下级目录
            if open_children == 'on':
                open_children = True
            else:
                open_children = False
            if show_children == 'on':
                show_children = True
            else:
                show_children = False

            if doc_id != '' and doc_name != '':
                doc = Doc.objects.get(id=doc_id)
                # 验证用户有权限修改文档：创建者 或 PermissionService 有 edit/admin 权限 或 超级用户
                from backend.apps.doc.services import PermissionService
                effective_perm = PermissionService.get_effective_permission(request.user, doc)
                if (request.user == doc.create_user) or (effective_perm in ('edit', 'admin')) or request.user.is_superuser:
                    # 开启事务
                    with transaction.atomic():
                        save_id = transaction.savepoint()
                        try:
                            # 自动保存不写入历史记录
                            if is_auto_save != '1':
                                DocHistory.objects.create(
                                    doc = doc,
                                    pre_content = doc.pre_content,
                                    create_user = request.user
                                )
                            # 发布时去除草稿标题前缀
                            if int(status) == 1:
                                draft_prefix = str(_('【预览草稿】'))
                                if doc_name.startswith(draft_prefix):
                                    doc_name = doc_name[len(draft_prefix):]
                            # 更新文档内容，parent_doc 未传则保持原值
                            em = int(editor_mode)
                            source = pre_content if em in (0, 2) else doc_content
                            outline = parse_outline(source, em)
                            Doc.objects.filter(id=int(doc_id)).update(
                                name=doc_name,
                                content=doc_content,
                                pre_content=pre_content,
                                parent_doc=int(parent_doc) if parent_doc != '' else doc.parent_doc,
                                sort=sort if sort != '' else 9999,
                                modify_time = datetime.datetime.now(),
                                status = status,
                                editor_mode = em,
                                open_children = open_children,
                                show_children = show_children,
                                outline = outline
                            )
                            # 更新文档标签
                            doc_tag_list = doc_tags.split(",") if doc_tags != "" else []
                            # print(doc_tags,doc_tag_list)
                            # 如果没有设置标签，则删除此文档的所有标签
                            if len(doc_tag_list) == 0:
                                DocTag.objects.filter(doc=doc).delete()
                            else:
                                current_doc_tags = [i.tag.name for i in DocTag.objects.filter(doc=doc)] # 获取当前文档的标签
                                # 遍历当前文档标签，如果不在新的标签列表，则删除
                                for tag in current_doc_tags:
                                    if tag not in doc_tag_list:
                                        tag = Tag.objects.get(name=tag,create_user=request.user)
                                        DocTag.objects.filter(doc=doc,tag=tag).delete()
                                # 遍历新的标签列表，如果不在当前文档标签中，则创建
                                for t in doc_tag_list:
                                    if t not in current_doc_tags and current_doc_tags != '':
                                        tag = Tag.objects.get_or_create(name=t, create_user=request.user)
                                        DocTag.objects.get_or_create(tag=tag[0], doc=doc)

                            # 文档 @提及通知（对比新旧内容，仅通知新增的提及用户）
                            old_mentions = set(_parse_mentions(doc.pre_content or ''))
                            new_mentions = set(_parse_mentions(pre_content or ''))
                            new_mentioned = new_mentions - old_mentions
                            if new_mentioned:
                                from backend.apps.doc.services import NotificationService
                                from backend.apps.doc.models import User
                                mentioned_users = User.objects.filter(
                                    username__in=new_mentioned, is_active=True
                                )
                                doc_url = f'/pages/{doc_id}/'
                                for mu in mentioned_users:
                                    NotificationService.send(
                                        recipient=mu, notification_type='mention',
                                        title='文档中有人 @了你',
                                        sender=request.user, send_email=True,
                                        body=f'{request.user.first_name or request.user.username} 在文档《{doc_name}》中 @了你',
                                        link=doc_url,
                                        context={'doc_name': doc_name},
                                    )
                            # 文档变更通知（通知文档创建者和其他有 admin 权限的用户）
                            if doc.create_user != request.user:
                                from backend.apps.doc.services import NotificationService
                                NotificationService.send(
                                    recipient=doc.create_user,
                                    notification_type='doc_change',
                                    title=f'文档《{doc_name}》被编辑',
                                    sender=request.user, send_email=True,
                                    body=f'{request.user.first_name or request.user.username} 编辑了你的文档《{doc_name}》',
                                    link=f'/pages/{doc_id}/',
                                    context={'doc_name': doc_name, 'change_type': '编辑'},
                                )
                            return JsonResponse({'status': True, 'data': _('修改成功')})
                        except Exception:
                            logger.exception("修改文档时发生异常")
                            # 回滚事务
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'status': False, 'data': _('文档修改未成功')})
                        transaction.savepoint_commit(save_id)
                    return JsonResponse({'status': False, 'data': _('文档修改未成功')})

                else:
                    return JsonResponse({'status':False,'data':_('未授权请求')})
            else:
                return JsonResponse({'status': False,'data':_('请求参数不正确')})
        except Exception:
            logger.exception("修改文档时发生异常")
            from django.conf import settings
            if settings.DEBUG:
                import traceback
                return JsonResponse({'status': False, 'data': traceback.format_exc()})
            return JsonResponse({'status':False,'data':_('无法处理该请求')})


# 删除文档 - 软删除 - 进入回收站
@login_required()
@require_http_methods(["POST"])
def remove_document(request):
    try:
        # 获取文档ID
        doc_id = request.POST.get('doc_id',None)
        range = request.POST.get('range', 'single')
        if doc_id:
            if range == 'single':
                # 查询文档
                try:
                    doc = Doc.objects.get(id=doc_id)
                except ObjectDoesNotExist:
                    return JsonResponse({'status': False, 'data': '文档不存在'})
                # v1.0: 使用 PermissionService 判断权限（文档创建者 / admin权限 / 超级用户）
                from backend.apps.doc.services import PermissionService
                effective_perm = PermissionService.get_effective_permission(request.user, doc)
                if (request.user == doc.create_user) \
                        or (request.user.is_superuser) \
                        or (effective_perm == 'admin'):
                    # v1.0: 使用软删除服务
                    from backend.apps.doc.services import DocService
                    result = DocService.soft_delete(doc_id, request.user)
                    if 'error' in result:
                        return JsonResponse({'status': False, 'data': result['error']})
                    # 通知文档创建者（非本人删除时）
                    if doc.create_user != request.user:
                        from backend.apps.doc.services import NotificationService
                        NotificationService.send(
                            recipient=doc.create_user, notification_type='doc_change',
                            title=f'文档《{doc.name}》被删除',
                            sender=request.user, send_email=True,
                            body=f'{request.user.first_name or request.user.username} 将你的文档《{doc.name}》移入了回收站',
                            link=f'/pages/{doc_id}/',
                            context={'doc_name': doc.name, 'change_type': '删除'},
                        )
                    return JsonResponse({'status': True, 'data': _('删除完成'),
                                         'deleted': result['deleted'],
                                         'children': result['children']})
                else:
                    return JsonResponse({'status': False, 'data': _('操作未被授权')})
            elif range == 'multi':
                docs = doc_id.split(",")
                try:
                    from backend.apps.doc.services import DocService
                    total_deleted = 0
                    for did in docs:
                        did_int = int(did.strip())
                        if request.user.is_superuser or Doc.objects.filter(id=did_int, create_user=request.user).exists():
                            result = DocService.soft_delete(did_int, request.user)
                            if 'error' not in result:
                                total_deleted += result['deleted']
                    return JsonResponse({'status': True, 'data': f'删除完成，共 {total_deleted} 篇'})
                except Exception:
                    return JsonResponse({'status': False, 'data': _('操作未被授权')})
            else:
                return JsonResponse({'status': False, 'data': _('操作类型不正确')})

        else:
            return JsonResponse({'status':False,'data':_('请求参数不正确')})
    except Exception as e:
        logger.exception("删除文档时发生异常")
        return JsonResponse({'status':False,'data':_('无法处理该请求')})


# 检查文档子文档数量（删除前确认）
@login_required()
@require_GET
def get_document_children_count(request, doc_id):
    """返回某文档的直接和间接子文档数量，用于分级删除确认。"""
    try:
        doc = Doc.objects.only('id', 'name').get(pk=doc_id)
    except Doc.DoesNotExist:
        return JsonResponse({'status': False, 'data': _('文档不存在')})
    from backend.apps.doc.services import DocService
    children = DocService._get_all_descendant_ids(doc_id)
    # 一级子文档
    direct_children = Doc.objects.filter(parent_doc=doc_id, is_deleted=False).values_list('id', 'name')[:20]
    return JsonResponse({
        'status': True,
        'total_children': len(children),
        'direct_children': [{'id': c[0], 'name': c[1]} for c in direct_children],
        'has_children': len(children) > 0,
    })


# 恢复已删除文档
@login_required()
@require_POST
def restore_deleted_document(request):
    """恢复已删除文档（仅系统管理员可在管理后台操作）。"""
    if not request.user.is_superuser:
        return JsonResponse({'status': False, 'data': _('仅系统管理员可恢复文档')})
    doc_id = request.POST.get('doc_id', '').strip()
    if not doc_id:
        return JsonResponse({'status': False, 'data': _('请求参数不正确')})
    from backend.apps.doc.services import DocService
    result = DocService.restore(int(doc_id))
    if 'error' in result:
        return JsonResponse({'status': False, 'data': result['error']})
    return JsonResponse({'status': True, 'data': _('恢复成功'), 'restored': result['restored']})


# 图形验证码生成
@require_GET
def graphic_verify_code(request):
    """生成删除确认用图形验证码。"""
    import io
    import random
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
    except ImportError:
        return JsonResponse({'status': False, 'data': _('服务器未安装验证码依赖')})

    # 生成 4 位随机数字
    code = ''.join(str(random.randint(1, 9)) for _ in range(4))
    request.session['DeleteCode'] = code

    # 使用不同字体大小，先画大号虚化文字再画清晰文字
    width, height = 160, 60
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # 背景噪点
    for _ in range(int(width * height * 0.02)):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        draw.point((x, y), fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)))

    # 绘制文字
    for i, ch in enumerate(code):
        x = 20 + i * 35 + random.randint(-5, 5)
        y = random.randint(8, 18)
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except Exception:
            font = ImageFont.load_default()
        # 阴影层
        draw.text((x + 1, y + 1), ch, font=font, fill=(150, 150, 150))
        # 文字层
        draw.text((x, y), ch, font=font, fill=(random.randint(0, 100), random.randint(50, 180), random.randint(0, 150)))

    # 干扰线
    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)), width=1)

    # 模糊处理
    image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

    buf = io.BytesIO()
    image.save(buf, format='PNG')
    buf.seek(0)
    return HttpResponse(buf.read(), content_type='image/png')


# 校验删除验证码
@require_POST
def verify_delete_code(request):
    """校验删除确认验证码。"""
    code = request.POST.get('code', '').strip()
    if not code:
        return JsonResponse({'status': False, 'data': _('请输入验证码')})
    session_code = request.session.get('DeleteCode', '')
    if code.lower() == session_code.lower():
        request.session['DeleteCode'] = ''
        request.session['DeleteCodeVerified'] = True
        return JsonResponse({'status': True, 'data': _('验证通过')})
    return JsonResponse({'status': False, 'data': _('验证码校验未通过')})


# 管理文档
@login_required()
@require_http_methods(['GET','POST'])
def manage_doc(request):
    if request.method == 'GET':
        # 文档数量
        # 已发布文档数量
        published_doc_cnt = Doc.objects.filter(create_user=request.user, status=1).count()
        # 草稿文档数量
        draft_doc_cnt = Doc.objects.filter(create_user=request.user, status=0).count()
        # 回收站文档数量
        recycle_doc_cnt = Doc.objects.filter(create_user=request.user, is_deleted=True).count()
        # 所有文档数量
        all_cnt = published_doc_cnt + draft_doc_cnt + recycle_doc_cnt
        # 文档列表（非删除状态）
        doc_list = Doc.objects.filter(create_user=request.user, is_deleted=False).order_by('-modify_time')
        paginator = Paginator(doc_list, 20)
        page = request.GET.get('page', 1)
        try:
            docs = paginator.page(page)
        except:
            docs = paginator.page(1)
        breadcrumb_items = [{"name": _('我的文档'), 'url': ''}]
        return render(request,'app_doc/manage/document_list.html',locals())
    else:
        kw = request.POST.get('kw', '')
        project = request.POST.get('project','')
        status = request.POST.get('status','')
        if status == '-1': # 全部文档
            q_status = [0,1]
        elif status in ['0','1']:
            q_status = [int(status)]
        else:
            q_status = [0, 1]

        page = request.POST.get('page', 1)
        limit = request.POST.get('limit', 10)
        # 没有搜索
        if kw == '':
            doc_list = Doc.objects.filter(
                create_user=request.user,
                status__in=q_status,
            ).order_by('-modify_time')
        # 有搜索
        else:
            doc_list = Doc.objects.filter(
                Q(content__icontains=kw) | Q(name__icontains=kw),
                create_user=request.user,status__in=q_status
            ).order_by('-modify_time')

        # 文档数量
        # 已发布文档数量
        published_doc_cnt = Doc.objects.filter(create_user=request.user, status=1).count()
        # 草稿文档数量
        draft_doc_cnt = Doc.objects.filter(create_user=request.user, status=0).count()
        # 所有文档数量
        all_cnt = published_doc_cnt + draft_doc_cnt

        # 分页处理
        paginator = Paginator(doc_list, limit)
        page = request.GET.get('page', page)
        try:
            docs = paginator.page(page)
        except PageNotAnInteger:
            docs = paginator.page(1)
        except EmptyPage:
            docs = paginator.page(paginator.num_pages)

        table_data = []
        for doc in docs:
            item = {
                'id': doc.id,
                'name': doc.name,
                'parent': Doc.objects.get(id=doc.parent_doc).name if doc.parent_doc and doc.parent_doc != 0 else '--',
                'project_id': doc.top_doc,
                'project_name': '--',
                'status':doc.status,
                'editor_mode':doc.editor_mode,
                'open_children':doc.open_children,
                'create_time': doc.create_time,
                'modify_time': doc.modify_time
            }
            table_data.append(item)
        resp_data = {
            "code": 0,
            "msg": "ok",
            "count": doc_list.count(),
            "data": _sanitize_json(table_data)
        }
        return JsonResponse(resp_data)


# 移动文档
@login_required()
@require_http_methods(['POST'])
def relocate_document(request):
    doc_id = request.POST.get('doc_id','') # 文档ID
    pro_id = request.POST.get('pro_id','') # 移动的文集ID
    move_type = request.POST.get('move_type','') # 移动的类型 0复制 1移动 2连同下级文档移动
    parent_id = request.POST.get('parent_id',0)
    # 判断源文档是否存在且有操作权限
    try:
        doc = Doc.objects.get(id=int(doc_id), status=1) # 查询源文档
        # v1.0: 使用 PermissionService 检查权限
        from backend.apps.doc.services import PermissionService, DocService
        effective_perm = PermissionService.get_effective_permission(request.user, doc)
        if (doc.create_user != request.user) and \
                (effective_perm not in ('edit', 'admin')) and \
                not request.user.is_superuser:
            return JsonResponse({'status':False,'data':_("无权操作文档")})
    except ObjectDoesNotExist:
        return JsonResponse({'status':False,'data':_('文档不存在')})
    # 判断上级文档是否存在
    # 跨文集移动时，目标父文档的 top_doc 可能与源文档的 pro_id 不同
    # 此时使用目标父文档的 top_doc 作为新的文集 ID
    try:
        if parent_id != '0':
            parent = Doc.objects.get(id=int(parent_id), status=1)
            if parent.top_doc != int(pro_id):
                pro_id = str(parent.top_doc)
    except ObjectDoesNotExist:
        return JsonResponse({'status':False,'data':_('上级文档不存在')})
    # 防循环引用：目标不能是源文档的子孙（仅移动操作）
    if move_type in ('1', '3') and parent_id != '0':
        if int(parent_id) == int(doc_id):
            return JsonResponse({'status':False,'data':_('不能将文档移动到自身下')})
        if int(parent_id) in DocService._get_all_descendant_ids(int(doc_id)):
            return JsonResponse({'status':False,'data':_('不能将文档移动到自身或子孙文档下')})
    # 复制文档
    if move_type == '3':
        # 拖拽排序：更新 sort 字段，仅同级内 reorder
        from django.db import transaction as db_transaction
        new_index = int(request.POST.get('new_index', 0))
        new_parent_id = int(request.POST.get('new_parent_id', parent_id))
        try:
            # 如果换了父级（与数据库中的当前 parent_doc 比较，而非前端传来的 parent_id）
            if (doc.parent_doc or 0) != new_parent_id:
                Doc.objects.filter(id=int(doc_id)).update(
                    parent_doc=new_parent_id,
                    top_doc=int(pro_id),
                    sort=new_index
                )
            # 更新同级其他文档的排序
            siblings = Doc.objects.filter(
                top_doc=int(pro_id), parent_doc=new_parent_id, status=1
            ).exclude(id=int(doc_id)).order_by('sort')
            gap = 10
            for i, sib in enumerate(siblings):
                pos = gap * (i + 1)
                if i >= new_index:
                    pos += gap
                sib.sort = pos
                sib.save(update_fields=['sort'])
            # 确保拖拽文档的 sort 正确
            Doc.objects.filter(id=int(doc_id)).update(sort=gap * (new_index + 1))
            return JsonResponse({'status': True, 'data': {'pro_id': pro_id, 'doc_id': doc_id}})
        except Exception:
            logger.exception("拖拽排序异常")
            return JsonResponse({'status': False, 'data': '排序失败'})
    elif move_type == '0':
        copy_doc = Doc.objects.create(
            name = doc.name,
            pre_content = doc.pre_content,
            content = doc.content,
            parent_doc = parent_id,
            top_doc = int(pro_id),
            editor_mode = doc.editor_mode,
            create_user = request.user,
            create_time = datetime.datetime.now(),
            modify_time = datetime.datetime.now(),
            # 文档状态说明：0表示草稿状态，1表示发布状态
            status = doc.status
        )
        return JsonResponse({'status':True,'data':{'pro_id':pro_id,'doc_id':copy_doc.id}})
    # 移动文档，下级文档更改到根目录
    elif move_type == '1':
        try:
            # 修改文档的所属文集和上级文档实现移动文档
            Doc.objects.filter(id=int(doc_id)).update(parent_doc=int(parent_id),top_doc=int(pro_id))
            # 修改其子文档为顶级文档
            Doc.objects.filter(parent_doc=doc_id).update(parent_doc=0)
            # 通知文档创建者
            if doc.create_user != request.user:
                from backend.apps.doc.services import NotificationService
                NotificationService.send(
                    recipient=doc.create_user, notification_type='doc_change',
                    title=f'文档《{doc.name}》被移动',
                    sender=request.user, send_email=True,
                    body=f'{request.user.first_name or request.user.username} 移动了你的文档《{doc.name}》',
                    link=f'/pages/{doc_id}/',
                    context={'doc_name': doc.name, 'change_type': '移动'},
                )
            return JsonResponse({'status':True,'data':{'pro_id':pro_id,'doc_id':doc_id}})
        except:
            logger.exception("移动文档时发生异常")
            return JsonResponse({'status':False,'data':_('文档移动未成功')})
    # 包含下级文档一起移动
    elif move_type == '2':
        try:
            # 修改文档的所属文集和上级文档实现移动文档
            Doc.objects.filter(id=int(doc_id)).update(parent_doc=int(parent_id), top_doc=int(pro_id))
            # 修改其子文档的文集归属
            child_doc = Doc.objects.filter(parent_doc=doc_id)
            child_doc.update(top_doc=int(pro_id))
            # 遍历子文档，如果其存在下级文档，那么继续修改所属文集
            for child in child_doc:
                Doc.objects.filter(parent_doc=child.id).update(top_doc=int(pro_id))
            # 通知文档创建者
            if doc.create_user != request.user:
                from backend.apps.doc.services import NotificationService
                NotificationService.send(
                    recipient=doc.create_user, notification_type='doc_change',
                    title=f'文档《{doc.name}》被移动',
                    sender=request.user, send_email=True,
                    body=f'{request.user.first_name or request.user.username} 移动了你的文档《{doc.name}》（含子文档）',
                    link=f'/pages/{doc_id}/',
                    context={'doc_name': doc.name, 'change_type': '移动'},
                )
            return JsonResponse({'status': True, 'data':{'pro_id':pro_id,'doc_id':doc_id}})
        except:
            logger.exception("移动包含下级的文档时发生异常")
            return JsonResponse({'status': False, 'data': _('文档移动未成功')})
    else:
        return JsonResponse({'status':False,'data':_('移动操作类别不正确')})


# RESTful 文档移动/排序 API (PRD §5.5)
@login_required()
@require_POST
def api_doc_move(request, doc_id):
    """POST /api/docs/<id>/move/
    Body: {parent_id: int|null, position: int}
    parent_id=0 表示移到顶层，parent_id=null 表示仅排序。
    """
    import json as _json
    from backend.apps.doc.services import PermissionService, DocService

    try:
        data = _json.loads(request.body)
    except _json.JSONDecodeError:
        return JsonResponse({'status': False, 'data': '请求体格式错误'})

    parent_id = data.get('parent_id')
    position = data.get('position', 0)

    if parent_id is None:
        return JsonResponse({'status': False, 'data': 'parent_id 不能为空'})

    # 权限校验：操作者需对源文档有 edit 及以上权限
    try:
        doc = Doc.objects.get(id=doc_id, is_deleted=False)
    except Doc.DoesNotExist:
        return JsonResponse({'status': False, 'data': '文档不存在'})

    effective_perm = PermissionService.get_effective_permission(request.user, doc)
    if effective_perm not in ('edit', 'admin') and doc.create_user != request.user and not request.user.is_superuser:
        return JsonResponse({'status': False, 'data': '无权移动此文档'})

    # 目标父文档权限校验
    if parent_id and int(parent_id) != 0:
        try:
            target = Doc.objects.get(id=parent_id, is_deleted=False)
        except Doc.DoesNotExist:
            return JsonResponse({'status': False, 'data': '目标父文档不存在'})
        target_perm = PermissionService.get_effective_permission(request.user, target)
        if target_perm not in ('edit', 'admin') and target.create_user != request.user and not request.user.is_superuser:
            return JsonResponse({'status': False, 'data': '无权移动到此父文档'})

    result = DocService.move(doc_id, parent_id, position)
    if 'error' in result:
        return JsonResponse({'status': False, 'data': result['error']})
    return JsonResponse({'status': True, 'data': result})


# 查看对比文档历史版本
@login_required()
@require_http_methods(['GET',"POST"])
def compare_document_history(request,doc_id,his_id):
    if request.method == 'GET':
        try:
            doc = Doc.objects.get(id=doc_id)  # 查询文档信息
            # v1.0: 使用 PermissionService 检查权限
            from backend.apps.doc.services import PermissionService
            effective_perm = PermissionService.get_effective_permission(request.user, doc)
            if (request.user == doc.create_user) or (effective_perm in ('edit', 'admin')) or (request.user.is_superuser):
                history = DocHistory.objects.get(id=his_id)
                history_list = DocHistory.objects.filter(doc=doc).order_by('-create_time')
                if history.doc == doc:
                    return render(request, 'app_doc/diff_doc.html', locals())
                else:
                    return render(request, '403.html')
            else:
                return render(request, '403.html')
        except Exception as e:
            logger.exception("文档历史版本页面访问异常")
            return render(request, '404.html')

    elif request.method == 'POST':
        try:
            doc = Doc.objects.get(id=doc_id)  # 查询文档信息
            # v1.0: 使用 PermissionService 检查权限
            from backend.apps.doc.services import PermissionService
            effective_perm = PermissionService.get_effective_permission(request.user, doc)
            if (request.user == doc.create_user) or (effective_perm in ('edit', 'admin')) or (request.user.is_superuser):
                history = DocHistory.objects.get(id=his_id)
                if history.doc == doc:
                    return JsonResponse({'status':True,'data':history.pre_content})
                else:
                    return JsonResponse({'status': False, 'data': _('操作未被授权')})
            else:
                return JsonResponse({'status':False,'data':_('操作未被授权')})
        except Exception as e:
            logger.exception("文档历史版本获取异常")
            return JsonResponse({'status':False,'data':_('数据获取失败')})


# 管理文档历史版本
@login_required()
@require_http_methods(['GET',"POST"])
def manage_doc_history(request,doc_id):
    if request.method == 'GET':
        try:
            doc = Doc.objects.get(id=doc_id,create_user=request.user)
            history_list = DocHistory.objects.filter(create_user=request.user,doc=doc_id).order_by('-create_time')
            paginator = Paginator(history_list, 15)
            page = request.GET.get('page', 1)
            try:
                historys = paginator.page(page)
            except PageNotAnInteger:
                historys = paginator.page(1)
            except EmptyPage:
                historys = paginator.page(paginator.num_pages)
            return render(request, 'app_doc/manage/document_history.html', locals())
        except Exception as e:
            logger.exception("管理文档历史版本页面访问异常")
            return render(request, '404.html')
    elif request.method == 'POST':
        try:
            history_id = request.POST.get('history_id','')
            DocHistory.objects.filter(id=history_id,doc=doc_id,create_user=request.user).delete()
            return JsonResponse({'status':True,'data':_('删除成功')})
        except:
            logger.exception("文档历史版本操作异常")
            return JsonResponse({'status':False,'data':_('服务器内部错误')})


# 文档回收站
@login_required()
@require_http_methods(['GET','POST'])
def doc_recycle(request):
    if request.method == 'GET':
        # v1.0: 获取软删除的文档
        doc_list = Doc.objects.filter(is_deleted=True, deleted_by=request.user).order_by('-deleted_at')
        # 分页处理
        paginator = Paginator(doc_list, 15)
        page = request.GET.get('page', 1)
        try:
            docs = paginator.page(page)
        except PageNotAnInteger:
            docs = paginator.page(1)
        except EmptyPage:
            docs = paginator.page(paginator.num_pages)
        breadcrumb_items = [{"name": _('文档回收站'), 'url': ''}]
        return render(request,'app_doc/manage/document_recycle.html',locals())
    elif request.method == 'POST':
        try:
            # 获取参数
            doc_id = request.POST.get('doc_id', None) # 文档ID
            types = request.POST.get('type',None) # 操作类型
            if doc_id:
                # 查询文档
                try:
                    doc = Doc.objects.get(id=doc_id)
                except ObjectDoesNotExist:
                    return JsonResponse({'status': False, 'data': _('文档不存在')})
                # v1.0: 文档创建者 或 有 admin 权限 才可以操作
                from backend.apps.doc.services import PermissionService
                effective_perm = PermissionService.get_effective_permission(request.user, doc)
                if (request.user == doc.create_user) or (effective_perm == 'admin') or request.user.is_superuser:
                    # 还原文档 (v1.0 使用 DocService)
                    if types == 'restore':
                        from backend.apps.doc.services import DocService
                        result = DocService.restore(int(doc_id))
                        if 'error' in result:
                            return JsonResponse({'status': False, 'data': result['error']})
                    # 永久删除文档
                    elif types == 'del':
                        DocHistory.objects.filter(doc=doc).delete()
                        DocShare.objects.filter(doc=doc).delete()
                        DocTag.objects.filter(doc=doc).delete()
                        doc.delete()
                    else:
                        return JsonResponse({'status':False,'data':_('无效请求')})
                    return JsonResponse({'status': True, 'data': _('操作完成')})
                else:
                    return JsonResponse({'status': False, 'data': _('操作未被授权')})
            # 清空回收站 (v1.0: is_deleted=True)
            elif types == 'empty':
                docs = Doc.objects.filter(is_deleted=True, deleted_by=request.user)
                for doc_item in docs:
                    DocHistory.objects.filter(doc=doc_item).delete()
                    DocShare.objects.filter(doc=doc_item).delete()
                    DocTag.objects.filter(doc=doc_item).delete()
                docs.delete()
                return JsonResponse({'status': True, 'data': _('清空成功')})
            # 还原回收站全部 (v1.0 使用 DocService)
            elif types == 'restoreAll':
                from backend.apps.doc.services import DocService
                all_deleted = Doc.objects.filter(is_deleted=True, deleted_by=request.user).values_list('id', flat=True)
                restored = 0
                for did in all_deleted:
                    result = DocService.restore(did)
                    if 'error' not in result:
                        restored += result.get('restored', 0)
                return JsonResponse({'status': True, 'data': f'已还原 {restored} 篇文档'})
            else:
                return JsonResponse({'status': False, 'data': _('请求参数不正确')})
        except Exception as e:
            logger.exception("文档回收处理异常")
            return JsonResponse({'status': False, 'data': _('无法处理该请求')})


# 一键发布文档
@login_required()
@require_http_methods(['POST'])
def quick_publish_document(request):
    doc_id = request.POST.get('doc_id',None)
    # 查询文档
    try:
        doc = Doc.objects.get(id=doc_id)
    except ObjectDoesNotExist:
        return JsonResponse({'status': False, 'data': _('文档不存在')})
    # v1.0: 文档创建者 或 有 edit/admin 权限 可以发布
    from backend.apps.doc.services import PermissionService
    effective_perm = PermissionService.get_effective_permission(request.user, doc)
    if (request.user == doc.create_user) or (effective_perm in ('edit', 'admin')) or request.user.is_superuser:
        try:
            doc.status = 1
            doc.modify_time = datetime.datetime.now()
            # 发布时去除草稿标题前缀
            draft_prefix = str(_('【预览草稿】'))
            if doc.name.startswith(draft_prefix):
                doc.name = doc.name[len(draft_prefix):]
            doc.save()
            return JsonResponse({'status':True,'data':_('发布成功')})
        except:
            logger.exception("文档快速发布异常")
            return JsonResponse({'status':False,'data':_('文档发布未成功')})
    else:
        return JsonResponse({'status':False,'data':_('操作未被授权')})


# 私密文档分享
@require_http_methods(['GET','POST'])
def share_document(request):
    if request.method == 'GET':
        share_token = request.GET.get('token')
        # 判断是否存在分享
        try:
            share_doc = DocShare.objects.get(token=share_token,is_enable=True)
            doc = share_doc.doc
            # 公开分享
            if share_doc.share_type == 0:
                return render(request, 'app_doc/share/shared_link_create.html', locals())
            # 私密分享
            else:
                doc_id_base64 = base64.standard_b64encode(str(share_doc.doc.id).encode())
                # 不存在公开分享的文档，则判断验证分享码
                share_cookie_name = 'sharedoc-{}'.format(share_token)
                share_value = request.COOKIES.get(share_cookie_name) if share_cookie_name in request.COOKIES.keys() else 0
                if share_doc.share_value == share_value:
                    return render(request, 'app_doc/share/shared_link_create.html', locals())
                else:
                    share_pwd = request.GET.get('pwd', '')
                    return redirect('/share_doc_check/?surl={}&pwd={}'.format(share_token, share_pwd))
        except ObjectDoesNotExist:
            return render(request,'404.html')
    elif request.method == 'POST':
        doc_id = request.POST.get('doc_id') or request.POST.get('id')
        action = request.POST.get('action', '')
        try:
            # 获取请求参数
            doc = Doc.objects.get(id=doc_id)
            from backend.apps.doc.services import PermissionService
            effective_perm = PermissionService.get_effective_permission(request.user, doc)
            if effective_perm not in ('edit', 'admin') and doc.create_user != request.user:
                return JsonResponse({'status': False, 'data': _('无操作权限')})

            # 撤销分享
            if action == 'cancel':
                DocShare.objects.filter(doc=doc, is_enable=True).update(is_enable=False)
                return JsonResponse({'status': True, 'data': 'cancelled'})

            share_type = request.POST.get('share_type', 0)
            share_value = request.POST.get('share_pwd') or request.POST.get('share_value', 0)
            is_enable = request.POST.get('is_enable', True)
            if is_enable == 'false':
                is_enable = False
            else:
                is_enable = True
            # 生成分享文档Token
            share_token = hashlib.md5()
            share_token.update("{}_{}".format(doc_id,request.user.username).encode())
            share_token = share_token.hexdigest()
            # 创建或更新分享信息
            doc_share = DocShare.objects.update_or_create(
                token=share_token,
                defaults={'doc': doc,
                          'share_type': share_type,
                          'share_value':share_value,
                          'is_enable':is_enable
                          }
            )
            if int(share_type) == 0:
                data = {
                    'doc':share_token
                }
            else:
                data = {
                    'doc': share_token,
                    'share_value':share_value
                }
            return JsonResponse({'status':True,'data':data})
        except ObjectDoesNotExist:
            return JsonResponse({'status':False,'data':_('文档不存在')})


# 验证文档分享码
def share_doc_check(request):
    doc_token = request.GET.get('surl', '')
    if request.method == 'GET':
        if doc_token != '':
            doc_share = DocShare.objects.get(token=doc_token)
            share_cookie_name = 'sharedoc-{}'.format(doc_token)
            share_value = request.COOKIES.get(share_cookie_name) if share_cookie_name in request.COOKIES.keys() else 0
            if doc_share.share_value == share_value:
                return redirect("/share_doc/?token={}".format(doc_token))
            else:
                return render(request,'app_doc/share/shared_link_verify.html',locals())
        else:
            return render(request,'404.html')
    else:
        # 接收参数值
        share_value = request.POST.get('share_value','')
        # 查询数据
        if DocShare.objects.filter(token=doc_token,share_type=1,share_value=share_value).exists():
            obj = redirect("/share_doc/?token={}".format(doc_token))
            obj.set_cookie('sharedoc-{}'.format(doc_token),share_value)
            return obj
        else:
            errormsg = _("分享访问口令错误")
            return render(request, 'app_doc/share/shared_link_verify.html', locals())


# 管理文档分享
@login_required()
@require_http_methods(['GET','POST'])
def manage_doc_share(request):
    if request.method == 'GET':
        # 获取用户的分享列表
        share_query = DocShare.objects.filter(doc__create_user=request.user).order_by('-create_time')
        paginator = Paginator(share_query, 15)
        page = request.GET.get('page', 1)
        try:
            shares = paginator.page(page)
        except PageNotAnInteger:
            shares = paginator.page(1)
        except EmptyPage:
            shares = paginator.page(paginator.num_pages)
        # 获取用户可分享的文档列表（用于创建分享）
        user_docs = Doc.objects.filter(create_user=request.user, status=1).order_by('name')
        query_string = request.GET.urlencode()
        breadcrumb_items = [{"name": _('分享管理'), 'url': ''}]
        return render(request, 'app_doc/manage/shared_links.html', locals())
    else:
        types = request.POST.get('type')
        # 请求类型 1：获取列表 2：删除 3：修改
        if types == '1':
            page = request.POST.get('page', 1)
            limit = request.POST.get('limit', 10)
            # share_doc = DocShare.objects.filter(doc__create_user=request.user).order_by('-create_time')
            docshare_list = DocShare.objects.filter(doc__create_user=request.user).order_by('-create_time')
            paginator = Paginator(docshare_list, limit)
            page = request.GET.get('page', page)
            try:
                docshares = paginator.page(page)
            except PageNotAnInteger:
                docshares = paginator.page(1)
            except EmptyPage:
                docshares = paginator.page(paginator.num_pages)
            share_list = []
            for doc in docshares:
                item = {
                    'token':doc.token,
                    'doc_name':doc.doc.name,
                    'share_type':doc.share_type,
                    'share_value':doc.share_value,
                    'share_status':doc.is_enable,
                    'create_time':doc.create_time
                }
                share_list.append(item)
            resp_data = {
                "code":0,
                "msg":"ok",
                "count":docshare_list.count(),
                "data":share_list
            }
            return JsonResponse(resp_data)
        # 删除
        elif types == '2':
            range = request.POST.get("range")
            token = request.POST.get("token")
            if range == 'single':
                try:
                    share = DocShare.objects.get(token=token,doc__create_user=request.user)
                    share.delete()
                    return JsonResponse({'status':True,'data':'ok'})
                except:
                    return JsonResponse({'status':False,'data':_('无指定内容')})
            elif range == "multi":
                tokens = token.split(",")
                try:
                    share = DocShare.objects.filter(token__in=tokens,doc__create_user=request.user)
                    share.delete()
                    return JsonResponse({'status':True,'data':'ok'})
                except:
                    return JsonResponse({'status':False,'data':_('无指定内容')})
            else:
                return JsonResponse({'status':False,'data':_('操作类型不正确')})
        # 修改
        elif types == '3':
            token = request.POST.get("token",'')
            name = request.POST.get('key','')
            value = request.POST.get('value','')
            # 修改分享状态
            if name == 'share_status':
                is_enable = True if value == 'true' else False
                DocShare.objects.filter(token=token).update(is_enable=is_enable)
            # 修改分享类型
            elif name == 'share_type':
                share_type = 0 if value == '0' else 1
                DocShare.objects.filter(token=token).update(share_type=share_type)
            else:
                return JsonResponse({'status':False,'data':_('请求参数不正确')})
            return JsonResponse({'status':True,'data':'ok'})
        # 创建分享
        elif types == '4':
            doc_id = request.POST.get('doc_id', '')
            share_type = request.POST.get('share_type', '0')
            share_value = request.POST.get('share_value', '')
            try:
                doc = Doc.objects.get(id=doc_id, create_user=request.user)
                share_token = hashlib.md5()
                share_token.update("{}_{}".format(doc_id, request.user.username).encode())
                share_token = share_token.hexdigest()
                DocShare.objects.update_or_create(
                    token=share_token,
                    defaults={
                        'doc': doc,
                        'share_type': int(share_type),
                        'share_value': share_value,
                        'is_enable': True
                    }
                )
                return JsonResponse({'status': True, 'data': {
                    'token': share_token,
                    'share_type': int(share_type),
                    'share_value': share_value
                }})
            except Doc.DoesNotExist:
                return JsonResponse({'status': False, 'data': _('文档不存在')})
        # 修改分享码
        elif types == '5':
            token = request.POST.get('token', '')
            share_value = request.POST.get('share_value', '')
            try:
                share = DocShare.objects.get(token=token, doc__create_user=request.user)
                share.share_value = share_value
                share.save()
                return JsonResponse({'status': True, 'data': 'ok'})
            except DocShare.DoesNotExist:
                return JsonResponse({'status': False, 'data': _('分享不存在')})
        else:
            return JsonResponse({'status': False, 'data': _('操作类型不正确')})


# 创建文档模板
@login_required()
@require_POST
def create_content_template(request):
    try:
        name = request.POST.get('name','')
        content = request.POST.get('content','')
        if name != '':
            doctemp = DocTemp.objects.create(
                name = name,
                content = content,
                create_user=request.user
            )
            doctemp.save()
            return JsonResponse({'status':True,'data':doctemp.id})
        else:
            return JsonResponse({'status':False,'data':_('模板标题不能为空')})
    except Exception as e:
        logger.exception("文档模板操作异常")
        return JsonResponse({'status':False,'data':_('无法处理该请求')})


# 修改文档模板
@login_required()
@require_POST
def edit_content_template(request):
    try:
        doctemp_id = request.POST.get('doctemp_id','')
        name = request.POST.get('name','')
        content = request.POST.get('content','')
        if doctemp_id != '' and name !='':
            doctemp = DocTemp.objects.get(id=doctemp_id)
            if request.user.id == doctemp.create_user.id:
                doctemp.name = name
                doctemp.content = content
                doctemp.save()
                return JsonResponse({'status':True,'data':_('修改成功')})
            else:
                return JsonResponse({'status':False,'data':_('没有操作权限')})
        else:
            return JsonResponse({'status':False,'data':_('请求参数不正确')})
    except Exception as e:
        logger.exception("文档模板修改异常")
        return JsonResponse({'status':False,'data':_('无法处理该请求')})


# 删除文档模板
@login_required()
def delete_content_template(request):
    try:
        doctemp_id = request.POST.get('doctemp_id','')
        if doctemp_id != '':
            doctemp = DocTemp.objects.get(id=doctemp_id)
            if request.user.id == doctemp.create_user.id:
                doctemp.delete()
                return JsonResponse({'status':True,'data':_('删除完成')})
            else:
                return JsonResponse({'status':False,'data':_('操作未被授权')})
        else:
            return JsonResponse({'status': False, 'data': _('请求参数不正确')})
    except Exception as e:
        logger.exception("文档模板删除异常")
        return JsonResponse({'status':False,'data':_('无法处理该请求')})


# 管理文档模板
@login_required()
@require_http_methods(['GET'])
def manage_doctemp(request):
    try:
        search_kw = request.GET.get('kw', None)
        if search_kw:
            doctemp_list = DocTemp.objects.filter(
                create_user=request.user,
                content__icontains=search_kw
            ).order_by('-modify_time')
            paginator = Paginator(doctemp_list, 10)
            page = request.GET.get('page', 1)
            try:
                doctemps = paginator.page(page)
            except PageNotAnInteger:
                doctemps = paginator.page(1)
            except EmptyPage:
                doctemps = paginator.page(paginator.num_pages)
            doctemps.kw = search_kw
        else:
            doctemp_list = DocTemp.objects.filter(create_user=request.user).order_by('-modify_time')
            paginator = Paginator(doctemp_list, 10)
            page = request.GET.get('page', 1)
            try:
                doctemps = paginator.page(page)
            except PageNotAnInteger:
                doctemps = paginator.page(1)
            except EmptyPage:
                doctemps = paginator.page(paginator.num_pages)
        breadcrumb_items = [{"name": _('文档模板'), 'url': ''}]
        return render(request, 'app_doc/manage/content_templates.html', locals())
    except Exception as e:
        logger.exception(_("管理文档模板页面访问出错"))
        return render(request, '404.html')


# 获取指定文档模板
@login_required()
@require_http_methods(["POST"])
def fetch_content_template(request):
    try:
        doctemp_id = request.POST.get('doctemp_id','')
        if doctemp_id != '':
            content = DocTemp.objects.get(id=int(doctemp_id)).serializable_value('content')
            return JsonResponse({'status':True,'data':content})
        else:
            return JsonResponse({'status':False,'data':_('请求参数不正确')})
    except Exception as e:
        logger.exception(_("获取指定文档模板出错"))
        return JsonResponse({'status':False,'data':_('无法处理该请求')})


# 图片素材管理
@login_required()
@require_http_methods(['GET',"POST"])
def manage_image(request):
    # 获取图片
    if request.method == 'GET':
        try:
            groups = ImageGroup.objects.filter(user=request.user) # 获取所有分组
            all_img_cnt = Image.objects.filter(user=request.user).count()
            no_group_cnt = Image.objects.filter(user=request.user,group_id=None).count() # 获取所有未分组的图片数量
            g_id = int(request.GET.get('group', 0))  # 图片分组id
            kw = request.GET.get('kw', '').strip()  # 搜索关键词
            if int(g_id) == 0:
                image_list = Image.objects.filter(user=request.user).order_by('-create_time')  # 查询所有图片
            elif int(g_id) == -1:
                image_list = Image.objects.filter(user=request.user,group_id=None).order_by('-create_time')  # 查询未分组的图片
            else:
                image_list = Image.objects.filter(user=request.user,group_id=g_id).order_by('-create_time')  # 查询指定分组的图片
            if kw:
                image_list = image_list.filter(file_name__icontains=kw)
            paginator = Paginator(image_list, 18)
            page = request.GET.get('page', 1)
            try:
                images = paginator.page(page)
            except PageNotAnInteger:
                images = paginator.page(1)
            except EmptyPage:
                images = paginator.page(paginator.num_pages)
            images.group = g_id
            breadcrumb_items = [{"name": _('图片管理'), 'url': ''}]
            return render(request,'app_doc/manage/image_library.html',locals())
        except:
            logger.exception(_("图片素材管理出错"))
            return render(request,'404.html')
    elif request.method == 'POST':
        try:
            img_id = request.POST.get('img_id','')
            types = request.POST.get('types','') # 操作类型：0表示删除，1表示修改，2表示获取
            range = request.POST.get('range','single') # 操作范围 single 表示单个图片，multi表示多个图片
            # 删除图片
            if int(types) == 0:
                if range == 'single':
                    img = Image.objects.get(id=img_id)
                    if img.user != request.user:
                        return JsonResponse({'status': False, 'data': _('未授权请求')})
                    file_path = settings.BASE_DIR+img.file_path
                    is_exist = os.path.exists(file_path)
                    if is_exist:
                        os.remove(file_path)
                    img.delete() # 删除记录
                elif range == 'multi':
                    imgs = img_id.split(',')
                    for i in imgs:
                        img = Image.objects.get(id=i)
                        if img.user != request.user:
                            logger.error(_("图片{}非法删除".format(i)))
                            break
                        file_path = settings.BASE_DIR + img.file_path
                        is_exist = os.path.exists(file_path)
                        if is_exist:
                            os.remove(file_path)
                        img.delete()  # 删除记录

                return JsonResponse({'status':True,'data':_('删除完成')})
            # 移动图片分组
            elif int(types) == 1:
                if range == 'single':
                    group_id = request.POST.get('group_id',None)
                    if group_id is None:
                        Image.objects.filter(id=img_id,user=request.user).update(group_id=None)
                    else:
                        group = ImageGroup.objects.get(id=group_id,user=request.user)
                        Image.objects.filter(id=img_id,user=request.user).update(group_id=group)
                elif range == 'multi':
                    imgs = img_id.split(',')
                    group_id = request.POST.get('group_id',None)
                    if group_id is None:
                        Image.objects.filter(id__in=imgs,user=request.user).update(group_id=None)
                    else:
                        group = ImageGroup.objects.get(id=group_id,user=request.user)
                        Image.objects.filter(id__in=imgs,user=request.user).update(group_id=group)

                return JsonResponse({'status':True,'data':_('移动完成')})
            # 获取图片
            elif int(types) == 2:
                group_id = request.POST.get('group_id', None) # 接受分组ID参数
                if group_id is None: #
                    return JsonResponse({'status':False,'data':_('请求参数不正确')})
                elif int(group_id) == 0:
                    imgs = Image.objects.filter(user=request.user).order_by('-create_time')
                elif int(group_id) == -1:
                    imgs = Image.objects.filter(user=request.user,group_id=None).order_by('-create_time')
                else:
                    imgs = Image.objects.filter(user=request.user,group_id=group_id).order_by('-create_time')
                img_list = []
                for img in imgs:
                    item = {
                        'path':img.file_path,
                        'name':img.file_name,
                    }
                    img_list.append(item)
                return JsonResponse({'status':True,'data':img_list})
            else:
                return JsonResponse({'status':False,'data':_('参数值无效')})
        except ObjectDoesNotExist:
            return JsonResponse({'status':False,'data':_('图片不存在')})
        except:
            logger.exception(_("操作图片素材出错"))
            return JsonResponse({'status':False,'data':_('服务器处理异常')})

# 图片分组管理
@login_required()
@require_http_methods(['GET',"POST"])
@logger.catch()
def manage_img_group(request):
    if request.method == 'GET':
        groups = ImageGroup.objects.filter(user=request.user)
        return render(request,'app_doc/manage/image_groups.html',locals())
    # 操作分组
    elif request.method == 'POST':
        types = request.POST.get('types',None) # 请求类型，0表示创建分组，1表示修改分组，2表示删除分组，3表示获取分组
        # 创建分组
        if int(types) == 0:
            group_name = escape(request.POST.get('group_name', ''))
            if group_name not in ['',_('默认分组'),_('未分组')]:
                ImageGroup.objects.get_or_create(
                    user = request.user,
                    group_name = group_name
                )
                return JsonResponse({'status':True,'data':'ok'})
        # 创建分享
        elif types == '4':
            doc_id = request.POST.get('doc_id', '')
            share_type = request.POST.get('share_type', '0')
            share_value = request.POST.get('share_value', '')
            try:
                doc = Doc.objects.get(id=doc_id, create_user=request.user)
                share_token = hashlib.md5()
                share_token.update("{}_{}".format(doc_id, request.user.username).encode())
                share_token = share_token.hexdigest()
                DocShare.objects.update_or_create(
                    token=share_token,
                    defaults={
                        'doc': doc,
                        'share_type': int(share_type),
                        'share_value': share_value,
                        'is_enable': True
                    }
                )
                return JsonResponse({'status': True, 'data': {
                    'token': share_token,
                    'share_type': int(share_type),
                    'share_value': share_value
                }})
            except Doc.DoesNotExist:
                return JsonResponse({'status': False, 'data': _('文档不存在')})
        # 修改分享码
        elif types == '5':
            token = request.POST.get('token', '')
            share_value = request.POST.get('share_value', '')
            try:
                share = DocShare.objects.get(token=token, doc__create_user=request.user)
                share.share_value = share_value
                share.save()
                return JsonResponse({'status': True, 'data': 'ok'})
            except DocShare.DoesNotExist:
                return JsonResponse({'status': False, 'data': _('分享不存在')})
            else:
                return JsonResponse({'status':False,'data':_('名称无效')})
        # 修改分组
        elif int(types) == 1:
            group_name = escape(request.POST.get("group_name",''))
            if group_name not in ['',_('默认分组'),_('未分组')]:
                group_id = request.POST.get('group_id', '')
                ImageGroup.objects.filter(id=group_id,user=request.user).update(group_name=group_name)
                return JsonResponse({'status':True,'data':_('修改成功')})
            else:
                return JsonResponse({'status':False,'data':_('名称无效')})

        # 删除分组
        elif int(types) == 2:
            try:
                group_id = request.POST.get('group_id','')
                group = ImageGroup.objects.get(id=group_id,user=request.user) # 查询分组
                images = Image.objects.filter(group_id=group_id,user=request.user).update(group_id=None) # 移动图片到未分组
                group.delete() # 删除分组
                return JsonResponse({'status':True,'data':_('删除完成')})
            except:
                logger.exception(_("删除图片分组出错"))
                return JsonResponse({'status':False,'data':_('删除操作未成功')})
        # 获取分组
        elif int(types) == 3:
            try:
                group_list = []
                all_cnt = Image.objects.filter(user=request.user).count()
                non_group_cnt = Image.objects.filter(group_id=None,user=request.user).count()
                group_list.append({'group_name':_('全部图片'),'group_cnt':all_cnt,'group_id':0})
                group_list.append({'group_name':_('未分组'),'group_cnt':non_group_cnt,'group_id':-1})
                groups = ImageGroup.objects.filter(user=request.user) # 查询所有分组
                for group in groups:
                    group_cnt = Image.objects.filter(group_id=group).count()
                    item = {
                        'group_id':group.id,
                        'group_name':group.group_name,
                        'group_cnt':group_cnt
                    }
                    group_list.append(item)
                return JsonResponse({'status':True,'data':group_list})
            except:
                logger.exception(_("获取图片分组出错"))
                return JsonResponse({'status':False,'data':_('请求处理未成功')})


# 附件管理
@login_required()
@csrf_exempt
@require_http_methods(['GET',"POST"])
def manage_attachment(request):
    # 文件大小 字节转换
    def sizeFormat(size, is_disk=False, precision=2):
        '''
        size format for human.
            byte      ---- (B)
            kilobyte  ---- (KB)
            megabyte  ---- (MB)
            gigabyte  ---- (GB)
            terabyte  ---- (TB)
            petabyte  ---- (PB)
            exabyte   ---- (EB)
            zettabyte ---- (ZB)
            yottabyte ---- (YB)
        '''
        formats = ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
        unit = 1000.0 if is_disk else 1024.0
        if not (isinstance(size, float) or isinstance(size, int)):
            raise TypeError('a float number or an integer number is required!')
        if size < 0:
            raise ValueError('number must be non-negative')
        for i in formats:
            size /= unit
            if size < unit:
                r = '{}{}'.format(round(size, precision),i)
                return r

    if request.method == 'GET':
        try:
            search_kw = request.GET.get('kw', None)
            # 搜索附件
            if search_kw:
                attachment_list = Attachment.objects.filter(
                    user=request.user,
                    file_name__icontains=search_kw
                ).order_by('-create_time')
                paginator = Paginator(attachment_list, 15)
                page = request.GET.get('page', 1)
                try:
                    attachments = paginator.page(page)
                except PageNotAnInteger:
                    attachments = paginator.page(1)
                except EmptyPage:
                    attachments = paginator.page(paginator.num_pages)
                attachments.kw = search_kw
            # 所有附件
            else:
                attachment_list = Attachment.objects.filter(user=request.user).order_by('-create_time')
                paginator = Paginator(attachment_list, 15)
                page = request.GET.get('page', 1)
                try:
                    attachments = paginator.page(page)
                except PageNotAnInteger:
                    attachments = paginator.page(1)
                except EmptyPage:
                    attachments = paginator.page(paginator.num_pages)
            breadcrumb_items = [{"name": _('附件管理'), 'url': ''}]
            return render(request, 'app_doc/manage/file_attachments.html', locals())
        except Exception as e:
            logger.exception(_("附件管理访问出错"))
            return render(request,'404.html')
    elif request.method == 'POST':
        # types参数，0表示上传、1表示删除、2表示获取附件列表
        types = request.POST.get('types','')
        if types in ['0',0]:
            attachment = request.FILES.get('attachment_upload',None)
            if attachment:
                attachment_name = attachment.name # 获取附件文件名
                attachment_size = sizeFormat(attachment.size) # 获取附件文件大小

                # 限制附件大小
                # 获取系统设置的附件文件大小，如果不存在，默认50MB
                try:
                    allow_attachment_size = SysSetting.objects.get(types='doc',name='attachment_size')
                    allow_attach_size = int(allow_attachment_size.value) * 1048576
                except Exception as e:
                    # print(repr(e))
                    allow_attach_size = 52428800
                if attachment.size > allow_attach_size:
                    return JsonResponse({'status':False,'data':_('文件大小超出限制')})

                # 限制附件格式
                if settings.CHECK_ATTACHMENT_SUFFIX:
                    try:
                        attachment_suffix_list = SysSetting.objects.get(types='doc', name='attachment_suffix')
                        attachment_suffix_list = attachment_suffix_list.value.split(',')
                        if attachment_suffix_list == ['']:
                            attachment_suffix_list = ['zip']
                    except ObjectDoesNotExist:
                        attachment_suffix_list = ['zip']
                    allow_attachment = False
                    if attachment_name.split('.')[-1].lower() in attachment_suffix_list:
                        allow_attachment = True
                else:
                    allow_attachment = True

                # 检测ZIP炸弹
                if allow_attachment and attachment_name.split('.')[-1].lower() == 'zip':
                    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                        for chunk in attachment.chunks():
                            temp_file.write(chunk)
                        temp_file_path = temp_file.name

                    if is_zip_bomb(temp_file_path):
                        os.remove(temp_file_path)
                        return JsonResponse({'code': 5, 'data': _('检测到可能的ZIP炸弹')})

                    os.remove(temp_file_path)
                    attachment.seek(0)

                if allow_attachment:
                    a = Attachment.objects.create(
                        file_name = attachment_name,
                        file_size = attachment_size,
                        file_path = attachment,
                        user = request.user
                    )
                    return JsonResponse({'status':True,'data':{'name':attachment_name,'url':a.file_path.name}})
                else:
                    return JsonResponse({'status':False,'data':_('不支持的格式')})
            else:
                return JsonResponse({'status':False,'data':_('无效文件')})
        elif types in ['1',1]:
            attach_id = request.POST.get('attach_id','')
            attachment = Attachment.objects.filter(id=attach_id,user=request.user) # 查询附件
            for a in attachment: # 遍历附件
                a.file_path.delete() # 删除文件
            attachment.delete() # 删除数据库记录
            return JsonResponse({'status':True,'data':_('删除成功')})
        elif types in [2,'2']:
            attachment_list = []
            attachments = Attachment.objects.filter(user=request.user).order_by('-create_time')
            for a in attachments:
                item = {
                    'filename':a.file_name,
                    'filesize':a.file_size,
                    'filepath':a.file_path.name,
                    'filetime':a.create_time
                }
                attachment_list.append(item)
            return JsonResponse({'status':True,'data':attachment_list})
        else:
            return JsonResponse({'status':False,'data':_('无效参数')})


# 搜索
def search(request):
    kw = request.GET.get('kw', None)
    search_type = request.GET.get('type', 'doc')  # 搜索类型，默认文档doc

    # 检查全局搜索方式配置：若设为全文搜索，重定向到 Haystack 搜索引擎
    try:
        global_search_type = SysSetting.objects.get(name='search_type')
        if global_search_type.value == '1' and kw:
            from django.http import HttpResponseRedirect
            from urllib.parse import urlencode
            params = request.GET.copy()
            params['q'] = params.get('kw', params.get('q', ''))
            if 'kw' in params:
                del params['kw']
            return HttpResponseRedirect('/search/query/?' + urlencode(params))
    except SysSetting.DoesNotExist:
        pass
    date_type = request.GET.get('d_type', 'recent')
    date_range = request.GET.get('d_range', 'all')  # 时间范围，默认不限，all
    project_range = request.GET.get('p_range', 0)  # 文集范围，默认不限，all

    # 处理时间范围
    if date_type == 'recent':
        if date_range == 'recent1':  # 最近1天
            start_date = datetime.datetime.now() - datetime.timedelta(days=1)
        elif date_range == 'recent7':  # 最近7天
            start_date = datetime.datetime.now() - datetime.timedelta(days=7)
        elif date_range == 'recent30':  # 最近30天
            start_date = datetime.datetime.now() - datetime.timedelta(days=30)
        elif date_range == 'recent365':  # 最近一年
            start_date = datetime.datetime.now() - datetime.timedelta(days=365)
        else:
            start_date = datetime.datetime.strptime('1900-01-01', '%Y-%m-%d')
        end_date = datetime.datetime.now()
    elif date_type == 'day':
        try:
            date_list = date_range.split('|')
            start_date = datetime.datetime.strptime(date_list[0], '%Y-%m-%d')
            end_date = datetime.datetime.strptime(date_list[1], '%Y-%m-%d')
        except:
            start_date = datetime.datetime.now() - datetime.timedelta(days=1)
            end_date = datetime.datetime.now()

    # 是否时间筛选
    if date_range == 'all':
        is_date_range = False
    else:
        is_date_range = True

    # 是否认证
    if request.user.is_authenticated:
        is_auth = True
    else:
        is_auth = False

    # 存在搜索关键词
    if kw:
        # 搜索文档
        if search_type == 'doc':
            if is_auth:
                # 认证用户：搜索公开文档 + 自己的文档
                data_list = Doc.objects.filter(
                    Q(is_public=True) | Q(create_user=request.user),
                    Q(create_time__gte=start_date, create_time__lte=end_date),  # 筛选创建时间
                    Q(name__icontains=kw) | Q(content__icontains=kw) | Q(pre_content__icontains=kw)  # 筛选文档标题和内容中包含搜索词
                ).order_by('-create_time')
            else:
                # 游客：仅搜索公开文档
                data_list = Doc.objects.filter(
                    Q(is_public=True),
                    Q(create_time__gte=start_date, create_time__lte=end_date),  # 筛选创建时间
                    Q(name__icontains=kw) | Q(content__icontains=kw) | Q(pre_content__icontains=kw)  # 筛选文档标题和内容中包含搜索词
                ).order_by('-create_time')

        # 搜索标签
        elif search_type == 'tag':
            # 认证用户
            if is_auth:
                # 认证用户：搜索公开文档 + 自己的文档中的标签
                tag_list = Tag.objects.filter(name__icontains=kw) # 查询符合条件的标签
                tag_doc_list = [i.doc.id for i in DocTag.objects.filter(tag__in=tag_list)] # 获取符合条件的标签文档

                data_list = Doc.objects.filter(
                    Q(is_public=True) | Q(create_user=request.user),  # 公开或自己的文档
                    Q(id__in=tag_doc_list), # 包含符合条件标签的文档ID列表
                    Q(create_time__gte=start_date, create_time__lte=end_date),  # 筛选创建时间
                ).order_by('-create_time')
            # 游客
            else:
                # 游客：仅搜索公开文档中的标签
                tag_list = Tag.objects.filter(name__icontains=kw)  # 查询符合条件的标签
                tag_doc_list = [i.doc.id for i in DocTag.objects.filter(tag__in=tag_list)]  # 获取符合条件的标签文档

                data_list = Doc.objects.filter(
                    Q(is_public=True),  # 仅公开文档
                    Q(id__in=tag_doc_list),  # 包含符合条件标签的文档ID列表
                    Q(create_time__gte=start_date, create_time__lte=end_date),  # 筛选创建时间
                ).order_by('-create_time')

        else:
            breadcrumb_items = [{"name": _('搜索文档'), 'url': ''}]
            return render(request, 'app_doc/search_results.html', locals())

        # 分页处理
        paginator = Paginator(data_list, 12)
        page = request.GET.get('page', 1)
        try:
            datas = paginator.page(page)
        except PageNotAnInteger:
            datas = paginator.page(1)
        except EmptyPage:
            datas = paginator.page(paginator.num_pages)
        return render(request, 'app_doc/search_result.html', locals())

    # 否则跳转到搜索首页
    else:
        breadcrumb_items = [{"name": _('搜索文档'), 'url': ''}]
        return render(request,'app_doc/search_results.html',locals())


# 文档Markdown文件下载
@require_http_methods(['GET',"POST"])
def download_markdown_export(request,doc_id):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            try:
                doc = Doc.objects.get(id=doc_id)
            except ObjectDoesNotExist:
                return JsonResponse({'status':False,'data':_('文档不存在')})
        else:
            try:
                doc = Doc.objects.get(id=doc_id)
            except ObjectDoesNotExist:
                return JsonResponse({'status':False,'data':_('数据不存在')})
            from backend.apps.doc.services import PermissionService
            effective_perm = PermissionService.get_effective_permission(request.user, doc)
            if request.user != doc.create_user and effective_perm is None:
                return JsonResponse({'status':False,'data':_('无权限')})
    else:
        return render(request,'404.html')

    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename={}.md'.format(doc.name)
    response.write(doc.pre_content)

    return response


def _build_doc_html_for_export(doc, request):
    """将文档内容构建为独立 HTML 页面，用于 PDF 和 HTML 导出"""
    try:
        site_name = SysSetting.objects.get(types="basic", name="site_name").value
    except:
        site_name = "爱思文档"

    content = doc.content or ""
    import re as re_module
    content = re_module.sub(
        r'src=[\'"]\.\./\.\.(?P<path>/media/[^\'"]+)',
        r'src="{}"'.format(request.build_absolute_uri('/')[:-1] + r'\g<path>'),
        content
    )

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans SC', sans-serif;
               max-width: 900px; margin: 40px auto; padding: 20px; line-height: 1.8; color: #333; }}
        h1, h2, h3, h4, h5, h6 {{ margin-top: 1.5em; margin-bottom: 0.5em; font-weight: 600; }}
        h1 {{ font-size: 1.8em; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
        h2 {{ font-size: 1.5em; }}
        pre {{ background: #f5f5f5; padding: 16px; border-radius: 6px; overflow-x: auto; }}
        code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
        pre code {{ background: transparent; padding: 0; }}
        img {{ max-width: 100%; height: auto; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        table td, table th {{ border: 1px solid #ddd; padding: 8px 12px; }}
        table th {{ background: #f5f5f5; font-weight: 600; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 16px 0; padding: 8px 16px; color: #666; background: #f9f9f9; }}
        p {{ margin: 0.8em 0; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {content}
</body>
</html>'''.format(title=doc.name, content=content)

    return html


# 文档 PDF 文件下载
@require_http_methods(['GET'])
def download_pdf_export(request, doc_id):
    if not request.user.is_authenticated:
        return render(request, '404.html')

    try:
        export_setting = SysSetting.objects.get(name='enable_project_report')
        if export_setting.value != 'on':
            raise Http404
    except SysSetting.DoesNotExist:
        raise Http404

    try:
        doc = Doc.objects.get(id=doc_id)
    except ObjectDoesNotExist:
        return JsonResponse({'status': False, 'data': _('文档不存在')})

    if not request.user.is_superuser:
        if request.user != doc.create_user:
            from backend.apps.doc.services import PermissionService
            effective_perm = PermissionService.get_effective_permission(request.user, doc)
            if effective_perm is None:
                return JsonResponse({'status': False, 'data': _('无权限')})

    html_content = _build_doc_html_for_export(doc, request)

    tmp_fd, html_path = tempfile.mkstemp(suffix='.html', prefix='isdoc_')
    os.close(tmp_fd)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    pdf_fd, pdf_path = tempfile.mkstemp(suffix='.pdf', prefix='isdoc_')
    os.close(pdf_fd)

    try:
        html2pdf(html_path, pdf_path)
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
    finally:
        os.unlink(html_path)
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)

    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename={}.pdf'.format(doc.name)
    return response


# 文档 HTML 文件下载
@require_http_methods(['GET'])
def download_html_export(request, doc_id):
    if not request.user.is_authenticated:
        return render(request, '404.html')

    try:
        export_setting = SysSetting.objects.get(name='enable_project_report')
        if export_setting.value != 'on':
            raise Http404
    except SysSetting.DoesNotExist:
        raise Http404

    try:
        doc = Doc.objects.get(id=doc_id)
    except ObjectDoesNotExist:
        return JsonResponse({'status': False, 'data': _('文档不存在')})

    if not request.user.is_superuser:
        if request.user != doc.create_user:
            from backend.apps.doc.services import PermissionService
            effective_perm = PermissionService.get_effective_permission(request.user, doc)
            if effective_perm is None:
                return JsonResponse({'status': False, 'data': _('无权限')})

    html_content = _build_doc_html_for_export(doc, request)

    response = HttpResponse(html_content, content_type='text/html; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename={}.html'.format(doc.name)
    return response


# 个人中心 - 概览
@login_required()
@require_http_methods(['GET','POST'])
def manage_overview(request):
    if request.method == 'GET':
        doc_cnt = Doc.objects.filter(create_user=request.user).count() # 文档总数
        total_tag_cnt = Tag.objects.filter(create_user=request.user).count()
        img_cnt = Image.objects.filter(user=request.user).count()
        attachment_cnt = Attachment.objects.filter(user=request.user).count()

        doc_active_list = Doc.objects.filter(create_user=request.user).order_by('-modify_time')[:5]
        breadcrumb_items = [{"name": _('我的概览'), 'url': ''}]
        return render(request,'app_doc/manage/my_overview.html',locals())
    else:
        pass


# 个人中心 - 文档标签
@login_required()
@require_http_methods(['GET','POST'])
def manage_doc_tag(request):
    if request.method == 'GET':
        tags = Tag.objects.filter(create_user=request.user)
        breadcrumb_items = [{"name": _('文档标签'), 'url': ''}]
        return render(request,'app_doc/manage/content_tags.html',locals())
    # 操作标签
    elif request.method == 'POST':
        types = request.POST.get('types', None)  # 请求类型，0表示创建标签，1表示修改标签，2表示删除标签，3表示获取标签
        # 创建标签
        if int(types) == 0:
            tag_name = request.POST.get('tag_name', '')
            if tag_name != '':
                Tag.objects.create(
                    user=request.user,
                    name=tag_name
                )
                return JsonResponse({'status': True, 'data': 'ok'})
            else:
                return JsonResponse({'status': False, 'data': _('名称无效')})
        # 修改标签
        elif int(types) == 1:
            try:
                tag_name = request.POST.get('tag_name', '')
                if tag_name != "":
                    tag_id = request.POST.get('tag_id', '')
                    if tag_id != "":
                        print(tag_id,tag_name)
                        Tag.objects.filter(id=tag_id, create_user=request.user).update(name=tag_name)
                        return JsonResponse({'status': True, 'data': _('修改成功')})
                    else:
                        return JsonResponse({'status': False, 'data': _('标签ID无效')})
                else:
                    return JsonResponse({'status': False, 'data': _('名称无效')})
            except Exception as e:
                logger.exception("标签修改异常")
                return JsonResponse({'status': False, 'data': _('内部处理错误')})

        # 删除标签
        elif int(types) == 2:
            try:
                tag_id = request.POST.get('tag_id', '')
                tag = Tag.objects.get(id=tag_id, create_user=request.user)  # 查询分组
                tag.delete()  # 删除标签
                return JsonResponse({'status': True, 'data': _('删除完成')})
            except:
                logger.exception(_("删除标签出错"))
                return JsonResponse({'status': False, 'data': _('删除操作未成功')})
        # 获取标签
        elif int(types) == 3:
            try:
                tag_list = []
                return JsonResponse({'status': True, 'data': tag_list})
            except:
                logger.exception(_("获取文档标签出错"))
                return JsonResponse({'status': False, 'data': _('请求处理未成功')})


# 标签文档关系页
def tag_docs(request,tag_id):
    # 获取标签
    try:
        # 颜色列表
        color_list = ['#37a2da', '#32c5e9', '#67e0e3', '#9fe6b8', '#ffdb5c', '#ff9f7f', '#fb7293', '#e062ae', '#e062ae']
        # 获取标签信息
        tag = Tag.objects.get(id=int(tag_id))
        # 获取标签的文档信息
        # 如果访问者已经登录
        if request.user.is_authenticated:
            # 判断是否为标签的创建者
            if request.user == tag.create_user:
                # 获取标签的所有文档
                docs = DocTag.objects.filter(tag=tag,doc__status=1,doc__is_deleted=False)
            else:
                # 获取公开文档 + 自己的文档
                view_docs = Doc.objects.filter(
                    Q(is_public=True) | Q(create_user=request.user),
                    status=1, is_deleted=False
                )
                docs = DocTag.objects.filter(tag=tag, doc__in=view_docs)

        else:
            # 游客：仅公开文档
            view_docs = Doc.objects.filter(is_public=True, status=1, is_deleted=False)
            docs = DocTag.objects.filter(tag=tag, doc__in=view_docs)

        # 获取文档的其他标签信息
        current_link_list = [] # 文档的所有标签ID列表
        for doc in docs:
            other_tags = [str(i.tag.id) for i in DocTag.objects.filter(~Q(tag=tag), doc=doc.doc)]
            current_link_list.extend(other_tags)

        # 标签的节点列表
        tag_nodes_list = [
            # {'id':str(tag.id),'name':tag.name,'symbolSize':50,'value':docs.count(),'itemStyle':{'color':random.choice(color_list)}}
        ]
        # 标签的关系列表
        tag_links_list = []
        # 标签分类列表
        tag_cate = []

        # 添加用户创建的所有标签到节点列表
        for t in Tag.objects.filter(create_user=tag.create_user):
            tag_cate.append({'name':t.name})
            if t.name == tag.name:
                item = {
                    'id': str(t.id),
                    'name': t.name,
                    'symbolSize': 50,
                    'value': DocTag.objects.filter(tag=t,doc__status=1,doc__is_deleted=False).count(),
                    'itemStyle': {'color': random.choice(color_list)}
                }
            else:
                item = {
                    'id':str(t.id),
                    'name':t.name,
                    'symbolSize':25,
                    'value':DocTag.objects.filter(tag=t,doc__status=1,doc__is_deleted=False).count(),
                    'itemStyle':{'color':random.choice(color_list)}
                }
            tag_nodes_list.append(item)
            # 查询非主标签的关联标签
            sub_tags = DocTag.objects.filter(tag=t,doc__status=1,doc__is_deleted=False) # 获取包含t标签的文档
            for sub_tag in sub_tags:
                sub_docs = DocTag.objects.filter(doc=sub_tag.doc,doc__is_deleted=False) # 获取包含文档的标签
                for sub_doc in sub_docs:
                    if str(sub_tag.tag.id) != str(sub_doc.tag.id):
                        item = {
                            'source': str(sub_tag.tag.id),
                            'target': str(sub_doc.tag.id),
                            'value' : sub_doc.doc.name,
                            'id': sub_doc.doc.id,
                            'pid': sub_doc.doc.top_doc,
                            'label':{
                                'normal':{
                                    'show':'true',
                                    'formatter':"{c}",
                                    'fontsize':'10px',
                                }
                            }
                        }
                        item_1 = {
                            'source': str(sub_doc.tag.id),
                            'target': str(sub_tag.tag.id),
                            'value': sub_doc.doc.name,
                            'id':sub_doc.doc.id,
                            'pid': sub_doc.doc.top_doc,
                            'label': {
                                'normal': {
                                    'show': 'true',
                                    'formatter': "{c}",
                                    'fontsize': '10px',
                                }
                            }
                        }
                        if item_1 not in tag_links_list:
                            tag_links_list.append(item)

        return render(request, 'app_doc/tag_document_list.html', locals())
    except Exception as e:
        logger.exception(_("标签文档页访问异常"))
        return render(request, '404.html')


# 标签文档页
@require_http_methods(['GET'])
def tag_doc(request,tag_id,doc_id):
    try:
        if tag_id != '' and doc_id != '':
            doc = Doc.objects.get(id=int(doc_id), status=1)
            # v1.0: 使用 PermissionService 检查文档权限
            from backend.apps.doc.services import PermissionService
            effective_perm = PermissionService.get_effective_permission(request.user, doc)
            if not doc.is_public and effective_perm is None:
                return render(request, '404.html')

            # 获取文档内容
            try:
                # 获取标签信息
                tag = Tag.objects.get(id=int(tag_id))
                # 获取标签文档信息
                docs = DocTag.objects.filter(tag=tag)
                # 获取文档的标签
                doc_tags = DocTag.objects.filter(doc=doc)
            except ObjectDoesNotExist:
                return render(request, '404.html')
            return render(request,'app_doc/tag_document_detail.html',locals())
        else:
            return HttpResponse(_('请求参数不正确'))
    except Exception as e:
        logger.exception(_("文集浏览出错"))
        return render(request,'404.html')


# 个人中心 - 个人设置
@login_required()
def manage_self(request):
    if request.method == 'GET':
        user = User.objects.get_by_natural_key(request.user)
        try:
            user_opt = UserOptions.objects.get(user=request.user)
        except ObjectDoesNotExist:
            user_opt = []
        return render(request,'app_doc/manage/my_settings.html',locals())
    elif request.method == 'POST':
        first_name = request.POST.get('first_name','') # 昵称
        email = request.POST.get('email',None) # 电子邮箱
        editor_mode = request.POST.get('editor_mode',0) # 编辑器
        user = User.objects.get_by_natural_key(request.user)
        if len(first_name) < 2 or len(first_name) > 10:
            return JsonResponse({'status': False, 'data': _('昵称长度不得小于2位大于10位')})
        if User.objects.filter(first_name=first_name).count() > 0 and user.first_name != first_name:
            return JsonResponse({'status':False,'data':_('昵称已被使用')})
        if User.objects.filter(email=email).count() > 0 and user.email != email:
            return JsonResponse({'status':False,'data':_('电子邮箱已被使用')})
        if email != '' and '@' in email:
            user.email = email
            user.first_name = first_name
            user.save()
            user_opt = UserOptions.objects.update_or_create(
                user = user,
                defaults={'editor_mode':editor_mode}
            )
            return JsonResponse({'status':True,'data':'ok'})
        else:
            return JsonResponse({'status':False,'data':_('参数不正确')})


# 文集文档收藏
@login_required()
def toggle_favorite(request):
    if request.method == 'GET':
        pass
    elif request.method == 'POST':
        collect_type = request.POST.get('collect_type',None) # 收藏类型
        collect_id = request.POST.get('collect_id',None) # 收藏对象ID
        if (collect_type is None) or (collect_id is None):
            return JsonResponse({'status':False,'data':_('请求参数不正确')})
        else:
            is_collect = MyCollect.objects.filter(collect_type=collect_type,collect_id=collect_id,create_user=request.user)
            # 存在收藏
            if is_collect.exists():
                is_collect.delete()
                return JsonResponse({'status': True, 'data': 'remove'})
            else:
                MyCollect.objects.create(
                    collect_type = collect_type,
                    collect_id = collect_id,
                    create_user = request.user,
                    create_time = datetime.datetime.now()
                )
                return JsonResponse({'status':True,'data':'add'})

    elif request.method == 'DELETE':
        pass

# 收藏管理
@login_required()
@require_http_methods(['GET','POST','DELETE'])
@csrf_exempt
def manage_favorites(request):
    if request.method == 'GET':
        # Redirect to unified user center
        return redirect(reverse('user_center') + '?tab=my_collects')
    elif request.method == 'POST':
        kw = request.POST.get('kw', '') # 搜索词
        collect_type = request.POST.get('type', '') # 收藏类型
        if collect_type in ['1']:
            q_type = [int(collect_type)]
        else:
            q_type = [1]

        page = request.POST.get('page', 1)
        limit = request.POST.get('limit', 10)
        # 没有搜索
        if kw == '':
            collect_list = MyCollect.objects.filter(
                create_user=request.user,
                collect_type__in=q_type,
            ).order_by('-create_time')
        # 有搜索
        else:
            doc_ids = Doc.objects.filter(name__icontains=kw).values_list('id', flat=True)
            from django.db.models import Q as Q_obj
            collect_list = MyCollect.objects.filter(
                collect_type__in=q_type,
                collect_id__in=doc_ids,
                create_user=request.user
            ).order_by('-create_time')

        # 分页处理
        paginator = Paginator(collect_list, limit)
        page = request.GET.get('page', page)
        try:
            collects = paginator.page(page)
        except PageNotAnInteger:
            collects = paginator.page(1)
        except EmptyPage:
            collects = paginator.page(paginator.num_pages)

        table_data = []
        for collect in collects:
            try:
                if collect.collect_type == 1:
                    item_doc = Doc.objects.get(id=collect.collect_id)
                    item_id = item_doc.id
                    item_name = item_doc.name
                    item_project_name = '--'
                    item_project_id = item_doc.top_doc
                else:
                    continue
            except Doc.DoesNotExist:
                continue
            item = {
                'id': collect.id,
                'item_id':item_id,
                'item_name': _escape_html(item_name),
                'type': collect.collect_type,
                'item_project_id':item_project_id,
                'item_project_name':item_project_name,
                'create_time': collect.create_time,
            }
            table_data.append(item)
        resp_data = {
            "code": 0,
            "msg": "ok",
            "count": collect_list.count(),
            "data": table_data
        }
        return JsonResponse(resp_data)
    elif request.method == 'DELETE':
        try:
            # 获取收藏ID
            DELETE = QueryDict(request.body)
            collect_id = DELETE.get('collect_id', None)
            range = DELETE.get('range', 'single')
            if collect_id:
                if range == 'single':
                    # 查询收藏
                    try:
                        collect = MyCollect.objects.get(id=collect_id)
                    except ObjectDoesNotExist:
                        return JsonResponse({'status': False, 'data': _('收藏不存在')})
                    # 如果请求用户为站点管理员、收藏的创建者，可以删除
                    if (request.user == collect.create_user) or (request.user.is_superuser):
                        MyCollect.objects.filter(id=collect_id).delete()
                        return JsonResponse({'status': True, 'data': _('删除完成')})
                    else:
                        return JsonResponse({'status': False, 'data': _('操作未被授权')})
                elif range == 'multi':
                    collects = collect_id.split(",")
                    try:
                        MyCollect.objects.filter(id__in=collects, create_user=request.user).delete()
                        return JsonResponse({'status': True, 'data': _('删除完成')})
                    except:
                        return JsonResponse({'status': False, 'data': _('操作未被授权')})
                else:
                    return JsonResponse({'status': False, 'data': _('操作类型不正确')})

            else:
                return JsonResponse({'status': False, 'data': _('请求参数不正确')})
        except Exception as e:
            logger.exception("收藏切换操作异常")
            return JsonResponse({'status': False, 'data': _('无法处理该请求')})

# 获取当前版本
def get_version(request):
    try:
        version = settings.VERSIONS
        data = {
            'status':True,
            'data':version
        }
    except:
        data = {
            'status':False,
            'data':_('异常')
        }
    return JsonResponse(data)


# 用户分组用户列表接口
class UserGroupUserList(APIView):
    authentication_classes = [SessionAuthentication, AppMustAuth]

    def get(self,request):
        user_data = User.objects.filter(is_active=True).values(
            'id', 'username', 'first_name'
        )
        user_list = []
        for user in user_data:
            item = {
                'name':user['username'],
                'value':user['id']
            }
            user_list.append(item)
        # serializer = UserSerializer(user_data, many=True)  # 对结果进行序列化处理
        resp = {
            'code': 0,
            'data': user_list,
            'count': user_data.count()
        }

        return Response(resp)


# ==================== 文档评论系统 ====================

def _is_doc_admin(user, doc):
    """检查用户是否为文档管理员（文档创建者或 DocPermission admin）。"""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if doc.create_user == user:
        return True
    from backend.apps.doc.services import PermissionService
    return PermissionService.get_effective_permission(user, doc) == 'admin'


def _can_delete_comment(user, comment):
    """检查用户是否有权删除评论（评论作者或文档管理员）。"""
    return comment.user == user or _is_doc_admin(user, comment.doc)


def _parse_mentions(content):
    """从评论文本中提取 @username 列表。"""
    import re
    pattern = r'@([\w.@+-]+)'
    return re.findall(pattern, content)


def get_comments_tree(comments):
    """将评论列表转换为树形结构"""
    top = []
    children_map = {}
    for c in comments:
        c._replies = []
        if c.parent_id:
            children_map.setdefault(c.parent_id, []).append(c)
        else:
            top.append(c)
    def attach(comment_list):
        for c in comment_list:
            c._replies = children_map.get(c.id, [])
            attach(c._replies)
    attach(top)
    return top


@login_required()
@require_http_methods(['GET', 'POST'])
def document_comments_handler(request, pro_id, doc_id):
    """获取/发表文档评论"""
    try:
        doc = Doc.objects.get(id=doc_id, top_doc=pro_id, status=1)
    except Doc.DoesNotExist:
        return JsonResponse({'status': False, 'data': _('文档不存在')})

    if request.method == 'GET':
        comments = DocComment.objects.filter(doc=doc, is_active=True).select_related('user', 'doc__create_user').order_by('create_time')
        result = []
        for c in get_comments_tree(comments):
            result.append(_serialize_comment(c, request.user))
        return JsonResponse({'status': True, 'data': result, 'count': comments.count()})

    elif request.method == 'POST':
        parent_id = request.POST.get('parent_id', '').strip()
        content = request.POST.get('content', '').strip()
        if not content:
            return JsonResponse({'status': False, 'data': _('评论内容不能为空')})
        if len(content) > 2000:
            return JsonResponse({'status': False, 'data': _('评论内容不能超过2000字')})
        parent = None
        if parent_id:
            try:
                parent = DocComment.objects.get(id=int(parent_id), doc=doc, is_active=True)
            except (DocComment.DoesNotExist, ValueError):
                return JsonResponse({'status': False, 'data': _('父评论不存在')})
        comment = DocComment.objects.create(
            doc=doc, user=request.user, parent=parent, content=content
        )
        # 更新父评论回复数
        if parent:
            DocComment.objects.filter(pk=parent.pk).update(
                reply_count=DocComment.objects.filter(parent=parent, is_active=True).count()
            )
        # 解析 @提及 并关联 mentioned_users
        mentioned = _parse_mentions(content)
        if mentioned:
            from backend.apps.doc.models import User
            mentioned_users = User.objects.filter(username__in=mentioned, is_active=True)
            comment.mentioned_users.add(*mentioned_users)
            # 发送 @提及 通知
            from backend.apps.doc.services import NotificationService
            doc_url = f'/pages/{doc_id}/'
            for mu in mentioned_users:
                if mu != request.user:
                    NotificationService.send(
                        recipient=mu, notification_type='mention', title='有人 @了你',
                        sender=request.user, send_email=True,
                        body=f'{request.user.first_name or request.user.username} 在文档评论中 @了你',
                        link=doc_url,
                        context={'doc_name': doc.name, 'comment_content': content[:200]},
                    )
        # 发送回复通知（给父评论作者）
        if parent and parent.user != request.user:
            from backend.apps.doc.services import NotificationService
            NotificationService.send(
                recipient=parent.user, notification_type='reply', title='有人回复了你的评论',
                sender=request.user, send_email=True,
                body=f'{request.user.first_name or request.user.username} 回复了你在《{doc.name}》中的评论',
                link=f'/pages/{doc_id}/',
                context={'doc_name': doc.name, 'comment_content': content[:200]},
            )
        return JsonResponse({'status': True, 'data': _serialize_comment(comment, request.user)})


@login_required()
@require_POST
def delete_comment(request, comment_id):
    """删除评论（评论作者或文档管理员可删除）"""
    try:
        comment = DocComment.objects.select_related('doc', 'doc__create_user').get(id=comment_id, is_active=True)
    except DocComment.DoesNotExist:
        return JsonResponse({'status': False, 'data': _('评论不存在')})
    if not _can_delete_comment(request.user, comment):
        return JsonResponse({'status': False, 'data': _('无权删除此评论')})
    comment.is_active = False
    comment.save()
    return JsonResponse({'status': True, 'data': _('删除成功')})


@login_required
@require_POST
def toggle_document_like(request, doc_id):
    """Toggle like on a document. Returns liked state and total count.

    点赞/取消时向文档作者发送聚合通知（同文档同日汇总为一条）。
    """
    try:
        doc = Doc.objects.get(id=doc_id, status__in=[0, 1])
    except Doc.DoesNotExist:
        return JsonResponse({'status': False, 'data': _('文档不存在')})
    like, created = DocLike.objects.get_or_create(doc=doc, user=request.user)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    count = DocLike.objects.filter(doc=doc).count()

    # 点赞聚合通知 — 仅通知文档作者（非本人点赞时）
    if doc.create_user_id and doc.create_user_id != request.user.id:
        from backend.apps.doc.services import NotificationService
        NotificationService._upsert_like_notification(
            doc=doc, liker=request.user, is_like=liked, total_count=count
        )

    return JsonResponse({'status': True, 'liked': liked, 'count': count})


def _render_comment_html(content, mentioned_users=None):
    """将评论文本转为安全的 HTML：转义 + URL 链接 + @mention 链接。"""
    import re
    from django.utils.html import escape
    text = escape(content)
    # URL → <a> link
    url_pattern = re.compile(r'(https?://[^\s<>"{}|\\^`\[\]]+)', re.IGNORECASE)
    text = url_pattern.sub(
        r'<a href="\1" target="_blank" rel="noopener noreferrer" class="ispace-autolink">\1</a>',
        text
    )
    # @username → <a data-user-id="N"> link
    if mentioned_users:
        user_map = {u.username: u.id for u in mentioned_users}
        mention_pattern = re.compile(r'@([\w.@+-]+)')
        def _mention_link(m):
            uname = m.group(1)
            uid = user_map.get(uname)
            if uid:
                return f'<a class="ispace-mention-link" data-user-id="{uid}">@{escape(uname)}</a>'
            return m.group(0)
        text = mention_pattern.sub(_mention_link, text)
    return text


def _serialize_comment(comment, current_user, depth=0):
    """序列化单个评论节点，递归包含所有层级回复。"""
    replies = []
    children = getattr(comment, '_replies', [])
    if children:
        replies = [_serialize_comment(r, current_user, depth + 1) for r in children]
    # 获取 mentioned_users 用于 linkify
    try:
        mentioned = list(comment.mentioned_users.all())
    except Exception:
        mentioned = []
    return {
        'id': comment.id,
        'content': comment.content,
        'content_html': _render_comment_html(comment.content, mentioned),
        'user_id': comment.user.id,
        'user_name': comment.user.first_name or comment.user.username,
        'user_avatar': comment.user.avatar.url if hasattr(comment.user, 'avatar') and comment.user.avatar else None,
        'create_time': comment.create_time.strftime('%Y-%m-%d %H:%M'),
        'parent_id': comment.parent_id,
        'depth': depth,
        'can_delete': _can_delete_comment(current_user, comment),
        'replies': replies,
    }


# ================================================================
#  v1.0 Phase 5 — 划词评论 (InlineComment) API
# ================================================================

@login_required()
def inline_comments(request, pro_id=None, doc_id=None):
    """划词评论列表 / 创建。

    GET  — 返回文档所有划词评论（按 anchor_start 排序）
    POST — 创建划词评论（body: anchor_start, anchor_end, anchor_hash, selected_text, content）
    """
    if doc_id is None and pro_id is not None:
        doc_id = pro_id  # V2 URL: /pages/<doc_id>/inline-comments/ — only one captured arg
    try:
        doc = Doc.objects.get(id=doc_id, status__in=[0, 1])
    except Doc.DoesNotExist:
        return JsonResponse({'status': False, 'data': _('文档不存在')})

    if request.method == 'GET':
        all_comments = list(InlineComment.objects.filter(
            doc=doc, is_active=True
        ).select_related('user', 'doc__create_user').order_by('anchor_start'))

        # 预收集所有 @mention 用户名 → 用户 ID 映射
        from backend.apps.doc.models import User
        all_mentions = set()
        for c in all_comments:
            all_mentions.update(_parse_mentions(c.content))
        mentioned_users_map = {}
        if all_mentions:
            users = User.objects.filter(username__in=all_mentions, is_active=True)
            mentioned_users_map = {u.username: u for u in users}

        # 构建回复树（所有评论，任意深度）
        children_map = {}
        for c in all_comments:
            children_map.setdefault(c.parent_id, []).append(c)

        def _build_inline_tree(comment_list):
            result = []
            for c in comment_list:
                # 找出该条评论对应的 mentioned users
                c_mentions = _parse_mentions(c.content)
                c_mentioned = [mentioned_users_map[u] for u in c_mentions if u in mentioned_users_map]
                result.append({
                    'id': c.id,
                    'user_id': c.user_id,
                    'user_name': c.user.first_name or c.user.username,
                    'content': c.content,
                    'content_html': _render_comment_html(c.content, c_mentioned),
                    'create_time': c.create_time.strftime('%Y-%m-%d %H:%M'),
                    'can_delete': _can_delete_comment(request.user, c),
                    'parent_id': c.parent_id,
                    'replies': _build_inline_tree(children_map.get(c.id, [])),
                })
            return result

        # 按 anchor 分组（同一锚点的顶级评论归到一组）
        top_comments = [c for c in all_comments if c.parent_id is None]
        groups = {}
        for c in top_comments:
            key = f'{c.anchor_start}:{c.anchor_end}'
            if key not in groups:
                groups[key] = {
                    'anchor_start': c.anchor_start,
                    'anchor_end': c.anchor_end,
                    'anchor_hash': c.anchor_hash,
                    'selected_text': c.selected_text,
                    'count': 0,
                    'comments': [],
                }
            groups[key]['count'] += 1
            # 找出该条评论对应的 mentioned users
            c_top_mentions = _parse_mentions(c.content)
            c_top_mentioned = [mentioned_users_map[u] for u in c_top_mentions if u in mentioned_users_map]
            groups[key]['comments'].append({
                'id': c.id,
                'user_id': c.user_id,
                'user_name': c.user.first_name or c.user.username,
                'content': c.content,
                'content_html': _render_comment_html(c.content, c_top_mentioned),
                'create_time': c.create_time.strftime('%Y-%m-%d %H:%M'),
                'can_delete': _can_delete_comment(request.user, c),
                'replies': _build_inline_tree(children_map.get(c.id, [])),
            })

        return JsonResponse({
            'status': True,
            'data': sorted(groups.values(), key=lambda g: g['anchor_start']),
        })

    # POST — 创建
    import json, hashlib
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'status': False, 'data': _('请求数据格式错误')})

    anchor_start = body.get('anchor_start', 0)
    anchor_end = body.get('anchor_end', 0)
    anchor_hash = body.get('anchor_hash', '')
    selected_text = body.get('selected_text', '')[:500]
    content = body.get('content', '').strip()
    parent_id = body.get('parent_id')

    if not content:
        return JsonResponse({'status': False, 'data': _('评论内容不能为空')})
    if len(selected_text) < 1:
        return JsonResponse({'status': False, 'data': _('划词文本不能为空')})

    # 上限校验（每文档最多 500 条）
    count = InlineComment.objects.filter(doc=doc, is_active=True).count()
    if count >= 500:
        return JsonResponse({'status': False, 'data': _('该文档划词评论已达上限（500条）')})

    # 校验父评论
    parent = None
    if parent_id:
        try:
            parent = InlineComment.objects.get(id=int(parent_id), doc=doc, is_active=True)
        except (InlineComment.DoesNotExist, ValueError):
            return JsonResponse({'status': False, 'data': _('父评论不存在')})

    # 计算锚点哈希（前端传参校验）
    expected_hash = hashlib.md5(selected_text.encode('utf-8')).hexdigest()
    if anchor_hash and anchor_hash != expected_hash:
        return JsonResponse({'status': False, 'data': _('划词文本校验失败，请重试')})

    comment = InlineComment.objects.create(
        doc=doc,
        anchor_start=anchor_start,
        anchor_end=anchor_end,
        anchor_hash=expected_hash,
        selected_text=selected_text,
        user=request.user,
        content=content,
        parent=parent,
    )

    # 向文档作者发送通知
    from backend.apps.doc.services import NotificationService
    doc_url = f'/pages/{doc.id}/'
    if doc.create_user_id and doc.create_user_id != request.user.id:
        NotificationService.send(
            recipient=doc.create_user,
            notification_type='comment',
            title=f'{request.user.first_name or request.user.username} 在《{doc.name}》中发表了划词评论',
            sender=request.user,
            body=content[:200],
            link=doc_url,
        )

    # 向父评论作者发送回复通知
    if parent and parent.user_id != request.user.id:
        NotificationService.send(
            recipient=parent.user,
            notification_type='reply',
            title='有人回复了你的划词评论',
            sender=request.user,
            send_email=True,
            body=f'{request.user.first_name or request.user.username} 回复了你在《{doc.name}》中的划词评论',
            link=doc_url,
            context={'doc_name': doc.name, 'comment_content': content[:200]},
        )

    # 解析 @提及 并发送通知
    from backend.apps.doc.models import User
    mentioned = _parse_mentions(content)
    if mentioned:
        mentioned_users = User.objects.filter(username__in=mentioned, is_active=True)
        for mu in mentioned_users:
            if mu != request.user and mu != (parent.user if parent else None):
                NotificationService.send(
                    recipient=mu, notification_type='mention', title='有人 @了你',
                    sender=request.user, send_email=True,
                    body=f'{request.user.first_name or request.user.username} 在划词评论中 @了你',
                    link=doc_url,
                    context={'doc_name': doc.name, 'comment_content': content[:200]},
                )

    # 为新建评论生成 content_html（mention 链接）
    mentioned_usernames = _parse_mentions(content)
    mentioned_users = User.objects.filter(username__in=mentioned_usernames, is_active=True)
    content_html = _render_comment_html(content, mentioned_users)

    return JsonResponse({
        'status': True,
        'data': {
            'id': comment.id,
            'anchor_start': comment.anchor_start,
            'anchor_end': comment.anchor_end,
            'selected_text': comment.selected_text,
            'content': comment.content,
            'content_html': content_html,
            'create_time': comment.create_time.strftime('%Y-%m-%d %H:%M'),
        },
    })


@login_required()
@require_POST
def delete_inline_comment(request, comment_id):
    """删除划词评论（软删除，评论作者或文档管理员可删除）。"""
    try:
        comment = InlineComment.objects.select_related('doc', 'doc__create_user').get(id=comment_id, is_active=True)
    except InlineComment.DoesNotExist:
        return JsonResponse({'status': False, 'data': _('评论不存在')})
    if not _can_delete_comment(request.user, comment):
        return JsonResponse({'status': False, 'data': _('无权删除此评论')})
    comment.is_active = False
    comment.save()
    return JsonResponse({'status': True, 'data': _('删除成功')})
