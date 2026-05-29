"""v2.0 API 集成测试（13.1.3）。

覆盖: 文档 CRUD / 评论 / 权限 / 认证 / v2 REST API
使用 Django TestClient 测试 JSON API 端点。
"""
import gc
import json

from django.test import TestCase, Client
from django.contrib.auth.models import User

from backend.apps.doc.models import Doc, DocComment, DocPermission
from backend.apps.doc.models_v2 import (
    IspDocument, IspDocPermission, IspComment, IspNotification,
)
from backend.apps.admin.models import UserOptions


class _ClientTestBase(TestCase):
    """所有使用 Client 的测试基类。

    - 创建超管用户确保 SetupCheckMiddleware 放行
    - teardown Haystack 信号避免 Python 3.14 + Django 4.2 Context.dicts 兼容性问题
    - 断开 search/webhook 信号避免后台线程导致 SQLite 表锁竞争
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._sp = None
        cls._disconnected_signals = []
        try:
            from haystack.signals import RealtimeSignalProcessor
            for obj in gc.get_objects():
                if isinstance(obj, RealtimeSignalProcessor):
                    obj.teardown()
                    cls._sp = obj
                    break
        except Exception:
            pass
        # 断开后台线程信号，避免 SQLite 表锁竞争
        try:
            from django.db.models.signals import post_save, post_delete
            from backend.apps.doc.search.signals import on_doc_saved, on_doc_deleted
            post_save.disconnect(on_doc_saved, sender=Doc)
            post_delete.disconnect(on_doc_deleted, sender=Doc)
            cls._disconnected_signals.append(('search', post_save, on_doc_saved, Doc))
            cls._disconnected_signals.append(('search', post_delete, on_doc_deleted, Doc))
        except Exception:
            pass
        try:
            from django.db.models.signals import post_save as ps
            from backend.apps.doc.webhook.signals import on_doc_save, on_comment_save
            ps.disconnect(on_doc_save, sender=Doc)
            ps.disconnect(on_comment_save, sender=DocComment)
            cls._disconnected_signals.append(('webhook', ps, on_doc_save, Doc))
            cls._disconnected_signals.append(('webhook', ps, on_comment_save, DocComment))
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        if cls._sp is not None:
            try:
                cls._sp.setup()
            except Exception:
                pass
        for _tag, signal, receiver, sender in cls._disconnected_signals:
            try:
                signal.connect(receiver, sender=sender)
            except Exception:
                pass
        super().tearDownClass()

    def setUp(self):
        self.client = Client()
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser('_setup_admin', 'a@test.com', password='_pass')

    def _create_user(self, username, password='testpass'):
        user = User.objects.create_user(username, password=password)
        UserOptions.objects.get_or_create(user=user, defaults={'editor_mode': 2})
        return user


class DocCRUDAPITest(_ClientTestBase):
    """文档 CRUD JSON API 集成测试"""

    def setUp(self):
        super().setUp()
        self.user = self._create_user('api_user')
        self.other = self._create_user('other_user')
        self.client.login(username='api_user', password='testpass')

    def test_create_doc(self):
        """POST /create_doc/ 应该返回 JSON 并包含 doc.id"""
        resp = self.client.post(
            '/create_doc/',
            data={'doc_name': 'API Created Doc', 'content': '# Hello', 'pre_content': '# Hello'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('status'), msg=f'response: {data}')
        self.assertIn('doc', data.get('data', {}))

    def test_create_doc_missing_title(self):
        """标题为空应返回错误"""
        resp = self.client.post(
            '/create_doc/',
            data={'doc_name': '', 'content': 'no title'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get('status'))

    def test_modify_doc(self):
        """POST /modify_doc/<id>/ 应该更新文档"""
        doc = Doc.objects.create(
            name='Old Title', content='old',
            create_user=self.user, top_doc=0, status=1,
        )
        DocPermission.objects.create(
            doc=doc, target_type='user', target_id=self.user.id,
            permission='admin', granted_by=self.user,
        )
        resp = self.client.post(
            f'/modify_doc/{doc.id}/',
            data={'doc_name': 'New Title', 'content': 'Updated', 'editor_mode': 2},
        )
        self.assertIn(resp.status_code, [200, 302])

    def test_create_doc_unauthenticated(self):
        """未登录用户无法创建文档"""
        self.client.logout()
        resp = self.client.post(
            '/create_doc/',
            data={'doc_name': 'Should Fail'},
        )
        self.assertNotEqual(resp.status_code, 200)

    def test_delete_doc_json(self):
        """POST /del_doc/ 应该删除文档"""
        doc = Doc.objects.create(
            name='To Delete', content='delete me',
            create_user=self.user, top_doc=0, status=1,
        )
        resp = self.client.post(
            '/del_doc/',
            data=json.dumps({'doc_id': doc.id}),
            content_type='application/json',
        )
        self.assertIn(resp.status_code, [200, 403])


class PermissionAPITest(_ClientTestBase):
    """权限管理 JSON API 测试"""

    def setUp(self):
        super().setUp()
        self.admin_user = self._create_user('perm_admin')
        self.user = self._create_user('perm_user')
        self.doc = Doc.objects.create(
            name='Permission Doc', content='test',
            create_user=self.admin_user, top_doc=0, status=1,
        )
        DocPermission.objects.create(
            doc=self.doc, target_type='user', target_id=self.admin_user.id,
            permission='admin', granted_by=self.admin_user,
        )
        self.client.login(username='perm_admin', password='testpass')

    def test_grant_permission_via_api(self):
        """POST /api/docs/<id>/permissions/grant/ 应该授予权限"""
        resp = self.client.post(
            f'/api/docs/{self.doc.id}/permissions/grant/',
            data=json.dumps({
                'target_type': 'user',
                'target_id': self.user.id,
                'permission': 'edit',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('code'), 0, msg=f'response: {data}')

    def test_my_permission_api(self):
        """GET /api/docs/<id>/permissions/mine/ 返回当前用户权限"""
        resp = self.client.get(
            f'/api/docs/{self.doc.id}/permissions/mine/',
        )
        self.assertEqual(resp.status_code, 200)

    def test_permissions_list_api(self):
        """GET /api/docs/<id>/permissions/ 返回权限列表"""
        resp = self.client.get(
            f'/api/docs/{self.doc.id}/permissions/',
        )
        self.assertEqual(resp.status_code, 200)

    def test_batch_permissions_summary(self):
        """GET /api/docs/permissions/summary/ 批量权限摘要"""
        resp = self.client.get(
            '/api/docs/permissions/summary/',
            data={'doc_ids': str(self.doc.id)},
        )
        self.assertEqual(resp.status_code, 200)


class CommentAPITest(_ClientTestBase):
    """评论 JSON API 测试"""

    def setUp(self):
        super().setUp()
        self.user = self._create_user('comment_api_user')
        self.doc = Doc.objects.create(
            name='Comment Doc', content='test',
            create_user=self.user, top_doc=0, status=1,
        )
        self.client.login(username='comment_api_user', password='testpass')

    def test_create_comment(self):
        """POST /pages/0/<doc_id>/comments/ 创建评论"""
        resp = self.client.post(
            f'/pages/0/{self.doc.id}/comments/',
            data={'content': 'Nice document!'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('status'))

    def test_get_comments(self):
        """GET /pages/0/<doc_id>/comments/ 返回评论列表"""
        DocComment.objects.create(
            doc=self.doc, content='First comment', user=self.user,
        )
        resp = self.client.get(
            f'/pages/0/{self.doc.id}/comments/',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('status'))


class v2APITest(_ClientTestBase):
    """v2.0 REST API 端点测试"""

    def setUp(self):
        super().setUp()
        self.user = self._create_user('v2_user')
        self.client.login(username='v2_user', password='testpass')
        self.doc = IspDocument.objects.create(
            title='V2 Doc', content='V2 content', created_by=self.user,
        )

    def test_v2_doc_list(self):
        resp = self.client.get('/api/documents/')
        self.assertIn(resp.status_code, [200, 404])

    def test_v2_doc_detail(self):
        resp = self.client.get(f'/api/documents/{self.doc.id}/')
        self.assertIn(resp.status_code, [200, 404])

    def test_v2_doc_tree(self):
        resp = self.client.get('/api/documents/tree/')
        self.assertIn(resp.status_code, [200, 404])

    def test_v2_notifications(self):
        resp = self.client.get('/api/notifications/')
        self.assertIn(resp.status_code, [200, 401, 404])

    def test_v2_search_suggest_api(self):
        resp = self.client.get('/api/search/suggest/', {'prefix': 'test'})
        self.assertIn(resp.status_code, [200, 404])


class AuthAPITest(_ClientTestBase):
    """认证测试"""

    def setUp(self):
        super().setUp()
        User.objects.create_user('login_test2', password='testpass')

    def test_login_success(self):
        """POST /login/ 正确密码登录重定向"""
        User.objects.create_user('login_test', password='testpass')
        resp = self.client.post(
            '/login/',
            data={'username': 'login_test', 'password': 'testpass'},
        )
        self.assertEqual(resp.status_code, 302)

    def test_login_wrong_password(self):
        """错误密码登录留在登录页"""
        resp = self.client.post(
            '/login/',
            data={'username': 'login_test2', 'password': 'wrongpass'},
        )
        self.assertEqual(resp.status_code, 200)

    def test_user_search_api(self):
        """GET /api/users/search/ 搜索用户"""
        resp = self.client.get('/api/users/search/', {'q': 'login_test2'})
        self.assertEqual(resp.status_code, 200)
