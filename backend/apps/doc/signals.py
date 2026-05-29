"""
信号处理

- User 创建时自动创建 UserProfile
- 用户活跃时间更新
- WebHook 事件分发（文档/评论变更时）
"""

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """新建 User 时自动创建关联的 UserProfile。"""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(user_logged_in)
def update_last_active(sender, user, request, **kwargs):
    """登录时更新最后活跃时间。"""
    UserProfile.objects.filter(user=user).update(last_active=timezone.now())


# 导入 WebHook 信号处理（文档/评论变更 → WebHook 推送）
import backend.apps.doc.webhook.signals  # noqa

# 导入搜索索引同步信号（文档变更 → 搜索后端）
import backend.apps.doc.search.signals  # noqa
