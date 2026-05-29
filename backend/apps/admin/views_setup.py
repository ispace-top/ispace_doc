# coding:utf-8
"""安装初始化引导 API"""

import json
import os
import random
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection, DatabaseError
from django.http.response import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from backend.apps.admin.models import SysConfig, SysSetting
from backend.apps.admin.utils import enctry


SETUP_MARKER = os.path.join(settings.BASE_DIR, '.ispace_installed')


def _is_installed():
    return os.path.exists(SETUP_MARKER)


# ========== 前端页面 ==========

@require_GET
def setup_index(request):
    """安装引导首页。"""
    if _is_installed():
        from django.http import Http404
        raise Http404
    return render(request, 'setup/index.html', {'step': 1})


# ========== 步骤校验 API ==========

@require_POST
@csrf_exempt
def api_setup_check(request):
    """分步校验。

    请求体: {
        "step": 1-4,
        "data": {...}  // 当前步骤表单数据
    }
    """
    if _is_installed():
        return JsonResponse({'status': False, 'message': '系统已安装'})

    data = json.loads(request.body)
    step = data.get('step', 0)
    form_data = data.get('data', {})

    checks = {
        1: _check_step1,
        2: _check_step2,
        3: _check_step3,
        4: _check_step4,
    }
    check_fn = checks.get(step)
    if not check_fn:
        return JsonResponse({'status': False, 'message': '无效的步骤'})
    return JsonResponse(check_fn(form_data))


def _check_step1(data):
    """步骤1: 站点信息。"""
    site_name = data.get('site_name', '').strip()
    site_desc = data.get('site_desc', '').strip()
    if not site_name or len(site_name) > 64:
        return {'status': False, 'message': '网站名称长度需在1-64字符之间'}
    if len(site_desc) > 256:
        return {'status': False, 'message': '网站描述不能超过256字符'}
    return {'status': True}


def _check_step2(data):
    """步骤2: 超级管理员。"""
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    password2 = data.get('password2', '').strip()

    if not username or len(username) < 5 or not username.isalnum():
        return {'status': False, 'message': '用户名需为5位以上大小写字母+数字'}
    if '@' not in email:
        return {'status': False, 'message': '请输入正确的邮箱格式'}
    if len(password) < 6:
        return {'status': False, 'message': '密码不少于6位'}
    if password != password2:
        return {'status': False, 'message': '两次密码不一致'}
    return {'status': True}


def _check_step3(data):
    """步骤3: 数据库配置（可选，默认使用 SQLite 跳过）。"""
    db_type = data.get('db_type', 'sqlite')
    if db_type == 'sqlite':
        return {'status': True}  # 默认SQLite无需额外配置

    db_name = data.get('db_name', '').strip()
    db_user = data.get('db_user', '').strip()
    db_host = data.get('db_host', '').strip()
    if not db_name or not db_user or not db_host:
        return {'status': False, 'message': '请填写完整的数据库信息'}

    # 如果有测试连接需求
    if data.get('test_connection'):
        try:
            from django.db import connections
            conn = connection
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
        except DatabaseError as e:
            return {'status': False, 'message': f'数据库连接失败: {str(e)}'}
    return {'status': True}


def _check_step4(data):
    """步骤4: 邮件配置。"""
    # 邮件配置全部可选（可跳过）
    if not data or not data.get('smtp_host'):
        return {'status': True}
    smtp_host = data.get('smtp_host', '').strip()
    if smtp_host and len(smtp_host) > 256:
        return {'status': False, 'message': 'SMTP 地址格式无效'}
    return {'status': True}


# ========== 执行安装 API ==========

@require_POST
@csrf_exempt
def api_setup_install(request):
    """执行安装。

    请求体包含所有5个步骤的数据。
    """
    if _is_installed():
        return JsonResponse({'status': False, 'message': '系统已安装'})

    data = json.loads(request.body)
    step1 = data.get('step1', {})
    step2 = data.get('step2', {})
    step3 = data.get('step3', {})
    step4 = data.get('step4', {})
    step5 = data.get('step5', {})

    # 检查必填项
    if not step2.get('password'):
        return JsonResponse({'status': False, 'message': '管理员密码不能为空'})

    try:
        # 执行数据库迁移
        call_command('migrate', '--noinput', verbosity=0)

        # 创建超级管理员
        username = step2['username'].strip()
        email = step2['email'].strip()
        password = step2['password'].strip()

        if User.objects.filter(username__iexact=username).exists():
            user = User.objects.get(username__iexact=username)
            user.is_superuser = True
            user.is_staff = True
            user.email = email
            user.set_password(password)
            user.save()
        else:
            User.objects.create_superuser(
                username=username, email=email, password=password
            )

        # 保存站点配置到 SysConfig
        site_name = step1.get('site_name', '').strip()
        if site_name:
            SysConfig.objects.update_or_create(
                key='site_name', defaults={'value': site_name, 'description': '网站名称'}
            )
        site_desc = step1.get('site_desc', '').strip()
        if site_desc:
            SysConfig.objects.update_or_create(
                key='site_desc', defaults={'value': site_desc, 'description': '网站描述'}
            )

        # 保存语言设置
        language = step1.get('language', '').strip()
        if language:
            SysConfig.objects.update_or_create(
                key='site_language', defaults={'value': language, 'description': '语言'}
            )
        # 使用 SysSetting 保存（兼容旧版）
        if site_name:
            SysSetting.objects.update_or_create(
                name='site_name', defaults={'value': site_name, 'types': 'basic'}
            )

        # 保存邮件配置到 SysSetting（与后台站点设置共用）
        if step4:
            smtp_host = step4.get('smtp_host', '').strip()
            smtp_port = step4.get('smtp_port', '').strip() or '587'
            smtp_user = step4.get('smtp_user', '').strip()
            smtp_from = step4.get('smtp_from', '').strip()
            smtp_pwd = step4.get('smtp_password', '').strip()
            if smtp_host:
                # 完整保存 6 项邮件设置，确保管理后台回显
                SysSetting.objects.update_or_create(
                    name='smtp_host', defaults={'value': smtp_host, 'types': 'email'}
                )
                SysSetting.objects.update_or_create(
                    name='smtp_port', defaults={'value': smtp_port, 'types': 'email'}
                )
                SysSetting.objects.update_or_create(
                    name='username', defaults={'value': smtp_user, 'types': 'email'}
                )
                SysSetting.objects.update_or_create(
                    name='send_emailer', defaults={'value': smtp_from, 'types': 'email'}
                )
                SysSetting.objects.update_or_create(
                    name='pwd', defaults={'value': enctry(smtp_pwd), 'types': 'email'}
                )
                # 端口为465时默认启用SSL
                is_ssl = 'on' if smtp_port == '465' else 'off'
                SysSetting.objects.update_or_create(
                    name='smtp_ssl', defaults={'value': is_ssl, 'types': 'email'}
                )
                # 启用邮件功能
                SysSetting.objects.update_or_create(
                    name='enable_email', defaults={'value': 'on', 'types': 'basic'}
                )

        # 标记安装完成
        try:
            with open(SETUP_MARKER, 'w') as f:
                f.write('installed')
        except OSError:
            return JsonResponse({
                'status': False,
                'message': '无法写入安装标记文件，请手动创建 .ispace_installed'
            })

        return JsonResponse({
            'status': True,
            'message': '安装成功，请登录',
            'redirect': '/login/',
        })

    except Exception as e:
        import traceback
        return JsonResponse({'status': False, 'message': f'安装失败: {str(e)}'})
