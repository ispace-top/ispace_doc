# coding:utf-8
"""管理命令：重新生成内置用户指南文档。

用法:
    python manage.py seed_guide
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from backend.apps.admin.seed_guide import create_builtin_guide


class Command(BaseCommand):
    help = '以超级管理员为作者，生成内置用户指南文档'

    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).order_by('id').last()
        if not admin:
            self.stderr.write('错误：未找到超级管理员用户，请先创建管理员。')
            return
        create_builtin_guide(admin)
        self.stdout.write(self.style.SUCCESS('内置用户指南生成完毕！'))
