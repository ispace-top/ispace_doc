"""v2.0 模型单元测试（13.1.1）。

覆盖: IspDocument / IspComment / IspDocPermission / IspNotification /
       IspAttachment / IspImage / IspUserProfile / IspOAuthBinding /
       IspOrgNode / IspOrgUser / IspGroup / IspGroupMember
"""
import uuid

from django.test import TestCase
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.utils import timezone

from backend.apps.doc.models_v2 import (
    IspDocument, IspAttachment, IspImage, IspImageGroup,
    IspDocPermission, IspComment, IspNotification,
    IspUserProfile, IspOAuthBinding,
    IspOrgNode, IspOrgUser, IspGroup, IspGroupMember,
)


class IspDocumentTest(TestCase):
    """文档模型 CRUD 与约束测试"""

    def setUp(self):
        self.user = User.objects.create_user('author', password='pass')

    def test_create_document(self):
        doc = IspDocument.objects.create(
            title='测试文档', content='# Hello', created_by=self.user
        )
        self.assertIsInstance(doc.id, uuid.UUID)
        self.assertEqual(doc.status, IspDocument.Status.PUBLISHED)
        self.assertEqual(doc.editor_mode, IspDocument.EditorMode.VDITOR)
        self.assertTrue(doc.is_public)
        self.assertFalse(doc.is_deleted)
        self.assertIsNotNone(doc.created_at)
        self.assertIsNotNone(doc.updated_at)

    def test_document_str(self):
        doc = IspDocument.objects.create(title='Doc Title', created_by=self.user)
        self.assertEqual(str(doc), 'Doc Title')

    def test_document_draft_status(self):
        doc = IspDocument.objects.create(
            title='Draft', created_by=self.user,
            status=IspDocument.Status.DRAFT
        )
        self.assertEqual(doc.status, IspDocument.Status.DRAFT)

    def test_document_archived_status(self):
        doc = IspDocument.objects.create(
            title='Archived', created_by=self.user,
            status=IspDocument.Status.ARCHIVED
        )
        self.assertEqual(doc.status, IspDocument.Status.ARCHIVED)

    def test_document_parent_relation(self):
        parent = IspDocument.objects.create(title='Parent', created_by=self.user)
        child = IspDocument.objects.create(title='Child', parent=parent, created_by=self.user)
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())

    def test_document_soft_delete(self):
        doc = IspDocument.objects.create(title='To Delete', created_by=self.user)
        doc.is_deleted = True
        doc.deleted_at = timezone.now()
        doc.deleted_by = self.user
        doc.save()
        doc.refresh_from_db()
        self.assertTrue(doc.is_deleted)
        self.assertIsNotNone(doc.deleted_at)

    def test_document_watermark(self):
        doc = IspDocument.objects.create(
            title='Watermarked', created_by=self.user,
            is_watermark=True, watermark_type=1,
            watermark_value='CONFIDENTIAL'
        )
        self.assertTrue(doc.is_watermark)
        self.assertEqual(doc.watermark_value, 'CONFIDENTIAL')

    def test_document_content_json(self):
        doc = IspDocument.objects.create(
            title='With JSON', created_by=self.user,
            content_json={'nodes': [{'id': 1, 'label': 'A'}]}
        )
        self.assertEqual(doc.content_json['nodes'][0]['label'], 'A')

    def test_document_editor_modes(self):
        for mode in IspDocument.EditorMode:
            doc = IspDocument.objects.create(
                title=f'Editor {mode.label}', created_by=self.user, editor_mode=mode
            )
            self.assertEqual(doc.editor_mode, mode)


class IspDocPermissionTest(TestCase):
    """文档权限模型测试"""

    def setUp(self):
        self.user = User.objects.create_user('tester', password='pass')
        self.admin = User.objects.create_user('admin', password='pass')
        self.doc = IspDocument.objects.create(title='Test Doc', created_by=self.user)

    def test_create_user_permission(self):
        perm = IspDocPermission.objects.create(
            document=self.doc, target_type='user', target_id=self.user.pk,
            permission='edit', granted_by=self.admin
        )
        self.assertEqual(perm.target_type, 'user')
        self.assertEqual(perm.permission, 'edit')

    def test_permission_unique_constraint(self):
        IspDocPermission.objects.create(
            document=self.doc, target_type='user', target_id=self.user.pk,
            permission='view', granted_by=self.admin
        )
        with self.assertRaises(IntegrityError):
            IspDocPermission.objects.create(
                document=self.doc, target_type='user', target_id=self.user.pk,
                permission='edit', granted_by=self.admin
            )

    def test_permission_granted_by_null_on_delete(self):
        temp_admin = User.objects.create_user('tempadmin', password='pass')
        perm = IspDocPermission.objects.create(
            document=self.doc, target_type='user', target_id=self.user.pk,
            permission='view', granted_by=temp_admin
        )
        temp_admin.delete()
        perm.refresh_from_db()
        self.assertIsNone(perm.granted_by)

    def test_permission_cascade_on_doc_delete(self):
        IspDocPermission.objects.create(
            document=self.doc, target_type='user', target_id=self.user.pk,
            permission='view', granted_by=self.admin
        )
        doc_id = self.doc.pk
        self.doc.delete()
        self.assertEqual(IspDocPermission.objects.filter(document_id=doc_id).count(), 0)


