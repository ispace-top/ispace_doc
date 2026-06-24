# coding:utf-8
# 全局侧边栏文档树 — 上下文处理器
from django.core.cache import cache
from django.db.models import Q
from backend.apps.doc.models import Doc, DocPermission, GroupMember
from backend.apps.doc.services import _get_user_org_ancestor_ids

_SIDEBAR_CACHE_TTL = 60  # 侧边栏树缓存秒数


def sidebar_tree(request):
    """为全站页面提供左侧统一文档目录树数据。
    对认证用户缓存 60 秒，减少每次页面渲染的重复 DB 查询。
    """

    user = request.user
    is_auth = user.is_authenticated
    is_spa_request = request.META.get('HTTP_X_SPA_NAVIGATE') == '1'

    # SPA 导航请求不重新渲染侧边栏，跳过查询
    if is_spa_request:
        return {'sidebar_tree': [], 'is_spa_request': True}

    cache_key = f'sidebar_tree:{user.id}' if is_auth else 'sidebar_tree:anon'

    def _build_tree():
        try:
            if is_auth:
                group_ids = set(GroupMember.objects.filter(user=user).values_list('group_id', flat=True))
                org_ids = _get_user_org_ancestor_ids(user)

                target_filter = Q(target_type='user', target_id=user.id)
                if group_ids:
                    target_filter |= Q(target_type='group', target_id__in=group_ids)
                if org_ids:
                    target_filter |= Q(target_type='org', target_id__in=org_ids)

                permitted_doc_ids = set(
                    DocPermission.objects.filter(target_filter)
                    .values_list('doc_id', flat=True).distinct()
                )

                docs_qs = Doc.objects.filter(
                    Q(is_public=True) | Q(create_user=user) | Q(id__in=permitted_doc_ids),
                    status=1,
                    is_deleted=False
                ).only('id', 'name', 'parent_doc', 'create_user', 'open_children').order_by('sort', 'name')
            else:
                docs_qs = Doc.objects.filter(
                    is_public=True, status=1, is_deleted=False
                ).only('id', 'name', 'parent_doc', 'create_user', 'open_children').order_by('sort', 'name')

            if not docs_qs.exists():
                return []

            doc_map = {}
            for d in docs_qs:
                doc_map.setdefault(d.parent_doc, []).append(d)

            def make_nodes(parent_id):
                children = doc_map.get(parent_id, [])
                nodes = []
                for doc in children:
                    nodes.append({
                        'id': doc.id,
                        'name': doc.name,
                        'children': make_nodes(doc.id),
                        'has_children': doc.id in doc_map,
                        'open_children': doc.open_children,
                        'can_create': is_auth,
                        'can_manage': is_auth and (doc.create_user_id == user.id),
                    })
                return nodes

            return make_nodes(0)
        except Exception:
            return []

    tree = cache.get(cache_key)
    if tree is None:
        tree = _build_tree()
        cache.set(cache_key, tree, _SIDEBAR_CACHE_TTL)

    return {'sidebar_tree': tree, 'is_spa_request': is_spa_request}
