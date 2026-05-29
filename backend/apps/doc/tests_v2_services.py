"""v2.0 服务层单元测试（13.1.2）。

覆盖: PermissionService / DocService / NotificationService /
       StorageBackend / SearchBackend / AuthBackend
"""
from io import BytesIO

from django.test import TestCase
from django.core.cache import cache
from django.contrib.auth.models import User
from django.utils import timezone

from backend.apps.doc.models import Doc, DocPermission, Group, GroupMember, OrgNode, OrgUser
from backend.apps.doc.services import PermissionService, DocService, NotificationService


# ================================================================
# PermissionService v1.0
# ================================================================

class PermissionServiceTest(TestCase):
    """有效权限计算引擎测试"""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('tester', password='pass')
        self.other = User.objects.create_user('other', password='pass')
        self.superuser = User.objects.create_superuser('admin', 'admin@test.com', password='pass')
        self.doc = Doc.objects.create(name='test-doc', create_user=self.user)

    def test_no_user_returns_none(self):
        self.assertIsNone(PermissionService.get_effective_permission(None, self.doc))

    def test_superuser_always_admin(self):
        self.assertEqual(
            PermissionService.get_effective_permission(self.superuser, self.doc),
            'admin'
        )

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

    def test_group_permission(self):
        group = Group.objects.create(name='Test Group', owner=self.superuser)
        GroupMember.objects.create(group=group, user=self.user)
        DocPermission.objects.create(
            doc=self.doc, target_type='group', target_id=group.id,
            permission='view', granted_by=self.superuser
        )
        self.assertEqual(
            PermissionService.get_effective_permission(self.user, self.doc),
            'view'
        )

    def test_org_permission(self):
        root = OrgNode.objects.create(name='Root', path='/root', depth=0)
        OrgUser.objects.create(org_node=root, user=self.user)
        DocPermission.objects.create(
            doc=self.doc, target_type='org', target_id=root.id,
            permission='edit', granted_by=self.superuser
        )
        self.assertEqual(
            PermissionService.get_effective_permission(self.user, self.doc),
            'edit'
        )

    def test_permission_wins_over_public(self):
        self.doc.is_public = False
        self.doc.save()
        DocPermission.objects.create(
            doc=self.doc, target_type='user', target_id=self.user.id,
            permission='view', granted_by=self.superuser
        )
        self.assertEqual(
            PermissionService.get_effective_permission(self.user, self.doc),
            'view'
        )

    def test_is_doc_public(self):
        self.doc.is_public = True
        self.assertTrue(PermissionService._is_doc_public(self.doc))

        self.doc.is_public = False
        self.assertFalse(PermissionService._is_doc_public(self.doc))

    def test_cache_invalidation(self):
        # invalidate_cache 递增版本号，后续查询使用新 key
        old_version = cache.get(f'permver:{self.doc.id}')
        PermissionService.invalidate_cache(self.doc.id)
        new_version = cache.get(f'permver:{self.doc.id}')
        self.assertNotEqual(old_version, new_version)

    def test_batch_get_permissions(self):
        doc2 = Doc.objects.create(name='doc2', create_user=self.user)
        DocPermission.objects.create(
            doc=self.doc, target_type='user', target_id=self.user.id,
            permission='edit', granted_by=self.superuser
        )
        result = PermissionService.batch_get_permissions(self.user, [self.doc, doc2])
        self.assertEqual(result[self.doc.id], 'edit')
        # doc2 公开，因此至少有 view 权限
        self.assertIsNotNone(result.get(doc2.id))


# ================================================================
# DocService v1.0
# ================================================================