class IspCommentTest(TestCase):
    """统一评论模型测试"""

    def setUp(self):
        self.user = User.objects.create_user('commenter', password='pass')
        self.doc = IspDocument.objects.create(title='Doc for Comment', created_by=self.user)

    def test_create_comment(self):
        comment = IspComment.objects.create(
            document=self.doc, content='Great doc!', created_by=self.user
        )
        self.assertIsInstance(comment.id, uuid.UUID)
        self.assertFalse(comment.is_resolved)

    def test_inline_comment_with_anchor(self):
        comment = IspComment.objects.create(
            document=self.doc, content='This needs clarification',
            anchor_id='anchor-abc', anchor_text='select some text',
            created_by=self.user
        )
        self.assertEqual(comment.anchor_id, 'anchor-abc')
        self.assertEqual(comment.anchor_text, 'select some text')

    def test_comment_reply(self):
        parent = IspComment.objects.create(
            document=self.doc, content='Main comment', created_by=self.user
        )
        reply = IspComment.objects.create(
            document=self.doc, content='Reply', parent=parent, created_by=self.user
        )
        self.assertEqual(reply.parent, parent)
        self.assertIn(reply, parent.replies.all())

    def test_comment_resolve(self):
        comment = IspComment.objects.create(
            document=self.doc, content='Issue here', created_by=self.user
        )
        comment.is_resolved = True
        comment.save()
        comment.refresh_from_db()
        self.assertTrue(comment.is_resolved)


class IspNotificationTest(TestCase):
    """通知模型测试"""

    def setUp(self):
        self.sender = User.objects.create_user('sender', password='pass')
        self.recipient = User.objects.create_user('recipient', password='pass')

    def test_create_notification(self):
        notif = IspNotification.objects.create(
            recipient=self.recipient, sender=self.sender,
            event_type='doc.created', title='New doc created'
        )
        self.assertIsInstance(notif.id, uuid.UUID)
        self.assertFalse(notif.is_read)
        self.assertEqual(notif.event_type, 'doc.created')

    def test_notification_context(self):
        notif = IspNotification.objects.create(
            recipient=self.recipient, sender=self.sender,
            event_type='comment.created', title='@提及',
            context={'doc_id': 'abc-123', 'comment_id': 'def-456'}
        )
        self.assertEqual(notif.context['doc_id'], 'abc-123')

    def test_notification_sender_null(self):
        notif = IspNotification.objects.create(
            recipient=self.recipient,
            event_type='doc.created', title='System notification'
        )
        self.assertIsNone(notif.sender)

    def test_notification_event_types(self):
        for event_type in IspNotification.EventType:
            notif = IspNotification.objects.create(
                recipient=self.recipient, event_type=event_type,
                title=f'Event: {event_type.label}'
            )
            self.assertEqual(notif.event_type, event_type)


class IspAttachmentTest(TestCase):
    """附件/图片模型测试"""

    def setUp(self):
        self.user = User.objects.create_user('uploader', password='pass')
        self.doc = IspDocument.objects.create(title='Doc', created_by=self.user)

    def test_create_attachment(self):
        att = IspAttachment.objects.create(
            document=self.doc, file_name='report.pdf', file_size=102400,
            content_type='application/pdf', storage_key='attachments/uuid/report.pdf',
            uploaded_by=self.user
        )
        self.assertEqual(att.file_name, 'report.pdf')
        self.assertEqual(att.storage_backend, 'local')

    def test_create_image(self):
        img = IspImage.objects.create(
            file_name='photo.png', file_size=51200,
            width=800, height=600, storage_key='images/uuid/photo.png',
            uploaded_by=self.user
        )
        self.assertEqual(img.width, 800)
        self.assertEqual(img.height, 600)

    def test_image_group(self):
        grp = IspImageGroup.objects.create(name='Screenshots', created_by=self.user)
        img = IspImage.objects.create(
            file_name='shot.png', file_size=20480,
            storage_key='images/uuid/shot.png', group=grp,
            uploaded_by=self.user
        )
        self.assertEqual(img.group, grp)
        self.assertIn(img, grp.images.all())


