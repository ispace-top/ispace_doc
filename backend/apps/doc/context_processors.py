# coding:utf-8
# 全局侧边栏文档树 — 上下文处理器
from django.db.models import Q
from backend.apps.doc.models import Doc, DocPermission, GroupMember, OrgUser


def sidebar_tree(request):
    """为全站页面提供左侧统一文档目录树数据。"""

    user = request.user
    is_auth = user.is_authenticated
    is_spa_request = request.META.get('HTTP_X_SPA_NAVIGATE') == '1'

    try:
        if is_auth:
            # 收集用户通过权限系统可访问的文档 ID
            group_ids = set(GroupMember.objects.filter(user=user).values_list('group_id', flat=True))
            org_nodes = OrgUser.objects.filter(user=user).select_related('org_node')
            org_ids = set()
            for ou in org_nodes:
                org_ids.add(ou.org_node_id)
                node = ou.org_node
                while node.parent_id:
                    org_ids.add(node.parent_id)
                    node = node.parent

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
            ).select_related('create_user').order_by('sort', 'name')
        else:
            docs_qs = Doc.objects.filter(
                is_public=True, status=1, is_deleted=False
            ).order_by('sort', 'name')

        if not docs_qs.exists():
            return {'sidebar_tree': [], 'is_spa_request': is_spa_request}

        # 构建文档层级
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

        tree = make_nodes(0)
        return {'sidebar_tree': tree, 'is_spa_request': is_spa_request}
    except Exception:
        # 数据库未迁移时静默跳过
        return {'sidebar_tree': [], 'is_spa_request': is_spa_request}
