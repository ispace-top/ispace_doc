# Generated manually for v1.0 Phase 5 — InlineComment full fields

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('app_doc', '0046_v1_0_userprofile_notify_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='inlinecomment',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='inline_comments', to=settings.AUTH_USER_MODEL, verbose_name='评论者'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='inlinecomment',
            name='content',
            field=models.TextField(blank=True, default='', verbose_name='评论内容'),
        ),
        migrations.AddField(
            model_name='inlinecomment',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='是否有效'),
        ),
        migrations.AddField(
            model_name='inlinecomment',
            name='create_time',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='创建时间'),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='inlinecomment',
            options={'ordering': ['anchor_start'], 'verbose_name': '划词评论', 'verbose_name_plural': '划词评论'},
        ),
    ]
