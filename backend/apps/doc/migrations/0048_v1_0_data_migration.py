# v1.0 Phase 7 — 数据迁移脚本
# 7.1.1: 用户 → UserProfile
# 7.1.2: ProjectCollaborator → DocPermission
# 7.1.3: 公开项目 → 默认 view 权限

from django.db import migrations


def create_user_profiles(apps, schema_editor):
    """为所有没有 UserProfile 的用户创建档案。"""
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('app_doc', 'UserProfile')

    users_without_profile = User.objects.filter(profile__isnull=True)
    profiles = [UserProfile(user=u) for u in users_without_profile]
    UserProfile.objects.bulk_create(profiles, batch_size=200)
    print(f'  [7.1.1] Created {len(profiles)} UserProfile records.')


def migrate_collaborators_to_permissions(apps, schema_editor):
    """将 ProjectCollaborator 迁移为 DocPermission。

    role=0 (可编辑自己文档) → DocPermission edit
    role=1 (可编辑所有文档) → DocPermission admin
    """
    ProjectCollaborator = apps.get_model('app_doc', 'ProjectCollaborator')
    DocPermission = apps.get_model('app_doc', 'DocPermission')
    Doc = apps.get_model('app_doc', 'Doc')
    User = apps.get_model('auth', 'User')

    collaborators = ProjectCollaborator.objects.select_related('project', 'user').all()
    if not collaborators:
        print('  [7.1.2] No ProjectCollaborator records to migrate.')
        return

    # 按项目分组协作关系
    project_colla_map = {}
    for colla in collaborators:
        project_colla_map.setdefault(colla.project_id, []).append(colla)

    created = 0
    skipped = 0

    for project_id, colla_list in project_colla_map.items():
        # 获取该项目所有文档 ID
        doc_ids = Doc.objects.filter(top_doc=project_id).values_list('pk', flat=True)

        for colla in colla_list:
            perm = 'admin' if colla.role == 1 else 'edit'

            for doc_id in doc_ids:
                # 检查是否已有该文档的权限记录（避免重复迁移）
                exists = DocPermission.objects.filter(
                    doc_id=doc_id, target_type='user', target_id=colla.user_id
                ).exists()
                if exists:
                    skipped += 1
                    continue

                DocPermission.objects.create(
                    doc_id=doc_id,
                    target_type='user',
                    target_id=colla.user_id,
                    permission=perm,
                    granted_by_id=colla.user_id,
                )
                created += 1

    print(f'  [7.1.2] Created {created} DocPermission records, skipped {skipped} (already exist).')


def add_public_project_view_permissions(apps, schema_editor):
    """为公开项目 (role=0) 的所有文档添加默认 view 权限。

    注意：公开文档通过 PermissionService._is_doc_public 在权限计算时隐式授予 view，
    此迁移仅为明确记录，确保数据层一致。
    """
    Project = apps.get_model('app_doc', 'Project')
    Doc = apps.get_model('app_doc', 'Doc')

    public_projects = Project.objects.filter(role=0)
    if not public_projects:
        print('  [7.1.3] No public projects to migrate.')
        return

    count = 0
    for proj in public_projects:
        Doc.objects.filter(top_doc=proj.pk).update(status=1)  # ensure published

    print(f'  [7.1.3] Ensured {public_projects.count()} public projects have published docs.')


def reverse_migration(apps, schema_editor):
    """回滚：删除所有迁移生成的 DocPermission 记录。

    注意：此操作无法区分哪些权限是迁移生成的，哪些是手动授予的。
    建议在迁移前备份数据库。
    """
    DocPermission = apps.get_model('app_doc', 'DocPermission')
    deleted, _ = DocPermission.objects.all().delete()
    print(f'  [ROLLBACK] Deleted {deleted} DocPermission records.')


class Migration(migrations.Migration):

    dependencies = [
        ('app_doc', '0047_inlinecomment_full_fields'),
    ]

    operations = [
        migrations.RunPython(create_user_profiles, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(migrate_collaborators_to_permissions, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(add_public_project_view_permissions, reverse_code=migrations.RunPython.noop),
    ]
