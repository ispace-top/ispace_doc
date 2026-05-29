"""
安装检测中间件

首次访问时检测系统是否已完成初始化。
如果不存在任何超级管理员，且当前路径不是 /setup/ 相关，
则重定向到安装引导页面。
"""

import os

from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import redirect


SETUP_MARKER = os.path.join(settings.BASE_DIR, '.ispace_installed')


class SetupCheckMiddleware:
    """安装检测中间件。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # 安装相关路径和白名单
        setup_prefixes = ('/setup', '/api/setup', '/static/', '/media/',
                          '/favicon.ico', '/login/', '/register/')

        if any(path.startswith(p) for p in setup_prefixes):
            return self.get_response(request)

        # 检查安装标记文件
        if os.path.exists(SETUP_MARKER):
            return self.get_response(request)

        # 检查数据库是否已存在超管
        try:
            if User.objects.filter(is_superuser=True).exists():
                # 有超管但无标记文件，创建标记文件
                try:
                    with open(SETUP_MARKER, 'w') as f:
                        f.write('installed')
                except OSError:
                    pass
                return self.get_response(request)
        except Exception:
            # 数据库可能未迁移，允许重定向
            pass

        # 未安装，重定向
        return redirect('setup_index')
