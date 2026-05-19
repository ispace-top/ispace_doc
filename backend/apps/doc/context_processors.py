# coding:utf-8
# 全局侧边栏文档树 — 上下文处理器
from django.db.models import Q
from backend.apps.doc.models import Project, Doc, ProjectCollaborator


def sidebar_tree(request):
    """为全站页面提供左侧统一文档目录树数据。
    所有节点均为文档节点，层级关系由 parent_doc 字段决定，无项目包装层。
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

    # 构建用户对每个项目的编辑权限
    # 2=完全管理(创建者/协作者role=1), 1=可新建+可编辑自己的文档(协作者role=0), 0=无权限
    pro_perm = {}
    if is_auth:
        colla_map = {}
        for pc in ProjectCollaborator.objects.filter(
            project_id__in=pro_ids, user=user
        ).values('project_id', 'role'):
            colla_map[pc['project_id']] = pc['role']
        for pid in pro_ids:
            colla_role = colla_map.get(pid)
            if colla_role is not None:
                pro_perm[pid] = 2 if colla_role == 1 else 1
            else:
                pro_perm[pid] = 0
    else:
        for pid in pro_ids:
            pro_perm[pid] = 0

    # 补充创建者权限（creator 对所属项目拥有完全管理权限）
    for p in qs:
        if is_auth and p.create_user_id == user.id:
            pro_perm[p.id] = 2
        elif p.id not in pro_perm:
            pro_perm[p.id] = 0

    # 获取所有已发布文档
    docs_qs = Doc.objects.filter(
        top_doc__in=pro_ids,
        status=1
    ).select_related('create_user').order_by('sort', 'name')

    # 按项目分组文档
    pro_docs_map = {}
    for d in docs_qs:
        pro_docs_map.setdefault(d.top_doc, []).append(d)

    # 收集所有项目下的文档，构建统一的文档树（无项目包装层）
    all_docs = []
    for p in qs:
        all_docs.extend(pro_docs_map.get(p.id, []))

    def build_tree(docs_list):
        """将扁平的文档列表构建为树形结构（跨项目混合）"""
        doc_map = {}
        for d in docs_list:
            doc_map.setdefault(d.parent_doc, []).append(d)

        def make_nodes(parent_id):
            children = doc_map.get(parent_id, [])
            nodes = []
            for doc in children:
                pp = pro_perm.get(doc.top_doc, 0)
                if pp >= 2:
                    can_manage = True
                elif pp == 1 and doc.create_user_id == user.id:
                    can_manage = True
                else:
                    can_manage = False
                nodes.append({
                    'id': doc.id,
                    'name': doc.name,
                    'top_doc': doc.top_doc,
                    'children': make_nodes(doc.id),
                    'has_children': doc.id in doc_map,
                    'open_children': doc.open_children,
                    'is_project': False,
                    'can_create': pp >= 1,
                    'can_manage': can_manage,
                })
            return nodes

        return make_nodes(0)

    tree = build_tree(all_docs)

    return {'sidebar_tree': tree}
