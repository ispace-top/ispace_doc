"""
v1.0 核心服务单元测试

覆盖：PermissionService、DocService、NotificationService
"""

from django.test import TestCase, RequestFactory
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.models import User

from backend.apps.doc.models import (
    Doc, DocPermission, Group, GroupMember, OrgNode, OrgUser,
    Notification, UserProfile, InlineComment,
)
from backend.apps.doc.services import PermissionService, DocService, NotificationService


# ================================================================
#  PermissionService 测试
# ================================================================

class PermissionServiceTest(TestCase):
    """有效权限计算引擎测试"""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('tester', password='pass')
        self.other = User.objects.create_user('other', password='pass')
        self.superuser = User.objects.create_superuser('admin', password='pass')
        self.project = Project.objects.create(name='test-proj', role=1, intro='', create_user=self.user)
        self.doc = Doc.objects.create(
            name='test-doc', top_doc=self.project.pk, create_user=self.user
        )

    # ---- 无权限 ----

    def test_no_user_returns_none(self):
        self.assertIsNone(PermissionService.get_effective_permission(None, self.doc))

    def test_unauthenticated_returns_none(self):
        user = User()
        self.assertIsNone(PermissionService.get_effective_permission(user, self.doc))

    # ---- 超级管理员 ----

    def test_superuser_always_admin(self):
        self.assertEqual(
            PermissionService.get_effective_permission(self.superuser, self.doc),
            'admin'
        )

    # ---- 直接用户权限 ----

    def test_direct_user_view_permission(self):
        DocPermission.objects.create(
            doc=self.doc, target_type='user', target_id=self.user.id,
            permission='view', granted_by=self.superuser
        )
        self.assertEqual(
            PermissionService.get_effective_permission(self.user, self.doc),
            'view'
        )

    def test_direct_user_edit_permission(self):
        DocPermission.objects.create(
            doc=self.doc, target_type='user', target_id=self.user.id,
            permission='edit', granted_by=self.superuser
        )
        self.assertEqual(
            PermissionService.get_effective_permission(self.user, self.doc),
            'edit'
        )

    def test_direct_user_admin_permission(self):
        DocPermission.objects.create(
            doc=self.doc, target_type='user', target_id=self.user.id,
            permission='admin', granted_by=self.superuser
        )
        self.assertEqual(
            PermissionService.get_effective_permission(self.user, self.doc),
            'admin'
        )

    # ---- 分组权限 ----

    def test_group_permission(self):
        group = Group.objects.create(name='editors', owner=self.user)
        GroupMember.objects.create(group=group, user=self.user)
        DocPermission.objects.create(
            doc=self.doc, target_type='group', target_id=group.id,
            permission='edit', granted_by=self.superuser
        )
        self.assertEqual(
            PermissionService.get_effective_permission(self.user, self.doc),
            'edit'
        )

    def test_group_permission_non_member_no_effect(self):
        group = Group.objects.create(name='editors', owner=self.user)
        # other is NOT in the group
        DocPermission.objects.create(
            doc=self.doc, target_type='group', target_id=group.id,
            permission='edit', granted_by=self.superuser
        )
        self.assertIsNone(
            PermissionService.get_effective_permission(self.other, self.doc)
        )

    # ---- 组织节点权限 ----

    def test_org_node_permission(self):
        root = OrgNode.objects.create(name='公司', depth=0, path='1/')
        OrgUser.objects.create(org_node=root, user=self.user)
        DocPermission.objects.create(
            doc=self.doc, target_type='org', target_id=root.id,
            permission='view', granted_by=self.superuser
        )
        self.assertEqual(
            PermissionService.get_effective_permission(self.user, self.doc),
            'view'
        )

    def test_org_ancestor_inheritance(self):
        root = OrgNode.objects.create(name='公司', depth=0, path='1/')
        child = OrgNode.objects.create(name='研发部', parent=root, depth=1, path='1/2/')
        OrgUser.objects.create(org_node=child, user=self.user)
        # 权限授予根节点，子节点用户应继承
        DocPermission.objects.create(
            doc=self.doc, target_type='org', target_id=root.id,
            permission='edit', granted_by=self.superuser
        )
        self.assertEqual(
            PermissionService.get_effective_permission(self.user, self.doc),
            'edit'
        )

    # ---- 三线合并取最大 ----

    def test_merge_takes_max_permission(self):
        # 用户直接 view，分组 edit，组织 admin → 取 admin
        group = Group.objects.create(name='g1', owner=self.user)
        GroupMember.objects.create(group=group, user=self.user)
        root = OrgNode.objects.create(name='org1', depth=0, path='1/')
        OrgUser.objects.create(org_node=root, user=self.user)

        DocPermission.objects.create(doc=self.doc, target_type='user', target_id=self.user.id,
                                     permission='view', granted_by=self.superuser)
        DocPermission.objects.create(doc=self.doc, target_type='group', target_id=group.id,
                                     permission='edit', granted_by=self.superuser)
        DocPermission.objects.create(doc=self.doc, target_type='org', target_id=root.id,
                                     permission='admin', granted_by=self.superuser)

        self.assertEqual(
            PermissionService.get_effective_permission(self.user, self.doc),
            'admin'
        )

    # ---- 公开文档默认 view ----

    def test_public_doc_defaults_to_view(self):
        proj = Project.objects.create(name='public-proj', role=0, intro='', create_user=self.user)
        doc = Doc.objects.create(name='pub-doc', top_doc=proj.pk, create_user=self.user)
        self.assertEqual(
            PermissionService.get_effective_permission(self.other, doc),
            'view'
        )

    # ---- 缓存 ----

    def test_permission_result_is_cached(self):
        DocPermission.objects.create(
            doc=self.doc, target_type='user', target_id=self.user.id,
            permission='edit', granted_by=self.superuser
        )
        first = PermissionService.get_effective_permission(self.user, self.doc)
        # 删除权限记录，缓存仍应返回之前的值
        DocPermission.objects.filter(doc=self.doc).delete()
        second = PermissionService.get_effective_permission(self.user, self.doc)
        self.assertEqual(first, second)
        self.assertEqual(second, 'edit')

    def test_cache_invalidation(self):
        DocPermission.objects.create(
            doc=self.doc, target_type='user', target_id=self.user.id,
            permission='edit', granted_by=self.superuser
        )
        PermissionService.get_effective_permission(self.user, self.doc)
        PermissionService.invalidate_cache(self.doc.id)
        # 缓存失效后，无权限记录应返回 None
        DocPermission.objects.filter(doc=self.doc).delete()
        self.assertIsNone(
            PermissionService.get_effective_permission(self.user, self.doc)
        )

    # ---- get_users_with_permission ----

    def test_get_users_with_permission(self):
        DocPermission.objects.create(
            doc=self.doc, target_type='user', target_id=self.user.id,
            permission='edit', granted_by=self.superuser
        )
        users = PermissionService.get_users_with_permission(self.doc, min_permission='view')
        self.assertIn(self.user.id, users)

    def test_get_users_with_permission_enforces_min_rank(self):
        DocPermission.objects.create(
            doc=self.doc, target_type='user', target_id=self.user.id,
            permission='view', granted_by=self.superuser
        )
        users = PermissionService.get_users_with_permission(self.doc, min_permission='edit')
        self.assertNotIn(self.user.id, users)


