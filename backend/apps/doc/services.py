"""
v1.0 核心服务层

PermissionService  — 有效权限计算（用户 + 分组 + 组织节点 三线合并取最大）
DocService         — 文档软删除、恢复、拖拽排序
NotificationService — 通知发送（站内 + 邮件）
"""

import json as _json

from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Q, Max
from django.utils import timezone

from django.contrib.auth.models import User
from .models import (
    Doc, DocPermission, GroupMember, OrgUser, OrgNode,
    Notification, UserProfile,
)

# 权限缓存 TTL（秒）
_PERM_CACHE_TTL = 300


# ---------------------------------------------------------------
#  PermissionService
# ---------------------------------------------------------------

_PERM_RANK = {'view': 0, 'edit': 1, 'admin': 2}


class PermissionService:
    """文档有效权限计算引擎。

    算法：取 用户自身 + 所属所有分组 + 所属所有组织节点（含上级） 的最大权限。
    """

    @staticmethod
    def get_effective_permission(user: User, doc: Doc) -> str | None:
        """返回用户对文档的最终权限：'view' / 'edit' / 'admin'，无权限返回 None。

        结果缓存在内存中（默认 5 分钟 TTL），权限变更时主动失效。
        """
        if not user or not user.is_authenticated:
            return None
        if user.is_superuser:
            return 'admin'
        # 文档创建者默认拥有管理员权限
        if doc.create_user_id == user.id:
            return 'admin'

        # 查缓存
        cache_key = PermissionService._cache_key(user.id, doc.id)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached if cached != '__none__' else None

        best_rank = -1

        # 1) 直接授予用户的权限
        best_rank = max(best_rank, PermissionService._get_direct_user_perm(user, doc))

        # 2) 用户所属所有分组的权限
        best_rank = max(best_rank, PermissionService._get_group_perm(user, doc))

        # 3) 用户所属所有组织节点的权限（含上级继承）
        best_rank = max(best_rank, PermissionService._get_org_perm(user, doc))

        # 4) 公开文档默认 view
        if best_rank < 0 and PermissionService._is_doc_public(doc):
            best_rank = 0

        result = None
        for key, rank in _PERM_RANK.items():
            if rank == best_rank:
                result = key
                break

        # 写入缓存
        cache.set(cache_key, result if result else '__none__', _PERM_CACHE_TTL)
        return result

    @staticmethod
    def _cache_key(user_id: int, doc_id: int) -> str:
        """生成权限缓存 key，包含版本号以支持批量失效。"""
        version = cache.get(f'permver:{doc_id}') or 1
        return f'perm:{user_id}:{doc_id}:v{version}'

    @staticmethod
    def invalidate_cache(doc_id: int):
        """使某文档的所有权限缓存失效（递增版本号）。"""
        try:
            cache.incr(f'permver:{doc_id}')
        except ValueError:
            cache.set(f'permver:{doc_id}', 2, None)  # 设为 2 使旧 key(version=1) 失效

    @staticmethod
    def invalidate_for_group(group_id: int):
        """分组成员变更后，失效所有关联文档的权限缓存。"""
        doc_ids = DocPermission.objects.filter(
            target_type='group', target_id=group_id
        ).values_list('doc_id', flat=True).distinct()
        for did in doc_ids:
            PermissionService.invalidate_cache(did)

    @staticmethod
    def invalidate_for_org(node_id: int):
        """组织成员变更后，失效所有关联文档（含上级节点）的权限缓存。"""
        # 获取该节点及其所有祖先节点 ID
        try:
            node = OrgNode.objects.only('path').get(pk=node_id)
            path_parts = node.path.strip('/').split('/')
            ancestor_ids = [int(p) for p in path_parts if p.isdigit()]
        except OrgNode.DoesNotExist:
            ancestor_ids = [node_id]

        doc_ids = DocPermission.objects.filter(
            target_type='org', target_id__in=ancestor_ids
        ).values_list('doc_id', flat=True).distinct()
        for did in doc_ids:
            PermissionService.invalidate_cache(did)

    @staticmethod
    def _get_direct_user_perm(user, doc):
        perm = DocPermission.objects.filter(
            doc=doc, target_type='user', target_id=user.id
        ).aggregate(m=Max('permission'))['m']
        return _PERM_RANK.get(perm, -1)

    @staticmethod
    def _get_group_perm(user, doc):
        group_ids = list(GroupMember.objects.filter(user=user).values_list('group_id', flat=True))
        if not group_ids:
            return -1
        perm = DocPermission.objects.filter(
            doc=doc, target_type='group', target_id__in=group_ids
        ).aggregate(m=Max('permission'))['m']
        return _PERM_RANK.get(perm, -1)

    @staticmethod
    def _get_org_perm(user, doc):
        org_nodes = OrgUser.objects.filter(user=user).select_related('org_node')
        org_ids = set()
        for ou in org_nodes:
            org_ids.add(ou.org_node_id)
            # 向上追溯所有父节点
            node = ou.org_node
            while node.parent_id:
                org_ids.add(node.parent_id)
                node = node.parent
        if not org_ids:
            return -1
        perm = DocPermission.objects.filter(
            doc=doc, target_type='org', target_id__in=org_ids
        ).aggregate(m=Max('permission'))['m']
        return _PERM_RANK.get(perm, -1)

    @staticmethod
    def batch_get_permissions(user, docs: list) -> dict[int, str | None]:
        """批量计算用户对多篇文档的有效权限，避免 N+1 查询。

        Args:
            user: 当前用户
            docs: Doc 实例列表或 QuerySet

        Returns:
            dict[int, str | None]: doc_id → 'view'/'edit'/'admin'/None
        """
        if not user or not user.is_authenticated:
            return {doc.id: None for doc in docs}
        if user.is_superuser:
            return {doc.id: 'admin' for doc in docs}

        doc_ids = [doc.id for doc in docs]
        if not doc_ids:
            return {}

        # 1) 收集用户身份信息（一次查询）
        user_group_ids = set(GroupMember.objects.filter(user=user).values_list('group_id', flat=True))

        org_nodes = OrgUser.objects.filter(user=user).select_related('org_node')
        user_org_ids = set()
        for ou in org_nodes:
            user_org_ids.add(ou.org_node_id)
            node = ou.org_node
            while node.parent_id:
                user_org_ids.add(node.parent_id)
                node = node.parent

        # 2) 批量查询所有相关权限记录（一次查询）
        target_filters = Q(target_type='user', target_id=user.id)
        if user_group_ids:
            target_filters |= Q(target_type='group', target_id__in=user_group_ids)
        if user_org_ids:
            target_filters |= Q(target_type='org', target_id__in=user_org_ids)

        all_perms = DocPermission.objects.filter(
            doc_id__in=doc_ids,
        ).filter(target_filters).values_list('doc_id', 'target_type', 'permission')

        # 3) 按文档分组计算最佳权限
        doc_perm_map: dict[int, int] = {}
        for doc_id, target_type, perm_level in all_perms:
            rank = _PERM_RANK.get(perm_level, -1)
            current = doc_perm_map.get(doc_id, -1)
            if rank > current:
                doc_perm_map[doc_id] = rank

        # 4) 组装结果
        result = {}
        for doc in docs:
            did = doc.id
            best_rank = doc_perm_map.get(did, -1)
            if best_rank < 0 and doc.is_public:
                best_rank = 0
            perm_str = None
            for key, rank in _PERM_RANK.items():
                if rank == best_rank:
                    perm_str = key
                    break
            result[did] = perm_str

        return result

    @staticmethod
    def _is_doc_public(doc):
        return doc.is_public

    @staticmethod
    def get_users_with_permission(doc, min_permission='view'):
        """获取对文档拥有至少指定权限的所有用户 ID 列表。"""
        min_rank = _PERM_RANK.get(min_permission, 0)
        result = set()

        for perm in DocPermission.objects.filter(doc=doc).select_related():
            rank = _PERM_RANK.get(perm.permission, -1)
            if rank < min_rank:
                continue
            if perm.target_type == 'user':
                result.add(perm.target_id)
            elif perm.target_type == 'group':
                result.update(
                    GroupMember.objects.filter(group_id=perm.target_id)
                    .values_list('user_id', flat=True)
                )
            elif perm.target_type == 'org':
                node_ids = PermissionService._get_subtree_ids(perm.target_id)
                result.update(
                    OrgUser.objects.filter(org_node_id__in=node_ids)
                    .values_list('user_id', flat=True)
                )

        return list(result)

    @staticmethod
    def _get_subtree_ids(node_id):
        """获取某组织节点及其所有子孙节点 ID 列表。"""
        node = OrgNode.objects.only('path', 'depth').get(pk=node_id)
        return list(
            OrgNode.objects.filter(
                path__startswith=node.path
            ).values_list('pk', flat=True)
        )


