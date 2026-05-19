# coding:utf-8
# 全局侧边栏文档树 — 上下文处理器
from django.db.models import Q
from backend.apps.doc.models import Project, Doc, ProjectCollaborator


def sidebar_tree(request):
    """为全站页面提供左侧统一文档目录树数据。
    不再区分文集与文档——文集即根级文档节点，所有元素统一为文档节点。
    """
    tree = []
    user = request.user
    is_auth = user.is_authenticated

    if is_auth:
        colla_ids = list(ProjectCollaborator.objects.filter(
            user=user
        ).values_list('project_id', flat=True))
        qs = Project.objects.filter(
            Q(role__in=[0, 3]) |
            Q(role=2, role_value__contains=str(user.username)) |
            Q(create_user=user) |
            Q(id__in=colla_ids)
        ).order_by('-is_top', '-create_time')
    else:
        qs = Project.objects.filter(role__in=[0, 3]).order_by('-is_top', '-create_time')

    pro_ids = list(qs.values_list('id', flat=True))

    if not pro_ids:
        return {'sidebar_tree': []}

    # 获取所有已发布文档
    all_docs = Doc.objects.filter(
        top_doc__in=pro_ids,
        status=1
    ).select_related('create_user').order_by('sort', 'name')

    # 按项目分组文档
    pro_docs_map = {}
    for d in all_docs:
        pro_docs_map.setdefault(d.top_doc, []).append(d)

    def build_tree(docs_list):
        """将扁平的文档列表构建为树形结构"""
        doc_map = {}
        for d in docs_list:
            doc_map.setdefault(d.parent_doc, []).append(d)

        def make_nodes(parent_id):
            children = doc_map.get(parent_id, [])
            nodes = []
            for doc in children:
                nodes.append({
                    'id': doc.id,
                    'name': doc.name,
                    'top_doc': doc.top_doc,
                    'children': make_nodes(doc.id),
                    'has_children': doc.id in doc_map,
                    'open_children': doc.open_children,
                    'is_project': False,
                })
            return nodes

        return make_nodes(0)

    for p in qs:
        docs = pro_docs_map.get(p.id, [])
        root_docs = [d for d in docs if d.parent_doc == 0]
        if len(docs) == 1 and len(root_docs) == 1:
            # 含单一根级文档的项目：扁平化，文档直接显示在树根
            tree.extend(build_tree(docs))
        else:
            tree.append({
                'id': p.id,
                'name': p.name,
                'top_doc': p.id,
                'children': build_tree(docs),
                'has_children': len(docs) > 0,
                'open_children': False,
                'is_project': True,
            })

    return {'sidebar_tree': tree}