class IspUserProfileTest(TestCase):
    """用户档案与 OAuth 绑定测试"""

    def setUp(self):
        self.user = User.objects.create_user('profile_user', password='pass')

    def test_create_profile(self):
        profile = IspUserProfile.objects.create(
            user=self.user, avatar='https://cdn.example.com/avatar.png',
            gender='M', phone='13800138000', bio='Developer'
        )
        self.assertEqual(profile.gender, 'M')
        self.assertEqual(str(profile), 'profile_user')

    def test_profile_notify_defaults(self):
        profile = IspUserProfile.objects.create(user=self.user)
        self.assertEqual(profile.notify_settings, {})

    def test_oauth_binding(self):
        binding = IspOAuthBinding.objects.create(
            user=self.user, provider='wecom',
            provider_user_id='wx_user_001',
            provider_user_name='张三'
        )
        self.assertEqual(binding.provider, 'wecom')
        self.assertIsInstance(binding.extra_data, dict)

    def test_oauth_binding_unique(self):
        IspOAuthBinding.objects.create(
            user=self.user, provider='wecom', provider_user_id='wx_001'
        )
        with self.assertRaises(IntegrityError):
            IspOAuthBinding.objects.create(
                user=self.user, provider='wecom', provider_user_id='wx_001'
            )


class IspOrgNodeTest(TestCase):
    """组织架构模型测试"""

    def setUp(self):
        self.user = User.objects.create_user('admin_user', password='pass')

    def test_create_org_node(self):
        node = IspOrgNode.objects.create(
            name='技术部', path='/技术部', depth=1, sort_order=0
        )
        self.assertEqual(node.name, '技术部')
        self.assertEqual(node.depth, 1)

    def test_org_node_tree(self):
        root = IspOrgNode.objects.create(name='公司', path='/公司', depth=0)
        child = IspOrgNode.objects.create(
            name='研发中心', parent=root, path='/公司/研发中心', depth=1
        )
        self.assertEqual(child.parent, root)
        self.assertIn(child, root.children.all())

    def test_org_node_external_source(self):
        node = IspOrgNode.objects.create(
            name='部门A', path='/部门A', depth=1,
            external_source='wecom', external_id='dept_123'
        )
        self.assertEqual(node.external_source, 'wecom')
        self.assertEqual(node.external_id, 'dept_123')

    def test_org_user_assignment(self):
        node = IspOrgNode.objects.create(name='产品部', path='/产品部', depth=1)
        assignment = IspOrgUser.objects.create(
            org_node=node, user=self.user, is_primary=True, position='产品经理'
        )
        self.assertTrue(assignment.is_primary)
        self.assertEqual(assignment.position, '产品经理')

    def test_org_user_unique(self):
        node = IspOrgNode.objects.create(name='设计部', path='/设计部', depth=1)
        IspOrgUser.objects.create(org_node=node, user=self.user)
        with self.assertRaises(IntegrityError):
            IspOrgUser.objects.create(org_node=node, user=self.user)


class IspGroupTest(TestCase):
    """用户分组模型测试"""

    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pass')
        self.member = User.objects.create_user('member', password='pass')

    def test_create_group(self):
        group = IspGroup.objects.create(
            name='Python Team', description='Python developers', owner=self.owner
        )
        self.assertEqual(group.member_count, 0)

    def test_group_member(self):
        group = IspGroup.objects.create(name='Frontend', owner=self.owner)
        gm = IspGroupMember.objects.create(group=group, user=self.member, is_admin=True)
        self.assertTrue(gm.is_admin)
        self.assertEqual(gm.group, group)
        self.assertEqual(gm.user, self.member)

    def test_group_member_unique(self):
        group = IspGroup.objects.create(name='Unique Group', owner=self.owner)
        IspGroupMember.objects.create(group=group, user=self.member)
        with self.assertRaises(IntegrityError):
            IspGroupMember.objects.create(group=group, user=self.member)

    def test_group_name_unique(self):
        IspGroup.objects.create(name='My Team', owner=self.owner)
        with self.assertRaises(IntegrityError):
            IspGroup.objects.create(name='My Team', owner=self.owner)