# ---------------------------------------------------------------
#  DocService
# ---------------------------------------------------------------

class DocService:
    """文档服务：软删除、恢复、拖拽排序。"""

    @staticmethod
    @transaction.atomic
    def soft_delete(doc_id: int, user: User) -> dict:
        """标记删除文档及所有子文档。

        返回 {'deleted': N, 'children': [...]}
        """
        try:
            doc = Doc.objects.select_related('create_user').get(pk=doc_id)
        except Doc.DoesNotExist:
            return {'error': '文档不存在'}

        now = timezone.now()
        children = DocService._get_all_descendant_ids(doc_id)
        all_ids = [doc_id] + children

        updated = Doc.objects.filter(pk__in=all_ids).update(
            is_deleted=True, deleted_at=now, deleted_by=user
        )

        return {'deleted': updated, 'children': children}

    @staticmethod
    @transaction.atomic
    def restore(doc_id: int) -> dict:
        """恢复已删除文档及被级联删除的子文档。"""
        try:
            doc = Doc.objects.get(pk=doc_id)
        except Doc.DoesNotExist:
            return {'error': '文档不存在'}

        if not doc.is_deleted:
            return {'error': '文档未被删除'}

        # 获取同批次删除的子孙（含已删除的）
        children = DocService._get_all_descendant_ids(doc_id, include_deleted=True)
        all_ids = [doc_id] + children

        updated = Doc.objects.filter(pk__in=all_ids, is_deleted=True).update(
            is_deleted=False, deleted_at=None, deleted_by=None
        )

        return {'restored': updated}

    @staticmethod
    def _get_all_descendant_ids(doc_id: int, include_deleted: bool = False) -> list[int]:
        """递归获取所有子文档 ID。"""
        result = []
        queue = [doc_id]
        while queue:
            parent = queue.pop()
            qs = Doc.objects.filter(parent_doc=parent)
            if not include_deleted:
                qs = qs.exclude(is_deleted=True)
            children = list(qs.values_list('pk', flat=True))
            result.extend(children)
            queue.extend(children)
        return result

    @staticmethod
    @transaction.atomic
    def move(doc_id: int, new_parent_id: int | None, position: int, user: User) -> dict:
        """移动文档到新父级并设置排序位置。

        Args:
            doc_id: 被移动的文档 ID
            new_parent_id: 目标父文档 ID，None 表示移至项目根级
            position: 目标位置索引（0-based）
            user: 操作人
        """
        try:
            doc = Doc.objects.get(pk=doc_id)
        except Doc.DoesNotExist:
            return {'error': '源文档不存在'}

        if new_parent_id and new_parent_id != 0:
            try:
                target_parent = Doc.objects.get(pk=new_parent_id)
            except Doc.DoesNotExist:
                return {'error': '目标父文档不存在'}

            # 防循环：目标不能是源文档的子孙
            if new_parent_id in DocService._get_all_descendant_ids(doc_id):
                return {'error': '不能将文档移动到自身或子孙文档下'}
        else:
            new_parent_id = 0

        # 重新计算同级排序值
        siblings = list(
            Doc.objects.filter(parent_doc=new_parent_id)
            .exclude(pk=doc_id)
            .order_by('sort')
            .values_list('pk', 'sort')
        )

        # 间隙插入策略：position 位置插入
        if position <= 0:
            new_sort = (siblings[0][1] - 1000) if siblings else 1000
        elif position >= len(siblings):
            new_sort = siblings[-1][1] + 1000
        else:
            prev_sort = siblings[position - 1][1]
            next_sort = siblings[position][1]
            new_sort = (prev_sort + next_sort) // 2

        doc.parent_doc = new_parent_id
        doc.sort = new_sort
        doc.save(update_fields=['parent_doc', 'sort', 'modify_time'])

        # 如果间隙不足（差值 < 10），触发同级全量重排
        if new_sort > 0 and abs(new_sort - (siblings[position - 1][1] if position > 0 else new_sort)) < 10:
            DocService._rebalance_siblings(new_parent_id)

        return {'success': True, 'doc_id': doc_id, 'parent_id': new_parent_id, 'sort': new_sort}

    @staticmethod
    def _rebalance_siblings(parent_id: int):
        """同级全量重排：按 1000 步长重新分配排序值。"""
        siblings = Doc.objects.filter(parent_doc=parent_id).order_by('sort')
        for i, sib in enumerate(siblings):
            sib.sort = (i + 1) * 1000
            sib.save(update_fields=['sort'])