# ================================================================
#  DocService 测试
# ================================================================

class DocServiceTest(TestCase):
    """文档软删除、恢复、拖拽排序测试"""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('writer', password='pass')
        self.project = Project.objects.create(name='proj', role=1, intro='', create_user=self.user)
        self.doc = Doc.objects.create(
            name='root', top_doc=self.project.pk, create_user=self.user, sort=1000
        )
        self.child1 = Doc.objects.create(
            name='child1', top_doc=self.project.pk, create_user=self.user,
            parent_doc=self.doc.pk, sort=1000
        )
        self.child2 = Doc.objects.create(
            name='child2', top_doc=self.project.pk, create_user=self.user,
            parent_doc=self.doc.pk, sort=2000
        )

    # ---- 软删除 ----

    def test_soft_delete_sets_flags(self):
        result = DocService.soft_delete(self.doc.id, self.user)
        self.assertGreaterEqual(result['deleted'], 1)
        self.doc.refresh_from_db()
        self.assertTrue(self.doc.is_deleted)
        self.assertIsNotNone(self.doc.deleted_at)
        self.assertEqual(self.doc.deleted_by, self.user)

    def test_soft_delete_cascades_to_children(self):
        result = DocService.soft_delete(self.doc.id, self.user)
        self.assertEqual(result['deleted'], 3)  # root + child1 + child2
        self.assertEqual(len(result['children']), 2)

    def test_soft_delete_nonexistent_returns_error(self):
        result = DocService.soft_delete(99999, self.user)
        self.assertIn('error', result)

    # ---- 恢复 ----

    def test_restore_clears_flags(self):
        DocService.soft_delete(self.doc.id, self.user)
        result = DocService.restore(self.doc.id)
        self.assertGreaterEqual(result['restored'], 1)
        self.doc.refresh_from_db()
        self.assertFalse(self.doc.is_deleted)
        self.assertIsNone(self.doc.deleted_at)
        self.assertIsNone(self.doc.deleted_by)

    def test_restore_cascades_to_children(self):
        DocService.soft_delete(self.doc.id, self.user)
        result = DocService.restore(self.doc.id)
        self.assertEqual(result['restored'], 3)

    def test_restore_not_deleted_returns_error(self):
        result = DocService.restore(self.doc.id)
        self.assertIn('error', result)

    def test_restore_nonexistent_returns_error(self):
        result = DocService.restore(99999)
        self.assertIn('error', result)

    # ---- 移动/排序 ----

    def test_move_to_new_parent(self):
        new_parent = Doc.objects.create(
            name='new-parent', top_doc=self.project.pk, create_user=self.user
        )
        result = DocService.move(self.child1.id, new_parent.id, 0, self.user)
        self.assertTrue(result['success'])
        self.child1.refresh_from_db()
        self.assertEqual(self.child1.parent_doc, new_parent.id)

    def test_move_to_root_level(self):
        result = DocService.move(self.child1.id, None, 0, self.user)
        self.assertTrue(result['success'])
        self.child1.refresh_from_db()
        self.assertEqual(self.child1.parent_doc, 0)

    def test_move_prevents_circular_reference(self):
        # 不能将 root 移动到 child1 下面（child1 是 root 的子孙）
        result = DocService.move(self.doc.id, self.child1.id, 0, self.user)
        self.assertIn('error', result)

    def test_move_nonexistent_returns_error(self):
        result = DocService.move(99999, 0, 0, self.user)
        self.assertIn('error', result)

    def test_move_assigns_gap_sort_value(self):
        result = DocService.move(self.child2.id, self.doc.id, 0, self.user)
        self.assertTrue(result['success'])
        self.child2.refresh_from_db()
        # child1 的 sort 是 1000，放在 position 0 应该在 child1 之前
        self.assertLess(self.child2.sort, self.child1.sort)