class DocServiceTest(TestCase):
    """文档服务测试"""

    def setUp(self):
        self.user = User.objects.create_user('author', password='pass')
        self.doc = Doc.objects.create(name='Test Doc', create_user=self.user)

    def test_soft_delete(self):
        result = DocService.soft_delete(self.doc.id, self.user)
        self.assertIn('deleted', result)
        self.doc.refresh_from_db()
        self.assertTrue(self.doc.is_deleted)

    def test_restore(self):
        DocService.soft_delete(self.doc.id, self.user)
        result = DocService.restore(self.doc.id)
        self.assertIn('restored', result)
        self.doc.refresh_from_db()
        self.assertFalse(self.doc.is_deleted)

    def test_move_document(self):
        parent = Doc.objects.create(name='Parent', create_user=self.user)
        result = DocService.move(self.doc.id, parent.id, 0, self.user)
        self.assertTrue(result.get('success'))
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.parent_doc, parent.id)

    def test_soft_delete_not_found(self):
        result = DocService.soft_delete(99999, self.user)
        self.assertIn('error', result)


# ================================================================
# NotificationService v1.0
# ================================================================

class NotificationServiceTest(TestCase):
    """通知服务测试"""

    def setUp(self):
        self.sender = User.objects.create_user('sender', password='pass')
        self.recipient = User.objects.create_user('recipient', password='pass')
        self.doc = Doc.objects.create(name='Doc', create_user=self.sender)

    def test_send_notification(self):
        NotificationService.send(
            recipient=self.recipient,
            notification_type='perm',
            title='权限变更',
            body='您已被授予文档查看权限',
            sender=self.sender,
            context={'doc_name': self.doc.name},
        )
        from backend.apps.doc.models import Notification
        count = Notification.objects.filter(recipient=self.recipient).count()
        self.assertEqual(count, 1)

    def test_unread_count(self):
        NotificationService.send(
            recipient=self.recipient, notification_type='perm',
            title='Test', body='Body', sender=self.sender
        )
        count = NotificationService.get_unread_count(self.recipient)
        self.assertEqual(count, 1)


# ================================================================
# StorageBackend
# ================================================================

class StorageBackendTest(TestCase):
    """存储抽象层测试"""

    def test_local_backend_upload_get_url_exists(self):
        from backend.apps.doc.storage.local import LocalStorageBackend
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalStorageBackend(base_dir=tmpdir, base_url='/media/')
            content = BytesIO(b'Hello iSpaceDoc')
            key = 'test/hello.txt'
            result = backend.upload(content, key, 'text/plain')
            self.assertTrue(backend.exists(key))
            url = backend.get_url(key)
            self.assertIn(key, url)
            backend.delete(key)
            self.assertFalse(backend.exists(key))

    def test_local_backend_default_dir(self):
        from backend.apps.doc.storage.local import LocalStorageBackend
        backend = LocalStorageBackend()
        self.assertIsNotNone(backend._base_dir)

    def test_router_resolve_by_type(self):
        from backend.apps.doc.storage.router import StorageRouter
        router = StorageRouter()
        backend = router.resolve('image/png', 1024)
        self.assertIsNotNone(backend)


# ================================================================
# JWT Auth Backend (FastAPI)
# ================================================================

class JWTAuthTest(TestCase):
    """JWT 认证体系测试"""

    def setUp(self):
        self.user = User.objects.create_user('jwtuser', password='pass')

    def test_create_access_token(self):
        from backend.fastapi_app.auth import create_access_token, decode_token
        token = create_access_token(user_id=self.user.id, username='jwtuser')
        payload = decode_token(token)
        self.assertEqual(payload['sub'], str(self.user.id))
        self.assertEqual(payload['type'], 'access')

    def test_create_refresh_token(self):
        from backend.fastapi_app.auth import create_refresh_token, decode_token
        token = create_refresh_token(user_id=self.user.id)
        payload = decode_token(token)
        self.assertEqual(payload['sub'], str(self.user.id))
        self.assertEqual(payload['type'], 'refresh')

    def test_decode_invalid_token(self):
        from backend.fastapi_app.auth import decode_token
        result = decode_token('invalid.token.here')
        self.assertIsNone(result)

    def test_password_hashing(self):
        from backend.fastapi_app.auth import hash_password, verify_password
        hashed = hash_password('short')
        self.assertTrue(verify_password('short', hashed))
        self.assertFalse(verify_password('wrong', hashed))
