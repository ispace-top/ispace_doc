# 数据迁移：将 Project 的可见性和水印设置复制到 Doc
from django.db import migrations


def migrate_project_data_to_doc(apps, schema_editor):
    """将 Project.role 和 Project 水印字段复制到对应 Doc"""
    Doc = apps.get_model('app_doc', 'Doc')
    Project = apps.get_model('app_doc', 'Project')
    BrowseHistory = apps.get_model('app_doc', 'BrowseHistory')
    MyCollect = apps.get_model('app_doc', 'MyCollect')

    # 1. 复制 Project 数据到 Doc
    for doc in Doc.objects.all():
        try:
            proj = Project.objects.get(pk=doc.top_doc)
            doc.is_public = (proj.role == 0)  # role=0 为公开
            doc.is_watermark = proj.is_watermark
            doc.watermark_type = proj.watermark_type
            doc.watermark_value = proj.watermark_value or ''
            doc.save(update_fields=['is_public', 'is_watermark',
                                     'watermark_type', 'watermark_value'])
        except Project.DoesNotExist:
            doc.is_public = True
            doc.save(update_fields=['is_public'])

    # 2. 清除文集类型的浏览记录
    BrowseHistory.objects.filter(content_type='pro').delete()

    # 3. 清除文集类型的收藏
    MyCollect.objects.filter(collect_type=2).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('app_doc', '0052_browsehistory'),
    ]

    operations = [
        migrations.RunPython(
            migrate_project_data_to_doc,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