# ================================================================
#  NotificationService 测试
# ================================================================

class NotificationServiceTest(TestCase):
    """通知服务测试"""

    def setUp(self):
        cache.clear()
        self.sender = User.objects.create_user('sender', password='pass')
        self.recipient = User.objects.create_user('recipient', password='pass',
                                                   email='r@test.com')
        self.project = Project.objects.create(name='proj', role=1, intro='', create_user=self.sender)
        self.doc = Doc.objects.create(
            name='test-doc', top_doc=self.project.pk, create_user=self.sender
        )

    # ---- 创建通知 ----

    def test_send_creates_notification(self):
        notif = NotificationService.send(
            recipient=self.recipient,
            notification_type='comment',
            title='测试通知',
            body='这是测试内容',
            link='/pages/1/',
        )
        self.assertIsNotNone(notif.pk)
        self.assertEqual(notif.recipient, self.recipient)
        self.assertEqual(notif.notification_type, 'comment')
        self.assertFalse(notif.is_read)

    def test_send_with_sender(self):
        notif = NotificationService.send(
            recipient=self.recipient,
            notification_type='comment',
            title='有人评论',
            sender=self.sender,
        )
        self.assertEqual(notif.sender, self.sender)

    def test_send_bulk(self):
        u2 = User.objects.create_user('u2', password='pass')
        u3 = User.objects.create_user('u3', password='pass')
        NotificationService.send_bulk(
            recipients=[self.recipient, u2, u3],
            notification_type='system',
            title='批量通知',
            body='测试',
        )
        count = Notification.objects.filter(notification_type='system').count()
        self.assertEqual(count, 3)

    # ---- 未读计数 ----

    def test_unread_count(self):
        Notification.objects.create(recipient=self.recipient, notification_type='comment',
                                     title='t1')
        Notification.objects.create(recipient=self.recipient, notification_type='comment',
                                     title='t2', is_read=True)
        Notification.objects.create(recipient=self.recipient, notification_type='reply',
                                     title='t3')
        self.assertEqual(NotificationService.get_unread_count(self.recipient), 2)

    # ---- 标记已读 ----

    def test_mark_read(self):
        notif = Notification.objects.create(recipient=self.recipient, notification_type='comment',
                                             title='t1')
        NotificationService.mark_read(notif.id, self.recipient)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_mark_all_read(self):
        Notification.objects.create(recipient=self.recipient, notification_type='comment',
                                     title='t1')
        Notification.objects.create(recipient=self.recipient, notification_type='reply',
                                     title='t2')
        NotificationService.mark_all_read(self.recipient)
        unread = NotificationService.get_unread_count(self.recipient)
        self.assertEqual(unread, 0)

    # ---- 点赞聚合 _upsert_like_notification ----

    def test_upsert_like_creates_new_notification(self):
        doc = Doc.objects.create(
            name='liked-doc', top_doc=self.project.pk, create_user=self.recipient
        )
        NotificationService._upsert_like_notification(doc, self.sender, True, 1)
        notif = Notification.objects.filter(
            recipient=self.recipient, notification_type='doc_like'
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn('1', notif.title)
        self.assertIn(str(self.sender.username), notif.body)

    def test_upsert_like_aggregates_same_day(self):
        doc = Doc.objects.create(
            name='liked-doc', top_doc=self.project.pk, create_user=self.recipient
        )
        NotificationService._upsert_like_notification(doc, self.sender, True, 1)
        u2 = User.objects.create_user('liker2', password='pass')
        NotificationService._upsert_like_notification(doc, u2, True, 2)
        notif = Notification.objects.filter(
            recipient=self.recipient, notification_type='doc_like'
        ).first()
        self.assertIn('2', notif.title)

    def test_upsert_unlike_deletes_when_zero(self):
        doc = Doc.objects.create(
            name='liked-doc', top_doc=self.project.pk, create_user=self.recipient
        )
        NotificationService._upsert_like_notification(doc, self.sender, True, 1)
        NotificationService._upsert_like_notification(doc, self.sender, False, 0)
        exists = Notification.objects.filter(
            recipient=self.recipient, notification_type='doc_like'
        ).exists()
        self.assertFalse(exists)


# ================================================================
#  AuditLogMiddleware 测试
# ================================================================

from backend.apps.admin.middleware.audit_middleware import AuditLogMiddleware
from backend.apps.admin.models import AuditLog


class AuditLogMiddlewareTest(TestCase):
    """审计日志中间件测试"""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = AuditLogMiddleware(lambda r: None)
        self.user = User.objects.create_user('logger', password='pass')

    def test_no_audit_data_creates_no_log(self):
        request = self.factory.get('/some-page/')
        request.user = self.user
        response = self.middleware.process_response(request, None)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_audit_data_creates_log_entry(self):
        request = self.factory.get('/api/test/')
        request.user = self.user
        request._audit_log = {
            'action': 'delete',
            'target_type': 'doc',
            'target_id': 42,
            'detail': '删除文档《测试》',
        }
        self.middleware.process_response(request, None)
        log = AuditLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action, 'delete')
        self.assertEqual(log.target_type, 'doc')
        self.assertEqual(log.target_id, 42)
        self.assertEqual(log.user, self.user)

    def test_get_ip_from_x_forwarded_for(self):
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 10.0.0.2'
        request.user = self.user
        request._audit_log = {'action': 'test'}
        self.middleware.process_response(request, None)
        log = AuditLog.objects.first()
        self.assertEqual(log.ip_address, '10.0.0.1')

    def test_get_ip_from_remote_addr(self):
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = self.user
        request._audit_log = {'action': 'test'}
        self.middleware.process_response(request, None)
        log = AuditLog.objects.first()
        self.assertEqual(log.ip_address, '192.168.1.1')

    def test_unauthenticated_user_no_log(self):
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get('/')
        request.user = AnonymousUser()
        request._audit_log = {'action': 'test'}
        self.middleware.process_response(request, None)
        self.assertEqual(AuditLog.objects.count(), 0)