# ---------------------------------------------------------------
#  NotificationService
# ---------------------------------------------------------------

class NotificationService:
    """通知服务：创建站内通知 + 通过通道管理器分发到各通知渠道。"""

    # notification_type → UserProfile.notify_settings 中的邮件开关 key（保留向后兼容）
    _EMAIL_PREF_KEY_MAP = {
        'comment': 'email_comment',
        'reply': 'email_comment',
        'mention': 'email_mention',
        'doc_change': 'email_doc_change',
        'perm_change': 'email_perm_change',
        'perm_apply': 'email_perm_apply',
    }

    @staticmethod
    def send(recipient: User, notification_type: str, title: str,
             sender: User | None = None, body: str = '', link: str = '',
             send_email: bool = False, context: dict | None = None):
        """创建一条通知并通过通道管理器分发。

        context 可含: doc_name, comment_content, change_type, perm_detail 等模板变量。
        send_email 参数保留向后兼容：为 True 时确保 email 通道在路由中。
        """
        notif = Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            body=body,
            link=link,
        )

        # 通过通道管理器分发
        try:
            from .notification_channels import get_channel_manager
            manager = get_channel_manager()
            manager.send(notif)
        except Exception:
            logger.exception('NotificationService: 通道分发异常')

        return notif

    @staticmethod
    def send_bulk(recipients: list[User], notification_type: str, title: str,
                  sender: User | None = None, body: str = '', link: str = ''):
        """批量创建通知。"""
        objs = [
            Notification(
                recipient=r, sender=sender, notification_type=notification_type,
                title=title, body=body, link=link,
            )
            for r in recipients
        ]
        Notification.objects.bulk_create(objs, batch_size=200)

    @staticmethod
    def get_unread_count(user: User) -> int:
        return Notification.objects.filter(recipient=user, is_read=False).count()

    @staticmethod
    def mark_read(notification_id: int, user: User):
        Notification.objects.filter(pk=notification_id, recipient=user).update(is_read=True)

    @staticmethod
    def mark_all_read(user: User):
        Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)

    # ---------- 点赞聚合 ----------

    @staticmethod
    def _upsert_like_notification(doc, liker, is_like: bool, total_count: int):
        """点赞/取消时更新文档作者的聚合通知（同文档同日汇总为一条）。"""
        from datetime import timedelta

        author = doc.create_user
        if not author:
            return

        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        doc_link = f'/pages/{doc.id}/'

        existing = Notification.objects.filter(
            recipient=author,
            notification_type='doc_like',
            link=doc_link,
            created_at__gte=today,
            created_at__lt=tomorrow,
        ).first()

        liker_name = liker.first_name or liker.username

        if is_like:
            # 新增点赞
            if existing:
                # 更新已有聚合通知
                body = existing.body
                # 解析已有用户列表：从 body 中提取
                names, old_count = NotificationService._parse_like_body(body)
                if liker_name not in names:
                    names.append(liker_name)
                new_count = total_count
                existing.title = f'文档《{doc.name}》收到 {new_count} 个赞'
                existing.body = NotificationService._format_like_body(names, new_count, doc.name)
                existing.is_read = False
                existing.created_at = timezone.now()  # 更新时间戳使其排前
                existing.save(update_fields=['title', 'body', 'is_read', 'created_at'])
            else:
                NotificationService.send(
                    recipient=author, notification_type='doc_like',
                    title=f'文档《{doc.name}》收到 1 个赞',
                    sender=liker,
                    body=f'{liker_name} 赞了你的文档《{doc.name}》',
                    link=doc_link,
                )
        else:
            # 取消点赞
            if not existing:
                return
            if total_count == 0:
                existing.delete()
                return
            # 更新已有聚合通知
            names, _ = NotificationService._parse_like_body(existing.body)
            if liker_name in names:
                names.remove(liker_name)
            if not names:
                existing.delete()
                return
            existing.title = f'文档《{doc.name}》收到 {total_count} 个赞'
            existing.body = NotificationService._format_like_body(names, total_count, doc.name)
            existing.save(update_fields=['title', 'body'])

    @staticmethod
    def _parse_like_body(body: str):
        """从点赞聚合通知 body 中解析出用户名列表和数量。
        body格式: "张三、李四 等 3 人赞了你的文档《xxx》"
        或: "张三 赞了你的文档《xxx》"
        """
        import re
        if not body:
            return [], 0
        # 提取"赞了"之前的部分
        match = re.match(r'^(.+?)(?: 等 \d+ 人)?赞了', body)
        if not match:
            return [], 0
        names_str = match.group(1)
        names = [n.strip() for n in names_str.split('、') if n.strip()]
        # 提取人数
        count_match = re.search(r'等 (\d+) 人', body)
        if count_match:
            count = int(count_match.group(1))
        else:
            count = len(names)
        return names, count

    @staticmethod
    def _format_like_body(names: list, total_count: int, doc_name: str):
        """格式化点赞通知 body。"""
        if not names:
            return ''
        display_names = names[:5]  # 最多展示5个用户名
        if total_count <= 5:
            name_str = '、'.join(display_names)
            return f'{name_str} 赞了你的文档《{doc_name}》'
        else:
            name_str = '、'.join(display_names)
            return f'{name_str} 等 {total_count} 人赞了你的文档《{doc_name}》'
