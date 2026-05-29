# coding:utf-8
from django.shortcuts import render,redirect
from django.http.response import JsonResponse,HttpResponse,Http404
from django.contrib.auth import authenticate,login,logout # 认证相关方法
from django.contrib.auth.models import User # Django默认用户模型
from django.contrib.auth.decorators import login_required # 登录需求装饰器
from django.views.decorators.http import require_http_methods,require_GET,require_POST # 视图请求方法装饰器
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator,PageNotAnInteger,EmptyPage,InvalidPage # 后端分页
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.management import call_command
from rest_framework.views import APIView # 视图
from rest_framework.response import Response # 响应
from rest_framework.pagination import PageNumberPagination # 分页
from rest_framework.authentication import SessionAuthentication # 认证
from rest_framework.permissions import IsAdminUser # 权限
from backend.apps.api.serializers_app import *
from backend.apps.api.auth_app import AppAuth,AppMustAuth # 自定义认证
from backend.apps.api.permissions_app import SuperUserPermission # 自定义权限
from backend.apps.admin.decorators import superuser_only,open_register
from backend.apps.doc.models import *
from backend.apps.doc.views import _sanitize_json
from backend.apps.admin.models import *
from backend.apps.admin.utils import *
from loguru import logger
from urllib.parse import quote
from io import StringIO
import re
import datetime
import requests
import os
import json
import time


# 返回验证码图片
def check_code(request):
    try:
        import io
        from . import check_code as CheckCode
        stream = io.BytesIO()
        # img图片对象,code在图像中写的内容
        img, code = CheckCode.create_validate_code()
        img.save(stream, "png")
        # 图片页面中显示,立即把session中的CheckCode更改为目前的随机字符串值
        request.session["CheckCode"] = code
        return HttpResponse(stream.getvalue(), content_type="image/png")
    except Exception as e:
        logger.exception(_("生成验证码图片异常"))
        return HttpResponse(_("请求异常：{}".format(repr(e))))


def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


# 登录视图
def log_in(request):
    to = request.GET.get('next', '/')
    safe_to = is_internal_path(to)
    if safe_to is False:
        to = '/'
    if request.method == 'GET':
        # 登录用户访问登录页面自动跳转到首页
        if request.user.is_authenticated:
            return redirect(to)
        else:
            return render(request,'auth/login.html',locals())
    elif request.method == 'POST':
        try:
            username = request.POST.get('username','')
            pwd = request.POST.get('password','')
            if len(pwd) > 50:
                errormsg = _('密码长度不符！')
                return render(request, 'auth/login.html', locals())
            # 判断是否需要验证码
            require_login_check_code = SysSetting.objects.filter(types="basic",name="enable_login_check_code")
            if (len(require_login_check_code) > 0) and (require_login_check_code[0].value == 'on'):
                checkcode = request.POST.get("check_code", None)
                if checkcode.lower() != request.session['CheckCode'].lower():
                    errormsg = _('验证码错误！')
                    return render(request, 'auth/login.html', locals())
            # 验证登录次数
            if 'LoginLock' not in request.session.keys():
                request.session['LoginNum'] = 1 # 重试次数
                request.session['LoginLock'] = False # 是否锁定
                request.session['LoginTime'] = datetime.datetime.now().timestamp() # 解除锁定时间
            verify_num = request.session['LoginNum']
            if verify_num > 5:
                request.session['LoginLock'] = True
                request.session['LoginTime'] = (datetime.datetime.now() + datetime.timedelta(minutes=15)).timestamp()
            verify_lock = request.session['LoginLock']
            verify_time = request.session['LoginTime']

            # 验证是否锁定
            if verify_lock is True and datetime.datetime.now().timestamp() < verify_time:
                errormsg = _("操作过于频繁，请15分钟后再试！")
                request.session['LoginNum'] = 0  # 重试次数清零
                return render(request, 'auth/login.html', locals())

            if username != '' and pwd != '':
                user = authenticate(username=username,password=pwd)
                if user is not None:
                    if user.is_active:
                        login(request,user)
                        request.session['LoginNum'] = 0  # 重试次数
                        request.session['LoginLock'] = False  # 是否锁定
                        request.session['LoginTime'] = datetime.datetime.now().timestamp()  # 解除锁定时间
                        LoginRecord.objects.create(
                            username=username, user=user, ip_address=_get_client_ip(request),
                            user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
                            success=True,
                        )
                        return redirect(to)
                    else:
                        LoginRecord.objects.create(
                            username=username, user=user, ip_address=_get_client_ip(request),
                            user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
                            success=False, failure_reason='用户被禁用',
                        )
                        errormsg = _('用户被禁用！')
                        return render(request, 'auth/login.html', locals())
                else:
                    LoginRecord.objects.create(
                        username=username, ip_address=_get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
                        success=False, failure_reason='用户名或密码错误',
                    )
                    errormsg = _('用户名或密码错误！')
                    request.session['LoginNum'] += 1
                    return render(request, 'auth/login.html', locals())
            else:
                errormsg = _('用户名或密码未输入！')
                return render(request, 'auth/login.html', locals())
        except Exception as e:
            logger.exception("登录异常")
            return HttpResponse(_('无法处理该请求'))


# 注册视图
@open_register
@logger.catch()
def register(request):
    # 如果登录用户访问注册页面，跳转到首页
    if request.user.is_authenticated:
        return redirect('/')
    else:
        if request.method == 'GET':
            return render(request,'auth/register.html',locals())
        elif request.method == 'POST':
            username = request.POST.get('username',None)
            email = request.POST.get('email',None)
            password = request.POST.get('password',None)
            password2 = request.POST.get('password2',None)
            if password != password2:
                errormsg = _('两次输入的密码不一致！')
                return render(request, 'auth/register.html', locals())
            if len(password) > 50:
                errormsg = _('密码长度不符！')
                return render(request, 'auth/register.html', locals())
            is_register_code = SysSetting.objects.filter(types='basic', name='enable_register_code', value='on')
            if is_register_code.exists(): # 开启了注册码设置
                register_code = request.POST.get("register_code", None)
                if len(register_code) > 255:
                    errormsg = _('注册码无效!')
                    return render(request, 'auth/register.html', locals())
                try:
                    current_date = timezone.now().date()
                    register_code_value = RegisterCode.objects.get(code=register_code)
                    if register_code_value.used_cnt >= register_code_value.all_cnt:
                        errormsg = _('注册码使用次数已达限制!')
                        return render(request, 'auth/register.html', locals())
                    elif register_code_value.expire_date is not None and register_code_value.expire_date < current_date:
                        errormsg = _('注册码已过期!')
                        return render(request, 'auth/register.html', locals())
                except ObjectDoesNotExist:
                    errormsg = _('注册码无效!')
                    return render(request, 'auth/register.html', locals())
            # 判断是否输入了用户名、邮箱和密码
            if username and email and password:
                if '@'in email:
                    email_exit = User.objects.filter(email=email)
                    username_exit = User.objects.filter(username__iexact=username)
                    if email_exit.count() > 0: # 验证电子邮箱
                        errormsg = _('此电子邮箱已被注册！')
                        return render(request, 'auth/register.html', locals())
                    elif username_exit.count() > 0: # 验证用户名
                        errormsg = _('用户名已被使用！')
                        return render(request, 'auth/register.html', locals())
                    elif re.match('^[0-9a-zA-Z]+$',username) is None:
                        errormsg = _('用户名只能为英文+数字组合')
                        return render(request, 'auth/register.html', locals())
                    elif len(username) < 5:
                        errormsg = _('用户名必须大于等于5位！')
                        return render(request, 'auth/register.html', locals())
                    elif len(password) < 6: # 验证密码长度
                        errormsg = _('密码必须大于等于6位！')
                        return render(request, 'auth/register.html', locals())
                    else:
                        # 创建用户
                        user = User.objects.create_user(username=username, email=email, password=password)
                        user.save()
                        # 创建用户档案
                        from backend.apps.doc.models import UserProfile
                        UserProfile.objects.get_or_create(user=user)
                        # 登录用户
                        user = authenticate(username=username, password=password)
                        # 注册码数据更新
                        if is_register_code.exists():
                            r_all_cnt = register_code_value.all_cnt # 注册码的最大使用次数
                            r_used_cnt = register_code_value.used_cnt + 1 # 更新注册码的已使用次数
                            r_use_user = register_code_value.user_list # 注册码的使用用户
                            if r_used_cnt >= r_all_cnt: # 如果注册码已使用次数大于等于注册码的最大使用次数，则注册码失效
                                RegisterCode.objects.filter(code=register_code).update(
                                    status=0,# 注册码状态设为失效
                                    used_cnt = r_used_cnt, # 更新注册码的已使用次数
                                    user_list = r_use_user + email + ',',
                                )
                            else:
                                RegisterCode.objects.filter(code=register_code).update(
                                    used_cnt=r_used_cnt, # 更新注册码的已使用次数
                                    user_list = r_use_user + email + ',',
                                )
                        if user.is_active:
                            login(request, user)
                            return redirect('/')
                        else:
                            errormsg = _('用户被禁用，请联系管理员！')
                            return render(request, 'auth/register.html', locals())
                else:
                    errormsg = _('请输入正确的电子邮箱格式！')
                    return render(request, 'auth/register.html', locals())
            else:
                errormsg = _("输入内容不符合要求，请核实后重试")
                return render(request, 'auth/register.html', locals())


# 注销
@require_POST
def log_out(request):
    try:
        logout(request)
        resp = request.META['HTTP_REFERER']
        return JsonResponse({'status': True, 'data': resp})
    except Exception as e:
        logger.exception(_("注销异常"))
        return JsonResponse({'status':False})


# 忘记密码
def forget_pwd(request):
    if request.method == 'GET':
        return render(request,'auth/forget_pwd.html',locals())
    elif request.method == 'POST':
        email = request.POST.get("email",None) # 邮箱
        vcode = request.POST.get("vcode",None) # 验证码
        new_pwd= request.POST.get('password',None) # 密码
        new_pwd_confirm = request.POST.get('confirm_password')
        # 查询验证码和邮箱是否匹配
        try:
            # 验证重试次数
            if 'ForgetPwdEmailCodeVerifyLock' not in request.session.keys():
                request.session['ForgetPwdEmailCodeVerifyNum'] = 1 # 重试次数
                request.session['ForgetPwdEmailCodeVerifyLock'] = False # 是否锁定
                request.session['ForgetPwdEmailCodeVerifyTime'] = datetime.datetime.now().timestamp() # 解除锁定时间
            verify_num = request.session['ForgetPwdEmailCodeVerifyNum']
            if verify_num > 5:
                request.session['ForgetPwdEmailCodeVerifyLock'] = True
                request.session['ForgetPwdEmailCodeVerifyTime'] = (datetime.datetime.now() + datetime.timedelta(minutes=10)).timestamp()
            verify_lock = request.session['ForgetPwdEmailCodeVerifyLock']
            verify_time = request.session['ForgetPwdEmailCodeVerifyTime']

            # 验证是否锁定
            # print(datetime.datetime.now().timestamp(),verify_time)
            if verify_lock is True and datetime.datetime.now().timestamp() < verify_time:
                errormsg = _("操作过于频繁，请10分钟后再试！")
                request.session['ForgetPwdEmailCodeVerifyNum'] = 0  # 重试次数清零
                return render(request, 'auth/forget_pwd.html', locals())
            # 比对验证码
            data = EmaiVerificationCode.objects.get(email_name=email,verification_code=vcode,verification_type='忘记密码')
            expire_time = data.expire_time
            if expire_time > datetime.datetime.now():
                user = User.objects.get(email=email)
                user.set_password(new_pwd)
                user.save()
                errormsg = _("修改密码成功，请返回登录！")
                request.session['ForgetPwdEmailCodeVerifyNum'] = 0 # 重试次数
                request.session['ForgetPwdEmailCodeVerifyLock'] = False # 是否锁定
                request.session['ForgetPwdEmailCodeVerifyTime'] = datetime.datetime.now().timestamp() # 解除锁定时间
                return render(request, 'auth/forget_pwd.html', locals())
            else:
                errormsg = _("验证码已过期！")
                return render(request, 'auth/forget_pwd.html', locals())
        except ObjectDoesNotExist:
            logger.error(_("验证码或邮箱不存在：{}".format(email)))
            errormsg = _("验证码或邮箱错误！")
            request.session['ForgetPwdEmailCodeVerifyNum'] += 1
            return render(request, 'auth/forget_pwd.html', locals())
        except Exception as e:
            logger.exception("修改密码异常")
            errormsg = _("验证码或邮箱错误！")
            request.session['ForgetPwdEmailCodeVerifyNum'] += 1
            return render(request,'auth/forget_pwd.html',locals())


# 发送电子邮箱验证码
@logger.catch()
def send_email_vcode(request):
    if request.method == 'POST':
        email = request.POST.get('email',None)
        is_email = User.objects.filter(email=email)
        if is_email.count() != 0:
            vcode_str = generate_vcode()
            # 发送邮件
            send_status = send_email(to_email=email, vcode_str=vcode_str)
            if send_status:
                # 生成过期时间
                now_time = datetime.datetime.now()
                expire_time = now_time + datetime.timedelta(minutes=30)
                # 创建数据库记录
                EmaiVerificationCode.objects.create(
                    email_name = email,
                    verification_type = '忘记密码',
                    verification_code = vcode_str,
                    expire_time = expire_time
                )
                return JsonResponse({'status':True,'data':_('发送成功')})
            else:
                return JsonResponse({'status':False,'data':_('验证码发送未成功，请稍后重试')})

        else:
            return JsonResponse({'status':False,'data':_('电子邮箱不存在！')})
    else:
        return JsonResponse({'status':False,'data':_('不支持的请求方法')})


# 测试电子邮箱配置
@superuser_only
@require_http_methods(['POST'])
def send_email_test(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = request.POST
    smtp_host = data.get('smtp_host', '')
    send_emailer = data.get('send_emailer', '')
    smtp_port = data.get('smtp_port', '')
    username = data.get('username', '')
    pwd = data.get('pwd', '')
    ssl = data.get('smtp_ssl', False) in (True, 'true', 'on', 'True')
    # print(smtp_host,smtp_port,send_emailer,username,pwd)

    msg_from = send_emailer  # 发件人邮箱
    msg_to = send_emailer  # 收件人邮箱
    try:
        sitename = SysSetting.objects.get(types="basic", name="site_name").value
    except:
        sitename = "爱思文档"
    subject = "{sitename} - 邮箱配置测试".format(sitename=sitename)
    content = "此邮件由管理员配置【{sitename}】邮箱信息时发出！".format(sitename=sitename)
    msg = MIMEText(content, _subtype='html', _charset='utf-8')
    msg['Subject'] = subject
    msg['From'] = Header(sitename, 'utf-8').encode() + " <{}>".format(msg_from)
    msg['To'] = msg_to
    try:
        # print(smtp_host,smtp_port)
        if ssl:
            s = smtplib.SMTP_SSL(smtp_host, int(smtp_port))  # 发件箱邮件服务器及端口号
        else:
            s = smtplib.SMTP(smtp_host, int(smtp_port))
        # print(pwd)
        s.login(username, pwd)
        s.sendmail(from_addr=msg_from, to_addrs=msg_to, msg=msg.as_string())
        s.quit()
        return JsonResponse({'status': True, 'data': _('发送成功')})
    except smtplib.SMTPException as e:
        logger.error("邮件发送异常:{}".format(repr(e)))
        return JsonResponse({'status': False, 'data': str(e)[:200]})
    except UnicodeError as e:
        logger.error("邮件密码编码异常（密钥变更？请重新设置邮箱密码）:{}".format(repr(e)))
        return JsonResponse({'status': False, 'data': '邮箱密码解码失败，请在邮箱设置中重新输入密码后保存'})
    except Exception as e:
        logger.error("邮件发送异常:{}".format(repr(e)))
        return JsonResponse({'status': False, 'data': repr(e)})

# 后台管理 - 仪表盘
@superuser_only
def admin_overview(request):
    if request.method == 'GET':
        from datetime import timedelta
        import shutil

        today = datetime.date.today()
        week_ago = today - timedelta(days=7)

        # 用户数
        user_cnt = User.objects.all().count()
        # 文档数
        doc_cnt = Doc.objects.filter(status=1).count()  # 已发布文档总数
        # 今日新增文档
        today_doc_cnt = Doc.objects.filter(create_time__date=today).count()
        # 7天活跃用户
        active_user_cnt = User.objects.filter(last_login__date__gte=week_ago).count()
        img_cnt = Image.objects.all().count()
        attachment_cnt = Attachment.objects.all().count()
        # 评论总数
        comment_cnt = DocComment.objects.filter(is_active=True).count()
        # 文档动态
        doc_active_list = Doc.objects.all().order_by('-modify_time')[:5]
        # 最近审计日志
        audit_logs = AuditLog.objects.select_related('user').all().order_by('-created_at')[:10]

        # 系统资源监控
        sys_resources = _get_system_resources()

        return render(request, 'app_admin/admin_overview.html', locals())
    else:
        pass


def _get_system_resources():
    """获取服务器 CPU、内存、磁盘使用情况。"""
    import shutil
    import os

    result = {'cpu': None, 'memory': None, 'disk': None}

    try:
        import psutil
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.3)
        cpu_count = psutil.cpu_count(logical=True)
        result['cpu'] = {
            'percent': cpu_percent,
            'cores': cpu_count,
        }
        # 内存
        mem = psutil.virtual_memory()
        result['memory'] = {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'percent': mem.percent,
        }
    except ImportError:
        pass
    except Exception as e:
        result['cpu'] = {'percent': 0, 'cores': os.cpu_count() or 0, 'error': str(e)}

    # 磁盘
    try:
        import shutil
        total, used, free = shutil.disk_usage(os.getcwd())
        disk_percent = round((used / total) * 100, 1) if total > 0 else 0
        result['disk'] = {
            'total': total,
            'used': used,
            'free': free,
            'percent': disk_percent,
        }
    except Exception as e:
        result['disk'] = {'error': str(e)}

    return result

# 后台管理 - 用户管理HTML
@superuser_only
@logger.catch()
@require_GET
def admin_user(request):
    return render(request, 'app_admin/admin_user.html', locals())


# 后台管理 - 用户管理 - 用户资料编辑HTML
def admin_user_profile(request):
    return render(request, 'app_admin/admin_user_profile.html',locals())


# 后台管理 - 用户列表接口
class AdminUserList(APIView):
    authentication_classes = [SessionAuthentication,AppMustAuth]
    permission_classes = [SuperUserPermission]

    # 获取用户列表
    def get(self, request):
        username = request.query_params.get('username', '')
        page_num = request.query_params.get('page', 1)
        limit = request.query_params.get('limit', 10)
        if username == '':
            user_data = User.objects.all().values(
                'id', 'last_login', 'is_superuser', 'username', 'email', 'date_joined', 'is_active', 'first_name'
            )
        else:
            user_data = User.objects.filter(username__icontains=username).values(
                'id', 'last_login', 'is_superuser', 'username', 'email', 'date_joined', 'is_active', 'first_name'
            )

        page = PageNumberPagination()  # 实例化一个分页器
        page.page_size = limit
        page_users = page.paginate_queryset(user_data, request, view=self)  # 进行分页查询
        serializer = UserSerializer(page_users, many=True)  # 对分页后的结果进行序列化处理
        resp = {
            'code': 0,
            'data': serializer.data,
            'count': user_data.count()
        }

        return Response(resp)

    # 新增用户
    def post(self, request):
        username = request.data.get('username', '')  # 接收用户名参数
        email = request.data.get('email', '')  # 接收email参数
        password = request.data.get('password', '')  # 接收密码参数
        user_type = request.data.get('user_type', 0)  # 用户类型 0为普通用户，1位管理员
        # 用户名只能为英文小写或数字且大于等于5位，密码大于等于6位
        if len(username) >= 5 and \
                len(password) >= 6 and \
                '@' in email and \
                re.match(r'^[0-9a-zA-Z]', username):
            # 不允许电子邮箱重复
            if User.objects.filter(email=email).count() > 0:
                return JsonResponse({'status': False, 'data': _('电子邮箱不可重复')})
            # 不允许重复的用户名
            if User.objects.filter(username__iexact=username).count() > 0:
                return JsonResponse({'status': False, 'data': _('用户名不可重复')})
            try:
                if user_type == 0:
                    user = User.objects.create_user(
                        username=username,
                        password=password,
                        email=email
                    )
                    user.save()
                elif int(user_type) == 1:
                    user = User.objects.create_superuser(
                        username=username,
                        password=password,
                        email=email
                    )
                    user.save()
                return Response({'code': 0})
            except Exception as e:
                return Response({'code': 4, 'data': _('服务器处理异常')})
        else:
            return JsonResponse({'code': 5, 'data': _('请求参数校验未通过')})


# 后台管理 - 用户接口
class AdminUserDetail(APIView):
    authentication_classes = [SessionAuthentication,AppMustAuth]
    permission_classes = [SuperUserPermission]

    def get_object(self, id):
        try:
            return User.objects.get(id=id)
        except ObjectDoesNotExist:
            raise Http404

    # 获取用户
    def get(self,request, id):
        user = self.get_object(id)
        serializer = UserSerializer(user)
        resp = {
            'code': 0,
            'data': serializer.data,
        }

        return Response(resp)

    # 修改用户（资料、密码）
    def put(self, request, id):
        obj = request.data.get('obj','')
        if obj.replace(' ','') == '':
            resp = {
                'code':5,
                'data':'无效类型'
            }
            return Response(resp)
        elif obj == 'info': # 修改资料
            status = request.POST.get('is_active', '')  # 状态
            username = request.POST.get('username', '')  # 用户名
            nickname = request.POST.get('nickname', '')  # 昵称
            email = request.POST.get('email', '')  # 电子邮箱
            is_superuser = request.POST.get('is_superuser', '')  # 是否超级管理员
            try:
                User.objects.filter(id=id).update(
                    username = username,
                    first_name = nickname,
                    email = email,
                    is_active = True if status == 'on' else False,
                    is_superuser = True if is_superuser == 'true' else False
                )
                return Response({'code': 0, 'data': _('修改成功')})
            except:
                logger.exception("修改用户资料异常")
                return Response({'code': 4, 'data': _('数据修改操作异常')})

        elif obj == 'pwd': # 修改密码
            try:
                password = request.data.get('password', None)
                password2 = request.data.get('password2', None)
                if id and password:
                    if password == password2:
                        user = User.objects.get(id=int(id))
                        user.set_password(password)
                        user.save()
                        return Response({'code': 0, 'data': _('修改成功')})
                    else:
                        return Response({'code': 5, 'data': _('两个密码不一致')})
                else:
                    return JsonResponse({'code': 5, 'data': _('请求参数不正确')})
            except Exception as e:
                return JsonResponse({'code': 4, 'data': _('请求无法处理')})

        else:
            resp = {
                'code': 5,
                'data': '无效类型'
            }
            return Response(resp)

    # 删除用户
    def delete(self, request, id):
        try:
            user = self.get_object(id)  # 获取用户
            user.delete()
            resp = {
                'code':0,
                'data':_('删除成功')
            }
            return Response(resp)
        except Exception as e:
            logger.exception("删除用户出错")
            resp = {
                'code': 4,
                'data': _('删除操作执行异常')
            }
            return Response(resp)


# 后台管理 - 文档管理
@superuser_only
@logger.catch()
def admin_doc(request):
    if request.method == 'GET':
        published_doc_cnt = Doc.objects.filter(status=1).count()
        draft_doc_cnt = Doc.objects.filter(status=0).count()
        all_cnt = published_doc_cnt + draft_doc_cnt
        return render(request,'app_admin/admin_doc.html',locals())
    elif request.method == 'POST':
        kw = request.POST.get('kw', '')
        parent_doc = request.POST.get('parent_doc', '')
        status = request.POST.get('status', '')
        if status == '-1':
            q_status = [0, 1]
        elif status in ['0', '1']:
            q_status = [int(status)]
        else:
            q_status = [0, 1]

        q_filters = Q(status__in=q_status)
        if parent_doc:
            q_filters &= Q(parent_doc=int(parent_doc))

        page = request.POST.get('page', 1)
        limit = request.POST.get('limit', 10)
        if kw == '':
            doc_list = Doc.objects.filter(q_filters).order_by('-modify_time')
        else:
            doc_list = Doc.objects.filter(
                Q(content__icontains=kw) | Q(name__icontains=kw),
                q_filters
            ).order_by('-modify_time')

        paginator = Paginator(doc_list, limit)
        page_num = request.GET.get('page', page)
        try:
            docs = paginator.page(page_num)
        except PageNotAnInteger:
            docs = paginator.page(1)
        except EmptyPage:
            docs = paginator.page(paginator.num_pages)

        table_data = []
        for doc in docs:
            item = {
                'id': doc.id,
                'name': doc.name,
                'parent': Doc.objects.get(id=doc.parent_doc).name if doc.parent_doc != 0 else '无',
                'status': doc.status,
                'editor_mode': doc.editor_mode,
                'open_children': doc.open_children,
                'create_user': doc.create_user.username,
                'create_time': doc.create_time,
                'modify_time': doc.modify_time
            }
            table_data.append(item)
        resp_data = {
            "code": 0,
            "msg": "ok",
            "count": doc_list.count(),
            "data": _sanitize_json(table_data)
        }
        return JsonResponse(resp_data)

# 后台管理 - 文档管理 - 文档历史管理
@superuser_only
def admin_doc_history(request,id):
    doc = Doc.objects.get(id=id)
    return render(request,'app_admin/admin_doc_history.html',locals())


# 文档历史接口 - 通过文档id
class AdminDocHistory(APIView):
    authentication_classes = [SessionAuthentication, AppMustAuth]
    permission_classes = [SuperUserPermission]

    def get_object(self, id):
        try:
            return Doc.objects.get(id=id)
        except ObjectDoesNotExist:
            raise Http404

    # 获取文档的历史记录
    def get(self,request, id):
        doc = self.get_object(id=id)
        page_num = request.query_params.get('page', 1)
        limit = request.query_params.get('limit', 10)

        history_data = DocHistory.objects.filter(doc=doc).order_by('-create_time')
        page = PageNumberPagination()  # 实例化一个分页器
        page.page_size = limit
        page_historys = page.paginate_queryset(history_data, request, view=self)  # 进行分页查询
        serializer = DocHistorySerializer(page_historys, many=True)  # 对分页后的结果进行序列化处理
        resp = {
            'code': 0,
            'data': serializer.data,
            'count': history_data.count()
        }

        return Response(resp)

    # 删除文档的历史记录
    def delete(self,request,id):
        pass


# 文档历史详情接口 - 通过文档历史id
class AdminDocHistoryDetail(APIView):
    authentication_classes = [SessionAuthentication, AppMustAuth]
    permission_classes = [SuperUserPermission]

    def delete(self,request):
        try:
            id = request.data.get('id','')
            his = DocHistory.objects.filter(id=id).delete()
            return Response({'code':0})
        except:

            return Response({'code':5,'data':_("系统异常")})



# 后台管理 - 模板管理
@superuser_only
@logger.catch()
def admin_doctemp(request):
    if request.method == 'GET':
        kw = request.GET.get('kw','')
        page_size = int(request.GET.get('page_size', 10))
        if kw == '':
            doctemp_list = DocTemp.objects.all()
            paginator = Paginator(doctemp_list, page_size)
            page = request.GET.get('page', 1)
            try:
                doctemps = paginator.page(page)
            except PageNotAnInteger:
                doctemps = paginator.page(1)
            except EmptyPage:
                doctemps = paginator.page(paginator.num_pages)
        else:
            doctemp_list = DocTemp.objects.filter(content__icontains=kw)
            paginator = Paginator(doctemp_list, page_size)
            page = request.GET.get('page', 1)
            try:
                doctemps = paginator.page(page)
            except PageNotAnInteger:
                doctemps = paginator.page(1)
            except EmptyPage:
                doctemps = paginator.page(paginator.num_pages)
            doctemps.kw = kw
        return render(request,'app_admin/template_management.html',locals())


# 后台管理 - 图片管理页面
@superuser_only
def admin_image(request):
    return render(request,'app_admin/admin_image.html',locals())

# 图片列表接口
class AdminImageList(APIView):
    authentication_classes = [SessionAuthentication,AppMustAuth]
    permission_classes = [SuperUserPermission]

    # 获取图片列表
    def get(self, request):
        kw  = request.query_params.get('kw', '')
        username = request.query_params.get('username', '')
        page_num = request.query_params.get('page', 1)
        limit = request.query_params.get('limit', 10)
        mode = request.query_params.get('mode', '')
        if mode == 'scan':
            img_data = Image.objects.all()
            img_list = []
            for img in img_data:
                quote_path = quote(img.file_path)
                if quote_path == img.file_path:
                    used_img_doc = Doc.objects.filter(pre_content__icontains=img.file_path).exists()
                else:
                    query = Q(pre_content__icontains=img.file_path) | Q(pre_content__icontains=quote_path)
                    used_img_doc = Doc.objects.filter(query).exists()
                if not used_img_doc:
                    img_list.append(img.file_path)
            img_data = img_data.filter(file_path__in=img_list).order_by('-create_time')
        elif kw == '' and username == '':
            img_data = Image.objects.all().order_by('-create_time')
        elif kw != '':
            img_data = Image.objects.filter(file_name__icontains=kw).order_by('-create_time')
        elif username != '':
            user = User.objects.get(id=username)
            img_data = Image.objects.filter(user=user).order_by('-create_time')
        page = PageNumberPagination()  # 实例化一个分页器
        page.page_size = limit
        page_imgs = page.paginate_queryset(img_data, request, view=self)  # 进行分页查询
        serializer = ImageSerializer(page_imgs, many=True)  # 对分页后的结果进行序列化处理
        resp = {
            'code': 0,
            'data': serializer.data,
            'count': img_data.count()
        }

        return Response(resp)

    # 批量删除图片
    def delete(self,request):
        ids = request.data.get('id','').split(',')
        try:
            image = Image.objects.filter(id__in=ids)  # 查询附件
            for a in image:  # 遍历附件
                file_path = settings.BASE_DIR + a.file_path
                is_exist = os.path.exists(file_path)
                if is_exist:
                    os.remove(file_path)
            image.delete()  # 删除数据库记录
            return JsonResponse({'code': 0, 'data': _('删除成功')})
        except Exception as e:
            logger.exception("删除图片异常")
            return JsonResponse({'code': 4, 'data': _('数据删除操作异常')})

# 图片详情接口
class AdminImageDetail(APIView):
    authentication_classes = [SessionAuthentication,AppMustAuth]
    permission_classes = [SuperUserPermission]

    # 删除图片
    def delete(self,request,id):
        try:
            image = Image.objects.filter(id=id)  # 查询附件
            for a in image:  # 遍历附件
                file_path = settings.BASE_DIR + a.file_path
                is_exist = os.path.exists(file_path)
                if is_exist:
                    os.remove(file_path)
            image.delete()  # 删除数据库记录
            return JsonResponse({'code': 0, 'data': _('删除成功')})
        except Exception as e:
            logger.exception("删除图片异常")
            return JsonResponse({'code': 4, 'data': _('数据删除操作异常')})


@superuser_only
# 后台管理 - 附件管理页面
def admin_attachment(request):
    return render(request,'app_admin/admin_attachment.html',locals())


# 附件列表接口
class AdminAttachmentList(APIView):
    authentication_classes = [SessionAuthentication,AppMustAuth]
    permission_classes = [SuperUserPermission]

    # 获取附件列表
    def get(self, request):
        kw  = request.query_params.get('kw', '')
        username = request.query_params.get('username', '')
        page_num = request.query_params.get('page', 1)
        limit = request.query_params.get('limit', 10)
        if kw == '' and username == '':
            attachment_data = Attachment.objects.all().order_by('-create_time')
        elif kw != '':
            attachment_data = Attachment.objects.filter(file_name__icontains=kw).order_by('-create_time')
        elif username != '':
            user = User.objects.get(id=username)
            attachment_data = Attachment.objects.filter(user=user).order_by('-create_time')
        page = PageNumberPagination()  # 实例化一个分页器
        page.page_size = limit
        page_attachments = page.paginate_queryset(attachment_data, request, view=self)  # 进行分页查询
        serializer = AttachmentSerializer(page_attachments, many=True)  # 对分页后的结果进行序列化处理
        resp = {
            'code': 0,
            'data': serializer.data,
            'count': attachment_data.count()
        }

        return Response(resp)

    # 批量删除附件
    def delete(self,request):
        ids = request.data.get('id','').split(',')
        try:
            attachment = Attachment.objects.filter(id__in=ids)  # 查询附件
            for a in attachment:  # 遍历附件
                a.file_path.delete()  # 删除文件
            attachment.delete()  # 删除数据库记录
            return JsonResponse({'code': 0, 'data': _('删除成功')})
        except Exception as e:
            logger.exception("删除附件异常")
            return JsonResponse({'code': 4, 'data': _('数据删除操作异常')})


# 附件详情接口
class AdminAttachmentDetail(APIView):
    authentication_classes = [SessionAuthentication,AppMustAuth]
    permission_classes = [SuperUserPermission]

    # 删除图片
    def delete(self,request,id):
        try:
            attachment = Attachment.objects.filter(id=id)  # 查询附件
            for a in attachment:  # 遍历附件
                a.file_path.delete()  # 删除文件
            attachment.delete()  # 删除数据库记录
            return JsonResponse({'code': 0, 'data': _('删除成功')})
        except Exception as e:
            logger.exception("删除图片异常")
            return JsonResponse({'code': 4, 'data': _('数据删除操作异常')})


# 后台管理 - 注册邀请码管理
@superuser_only
@logger.catch()
def admin_register_code(request):
    # 返回注册邀请码管理页面
    return render(request,'app_admin/admin_register_code.html',locals())


# 注册邀请码列表接口
class AdminRegisterCodeApi(APIView):
    authentication_classes = [SessionAuthentication,AppMustAuth]
    permission_classes = [SuperUserPermission]

    # 获取邀请码列表
    def get(self,request):
        page_num = request.query_params.get('page', 1)
        limit = request.query_params.get('limit', 10)
        code_data = RegisterCode.objects.all().order_by('-create_time')
        page = PageNumberPagination()  # 实例化一个分页器
        page.page_size = limit
        page_codes = page.paginate_queryset(code_data, request, view=self)  # 进行分页查询
        serializer = RegisterCodeSerializer(page_codes, many=True)  # 对分页后的结果进行序列化处理
        resp = {
            'code': 0,
            'data': serializer.data,
            'count': code_data.count()
        }

        return Response(resp)

    # 新增注册邀请码
    def post(self,request):
        try:
            all_cnt = int(request.data.get('all_cnt', 1))  # 注册码的最大使用次数
            expire_date = request.data.get('expire_date',None)
            if all_cnt <= 0:
                return Response({'code': 5, 'data': _('最大使用次数不可为负数')})
            is_code = False
            while is_code is False:
                code_str = '0123456789qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM'
                random_code = ''.join(random.sample(code_str, k=10))
                random_code_used = RegisterCode.objects.filter(code=random_code).count()
                if random_code_used > 0:  # 已存在此注册码，继续生成一个注册码
                    is_code = False
                else:  # 数据库中不存在此注册码，跳出循环
                    is_code = True
            # 创建一个注册码
            RegisterCode.objects.create(
                code=random_code,
                all_cnt=all_cnt,
                expire_date = expire_date,
                create_user=request.user
            )
            return Response({'code': 0, 'data': _('新增成功')})
        except Exception as e:
            logger.exception(_("生成注册码异常"))
            return Response({'code': 4, 'data': _('服务器处理异常')})

    # 删除邀请码
    def delete(self,request):
        code_id = request.data.get('code_id', None)
        try:
            register_code = RegisterCode.objects.get(id=int(code_id))
            register_code.delete()
            return Response({'code': 0, 'data': _('删除成功')})
        except ObjectDoesNotExist:
            return Response({'code': 1, 'data': _('注册码不存在')})
        except:
            return Response({'code': 4, 'data': _('服务器处理异常')})


# 普通用户修改密码
@login_required()
@logger.catch()
def change_pwd(request):
    if request.method == 'POST':
        try:
            old_pwd = request.POST.get('old_pwd', None)
            password = request.POST.get('password',None)
            password2 = request.POST.get('password2',None)
            # print(password, password2)
            user = request.user.check_password(old_pwd)
            if user is False:
                return JsonResponse({'status':False,'data':_('密码错误！')})
            if password and password== password2:
                if len(password) >= 6:
                    user = User.objects.get(id=request.user.id)
                    user.set_password(password)
                    user.save()
                    return JsonResponse({'status':True,'data':_('修改成功')})
                else:
                    return JsonResponse({'status':False,'data':_('密码不得少于6位数')})
            else:
                return JsonResponse({'status':False,'data':_('两个密码不一致')})
        except Exception as e:
            return JsonResponse({'status':False,'data':_('密码修改操作异常')})
    else:
        return HttpResponse(_('不支持的请求方法'))


# 后台管理 - 应用设置
@superuser_only
@logger.catch()
def admin_setting(request):
    email_settings = SysSetting.objects.filter(types="email")
    emailer = email_settings.filter(name='send_emailer').first()
    email_host = email_settings.filter(name='smtp_host').first()
    email_port = email_settings.filter(name='smtp_port').first()
    email_username = email_settings.filter(name="username").first()
    email_ssl = email_settings.filter(name="smtp_ssl").first()
    email_pwd = email_settings.filter(name="pwd").first()
    try:
        email_dec_pwd = dectry(email_pwd.value) if email_pwd and email_pwd.value else ''
    except Exception:
        email_dec_pwd = ''  # 解密失败（密钥变更），需重新设置密码
    enable_email = SysSetting.objects.filter(types='basic', name='enable_email').first()
    if request.method == 'GET':
        return render(request,'app_admin/admin_setting.html',locals())
    elif request.method == 'POST':
        types = request.POST.get('type',None)
        # 基础设置
        if types == 'basic':
            site_name = request.POST.get('site_name',None) # 站点名称
            site_sub_name = request.POST.get('site_sub_name', None)  # 站点子标题
            site_keywords = request.POST.get('site_keywords', None)  # 站点关键词
            site_desc = request.POST.get('site_desc', None)  # 站点描述
            beian_code = request.POST.get('beian_code', None)  # 备案号
            index_project_sort = request.POST.get('index_project_sort','1') # 首页文集默认排序
            close_register = request.POST.get('close_register',None) # 禁止注册
            require_login = request.POST.get('require_login',None) # 全站登录
            long_code = request.POST.get('long_code', None)  # 长代码显示
            disable_update_check = request.POST.get('disable_update_check', None)  # 关闭更新检测
            static_code = request.POST.get('static_code',None) # 统计代码
            ad_code = request.POST.get('ad_code',None) # 广告位1
            ad_code_2 = request.POST.get('ad_code_2',None) # 广告位2
            ad_code_3 = request.POST.get('ad_code_3', None)  # 广告位3
            ad_code_4 = request.POST.get('ad_code_4', None)  # 广告位4
            enbale_email = request.POST.get("enable_email",None) # 启用邮箱
            img_scale = request.POST.get('img_scale',None) # 图片缩略
            enable_register_code = request.POST.get('enable_register_code',None) # 注册邀请码
            enable_login_check_code = request.POST.get('enable_login_check_code',None) # 登录验证码
            # 更新首页文集默认排序
            SysSetting.objects.update_or_create(
                name='index_project_sort',
                defaults={'value': index_project_sort, 'types': 'basic'}
            )
            # 更新开放注册状态
            SysSetting.objects.update_or_create(
                name='require_login',
                defaults={'value':require_login,'types':'basic'}
            )
            # 更新全站登录状态
            SysSetting.objects.update_or_create(
                name='close_register',
                defaults={'value': close_register, 'types': 'basic'}
            )
            # 更新统计代码状态
            SysSetting.objects.update_or_create(
                name = 'static_code',
                defaults={'value':static_code,'types':'basic'}
            )
            # 更新广告代码状态
            SysSetting.objects.update_or_create(
                name = 'ad_code',
                defaults={'value':ad_code,'types':'basic'}
            )
            SysSetting.objects.update_or_create(
                name='ad_code_2',
                defaults={'value': ad_code_2, 'types': 'basic'}
            )
            SysSetting.objects.update_or_create(
                name='ad_code_3',
                defaults={'value': ad_code_3, 'types': 'basic'}
            )
            SysSetting.objects.update_or_create(
                name='ad_code_4',
                defaults={'value': ad_code_4, 'types': 'basic'}
            )

            # 更新备案号
            SysSetting.objects.update_or_create(
                name='beian_code',
                defaults={'value':beian_code,'types':'basic'}
            )
            # 更新站点名称
            SysSetting.objects.update_or_create(
                name='site_name',
                defaults={'value': site_name, 'types': 'basic'}
            )
            # 更新站点子标题
            SysSetting.objects.update_or_create(
                name='site_sub_name',
                defaults={'value': site_sub_name, 'types': 'basic'}
            )
            # 更新站点关键词
            SysSetting.objects.update_or_create(
                name='site_keywords',
                defaults={'value': site_keywords, 'types': 'basic'}
            )
            # 更新站点描述
            SysSetting.objects.update_or_create(
                name='site_desc',
                defaults={'value': site_desc, 'types': 'basic'}
            )

            # 更新图片缩略状态
            SysSetting.objects.update_or_create(
                name='img_scale',
                defaults={'value': img_scale, 'types': 'basic'}
            )
            # 更新长代码展示状态
            SysSetting.objects.update_or_create(
                name='long_code',
                defaults={'value': long_code, 'types': 'basic'}
            )
            # 更新关闭更新检测状态
            SysSetting.objects.update_or_create(
                name='disable_update_check',
                defaults={'value': disable_update_check, 'types': 'basic'}
            )
            # 更新邮箱启用状态
            SysSetting.objects.update_or_create(
                name='enable_email',
                defaults={'value': enbale_email, 'types': 'basic'}
            )
            # 更新注册码启停状态
            SysSetting.objects.update_or_create(
                name = 'enable_register_code',
                defaults= {'value': enable_register_code, 'types':'basic'}
            )
            # 更新登录验证码状态
            SysSetting.objects.update_or_create(
                name = 'enable_login_check_code',
                defaults={'value':enable_login_check_code,'types':'basic'}
            )
            # 更新站点语言
            site_language = request.POST.get('site_language', None)
            if site_language:
                SysSetting.objects.update_or_create(
                    name='site_language',
                    defaults={'value': site_language, 'types': 'basic'}
                )

            return render(request,'app_admin/admin_setting.html',locals())
        # 邮箱设置
        elif types == 'email':
            # 读取上传的参数
            emailer = request.POST.get("send_emailer",None)
            host = request.POST.get("smtp_host",None)
            port = request.POST.get("smtp_port",None)
            username = request.POST.get("smtp_username",None)
            pwd = request.POST.get("smtp_pwd",None)
            ssl = request.POST.get("smtp_ssl",None)
            # 对密码进行加密
            pwd = enctry(pwd)
            if emailer != None:
                # 更新发件箱
                SysSetting.objects.update_or_create(
                    name = 'send_emailer',
                    defaults={"value":emailer,"types":'email'}
                )
            if host != None:
                # 更新邮箱主机
                SysSetting.objects.update_or_create(
                    name='smtp_host',
                    defaults={"value": host, "types": 'email'}
                )
            if port != None:
                # 更新邮箱主机端口
                SysSetting.objects.update_or_create(
                    name='smtp_port',
                    defaults={"value": port, "types": 'email'}
                )
            if username != None:
                # 更新用户名
                SysSetting.objects.update_or_create(
                    name='username',
                    defaults={"value": username, "types": 'email'}
                )
            if pwd != None:
                # 更新密码
                SysSetting.objects.update_or_create(
                    name='pwd',
                    defaults={"value": pwd, "types": 'email'}
                )
            # 更新SSL
            SysSetting.objects.update_or_create(
                name='smtp_ssl',
                defaults={"value": ssl, "types": 'email'}
            )
            email_settings = SysSetting.objects.filter(types="email")
            if email_settings.count() == 6:
                emailer = email_settings.get(name='send_emailer')
                email_host = email_settings.get(name='smtp_host')
                email_port = email_settings.get(name='smtp_port')
                email_username = email_settings.get(name="username")
                email_ssl = email_settings.get(name="smtp_ssl")
                email_pwd = email_settings.get(name="pwd")
            return render(request, 'app_admin/admin_setting.html',locals())
        # 文档全局设置
        elif types == 'doc':
            # 上传图片大小
            img_size = request.POST.get('img_size', 10)
            try:
                if int(img_size) == 0:
                    img_size = 50
                else:
                    img_size = abs(int(img_size))
            except Exception as e:
                # print(repr(e))
                img_size = 10
            SysSetting.objects.update_or_create(
                name='img_size',
                defaults={'value': img_size, 'types': 'doc'}
            )

            # 附件格式白名单
            attachment_suffix = request.POST.get('attachment_suffix','')
            SysSetting.objects.update_or_create(
                name = 'attachment_suffix',
                defaults = {'value':attachment_suffix,'types':'doc'}
            )
            # 附件大小
            attachment_size = request.POST.get('attachment_size',50)
            try:
                if int(attachment_size) == 0:
                    attachment_size = 50
                else:
                    attachment_size = abs(int(attachment_size))
            except Exception as e:
                # print(repr(e))
                attachment_size = 50
            SysSetting.objects.update_or_create(
                name='attachment_size',
                defaults={'value': attachment_size, 'types': 'doc'}
            )
            return render(request, 'app_admin/admin_setting.html', locals())

@superuser_only
@require_http_methods(['POST'])
def admin_site_config(request):
    try:
        raw = json.loads(request.body.decode('utf-8'))
        data_json = json.loads(raw.get('data', '[]'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        data_json = json.loads(request.POST.get("data", '[]'))
    try:
        for d in data_json:
            if d['type'] == 'email' and d['name'] == 'pwd':
                d['value'] = enctry(d['value'])
            SysSetting.objects.update_or_create(
                name=d['name'],
                defaults={'value': d['value'], 'types': d['type']}
            )
        return JsonResponse({'code':0})
    except:
        logger.exception("更新站点设置出错")
        return JsonResponse({'code':2,'data':'更新出错'})

# 检测版本更新（功能已禁用，保留接口避免前端报错）
def check_update(request):
    """检查版本更新——通过 GitHub Releases API 按语义版本号获取真正最新版本。"""
    import re

    current_version = settings.VERSIONS.strip()
    result = {
        'status': True,
        'current_version': current_version,
        'latest_version': None,
        'has_update': False,
        'update_info': '',
        'changelog': '',
        'download_url': '',
    }

    GITHUB_API = 'https://api.github.com/repos/ispace-top/ispace_doc/releases'

    try:
        import requests
        resp = requests.get(GITHUB_API, timeout=15, headers={'Accept': 'application/vnd.github+json'}, params={'per_page': 20})
        if resp.status_code == 403 and 'X-RateLimit-Remaining' in resp.headers:
            result['update_info'] = _('检查更新请求过于频繁，请稍后重试')
            return JsonResponse(result)
        if resp.status_code != 200:
            result['update_info'] = _('检查更新失败：GitHub API 返回 {code}').format(code=resp.status_code)
            return JsonResponse(result)

        releases = resp.json()
        if not releases:
            result['update_info'] = _('未找到正式版本发布记录')
            return JsonResponse(result)

        # 按语义版本号找出最大者（而非按发布时间）
        best = releases[0]
        best_ver = best.get('tag_name', '').lstrip('v').strip()
        for rel in releases[1:]:
            tag = rel.get('tag_name', '').lstrip('v').strip()
            if tag and re.match(r'^\d', tag) and _version_greater(tag, best_ver):
                best = rel
                best_ver = tag

        if not best_ver or not re.match(r'^\d', best_ver):
            result['update_info'] = _('未找到正式版本发布记录')
            return JsonResponse(result)

        result['latest_version'] = best_ver
        result['download_url'] = best.get('html_url', '')

        if _version_greater(best_ver, current_version):
            result['has_update'] = True
            result['update_info'] = _('发现新版本 v{version}，当前版本为 v{current}').format(
                version=best_ver, current=current_version
            )
            body = best.get('body', '')
            if body:
                result['changelog'] = body[:500]
        else:
            result['update_info'] = _('当前已是最新版本 v{version}').format(version=current_version)

    except Exception as e:
        result['update_info'] = _('检查更新失败：{error}').format(error=str(e)[:100])

    return JsonResponse(result)


def _version_greater(a, b):
    """比较两个语义化版本号，a > b 返回 True。"""
    import re
    def _parse(v):
        parts = re.split(r'[-+]', v)
        nums = [int(x) for x in parts[0].split('.')]
        return nums
    try:
        return _parse(a) > _parse(b)
    except Exception:
        return a != b

# ========== 关于我们 ==========

def _about_context(request):
    """构建关于我们页面上下文。"""
    from django import VERSION as django_version_tuple
    import sys, platform
    return {
        'app_version': settings.VERSIONS,
        'django_version': '.'.join(str(v) for v in django_version_tuple[:3]),
        'python_version': sys.version.split()[0],
        'os_name': platform.system(),
        'os_release': platform.release(),
        'db_engine': settings.DATABASES['default']['ENGINE'],
        'is_superuser': request.user.is_superuser if request.user.is_authenticated else False,
    }


@require_GET
def about(request):
    """公开的关于我们页面。"""
    return render(request, 'app_admin/admin_about.html', _about_context(request))


@superuser_only
@require_GET
def admin_about(request):
    """管理后台关于我们页面。"""
    return render(request, 'app_admin/admin_about.html', _about_context(request))


# 站点数据备份
@superuser_only
@require_POST
def admin_backup(request):
    mode = request.POST.get('mode','data')
    # 定义备份文件路径
    backup_dir = os.path.join(settings.MEDIA_ROOT, 'backup')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    if mode == 'data':
        # 数据库文件路径
        db_files = {
            'db_admin.json': 'app_admin',
            'db_doc.json': 'app_doc',
            'db_api.json': 'app_api'
        }
        backup_files = []
        try:
            # 生成备份文件
            for db_file, app_label in db_files.items():
                dst = os.path.join(backup_dir, db_file)
                with open(dst, 'w', encoding='utf-8') as f:
                    # result = subprocess.run([sys.executable, 'manage.py', 'dumpdata', app_label],stdout=f,stderr=subprocess.PIPE)
                    # if result.returncode != 0:
                    #     raise Exception(f"Error dumping {app_label}: {result.stderr}")
                    out = StringIO()
                    call_command('dumpdata', app_label, stdout=out)
                    f.write(out.getvalue())
                backup_files.append(dst)

            # 压缩备份文件
            zip_file_name = 'isdoc_backup_data_{}.zip'.format(str(int(time.time())))
            zip_file_path = os.path.join(backup_dir, zip_file_name)
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in backup_files:
                    zipf.write(file, os.path.basename(file))
            # shutil.make_archive(os.path.splitext(zip_file_path)[0], 'zip', backup_dir)

            # 删除json文件
            for db_file, app_label in db_files.items():
                os.remove(os.path.join(backup_dir,db_file))

            backup_file_path = "/media/backup/" + zip_file_name
            return JsonResponse({'status':True,'data':backup_file_path})
        except Exception as e:
            return JsonResponse({'status':False,'data':f"An error occurred: {str(e)}"})
    elif mode == 'media':
        try:
            # 压缩备份文件
            zip_file_name = 'isdoc_backup_media_{}.zip'.format(str(int(time.time())))
            zip_file_path = os.path.join(backup_dir, zip_file_name)
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(settings.MEDIA_ROOT):
                    # 排除要忽略的目录
                    dirs[:] = [d for d in dirs if os.path.join(root, d) != os.path.join(settings.MEDIA_ROOT, 'backup')]

                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, settings.MEDIA_ROOT)
                        zipf.write(file_path, arcname)
            backup_file_path = "/media/backup/" + zip_file_name
            return JsonResponse({'status': True, 'data': backup_file_path})
        except Exception as e:
            return JsonResponse({'status': False, 'data': f"导出媒体文件失败: {str(e)}"})
    else:
        return JsonResponse({'status':False,'data':_("不支持的类型")})


# 清除 Django 缓存
@superuser_only
@require_POST
def admin_clear_cache(request):
    from django.core.cache import cache
    try:
        cache.clear()
        return JsonResponse({'status': True, 'data': '缓存已清除'})
    except Exception as e:
        logger.exception("清除缓存失败")
        return JsonResponse({'status': False, 'data': str(e)})


# 重建搜索索引
@superuser_only
@require_POST
def admin_rebuild_index(request):
    try:
        import shutil
        index_dir = os.path.join(settings.BASE_DIR, 'backend', 'apps', 'doc', 'search', 'index')
        if os.path.exists(index_dir):
            shutil.rmtree(index_dir)
        # 索引目录删除后，系统会在下次搜索时自动重建
        return JsonResponse({'status': True, 'data': '搜索索引已清除，下次搜索时将自动重建'})
    except Exception as e:
        logger.exception("重建搜索索引失败")
        return JsonResponse({'status': False, 'data': str(e)})


# Logo 上传
@superuser_only
@require_POST
def admin_upload_logo(request):
    from backend.apps.doc.storage.security import validate_content_type, generate_storage_key
    from backend.apps.doc.storage import get_storage

    logo_type = request.POST.get('logo_type', '')
    valid_types = ['site_logo', 'site_logo_admin', 'site_logo_user_center', 'site_logo_footer']
    if logo_type not in valid_types:
        return JsonResponse({'code': 1, 'data': '无效的Logo类型'})

    file = request.FILES.get('logo_file')
    if not file:
        return JsonResponse({'code': 1, 'data': '未选择文件'})

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico']:
        return JsonResponse({'code': 1, 'data': '不支持的图片格式，支持 PNG/JPG/GIF/SVG/WebP/ICO'})

    # MIME 类型检测（SVG/ICO 除外，它们没有可靠的魔数）
    if ext not in ['.svg', '.ico']:
        file_header = file.read(512)
        file.seek(0)
        allowed = [e.lstrip('.') for e in ['.png', '.jpg', '.jpeg', '.gif', '.webp']]
        is_allowed, _ = validate_content_type(file_header, allowed)
        if not is_allowed:
            return JsonResponse({'code': 1, 'data': '文件内容与扩展名不匹配'})

    # 删除旧 Logo（各种扩展名）
    storage = get_storage()
    for old_ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico']:
        old_key = f"logos/{logo_type}{old_ext}"
        try:
            if storage.exists(old_key):
                storage.delete(old_key)
        except Exception:
            pass

    # 通过存储后端上传
    key = f"logos/{logo_type}{ext}"
    result = storage.upload(file, key, content_type=f"image/{ext.lstrip('.')}")

    relative_url = f"/media/{key}"
    SysSetting.objects.update_or_create(
        name=logo_type,
        defaults={'value': relative_url, 'types': 'basic'}
    )

    return JsonResponse({'code': 0, 'data': relative_url})


# 后台管理
@superuser_only
def admin_center(request):
    breadcrumb_items = [{"name": _('后台管理'), 'url': ''}]
    return render(request,'app_admin/admin_center.html',locals())


# 后台管理菜单
def admin_center_menu(request):
    menu_data = [
        {
            "id": 1,
            "title": _("仪表盘"),
            "type": 1,
            "icon": "layui-icon layui-icon-console",
            "href": reverse('admin_overview'),
        },
        {
            "id": 2,
            "title": _("文档管理"),
            "type": 1,
            "icon": "layui-icon layui-icon-form",
            "href": reverse('doc_manage'),
        },
        {
            "id": 4,
            "title": _("模板管理"),
            "type": 1,
            "icon": "layui-icon layui-icon-templeate-1",
            "href": reverse('doctemp_manage'),
        },
        {
            "id": "my_fodder",
            "title": _("素材管理"),
            "icon": "layui-icon layui-icon-upload-drag",
            "type": 0,
            "href": "",
            "children": [
                {
                    "id": "my_img",
                    "title": _("图片管理"),
                    "icon": "layui-icon layui-icon-face-smile",
                    "type": 1,
                    "openType": "_iframe",
                    "href": reverse("image_manage")
                },
                {
                    "id": "my_attachment",
                    "title": _("附件管理"),
                    "icon": "layui-icon layui-icon-face-cry",
                    "type": 1,
                    "openType": "_iframe",
                    "href": reverse("attachment_manage")
                },
            ]
        },
        {
            "id": 5,
            "title": _("注册码"),
            "type": 1,
            "icon": "layui-icon layui-icon-component",
            "href": reverse('register_code_manage'),
        },
        {
            "id": 6,
            "title": _("用户管理"),
            "type": 1,
            "icon": "layui-icon layui-icon-user",
            "href": reverse('user_manage'),
        },
        {
            "id": 7,
            "title": _("站点设置"),
            "type": 1,
            "icon": "layui-icon layui-icon-set",
            "href": reverse('sys_setting'),
        },
        {
            "id": 8,
            "title": _("分组管理"),
            "type": 1,
            "icon": "layui-icon layui-icon-group",
            "href": reverse('admin_group_manage'),
        },
        {
            "id": 9,
            "title": _("组织架构"),
            "type": 1,
            "icon": "layui-icon layui-icon-tree",
            "href": reverse('admin_org_manage'),
        },
        {
            "id": 10,
            "title": _("回收站"),
            "type": 1,
            "icon": "layui-icon layui-icon-delete",
            "href": reverse('admin_doc_trash'),
        },
        {
            "id": 11,
            "title": _("审计日志"),
            "type": 1,
            "icon": "layui-icon layui-icon-log",
            "href": reverse('admin_audit_log'),
        },
        {
            "id": 12,
            "title": _("登录记录"),
            "type": 1,
            "icon": "layui-icon layui-icon-password",
            "href": reverse('admin_login_records'),
        },
        {
            "id": 13,
            "title": _("评论管理"),
            "type": 1,
            "icon": "layui-icon layui-icon-dialogue",
            "href": reverse('admin_comments'),
        },
        {
            "id": 14,
            "title": _("通知管理"),
            "type": 1,
            "icon": "layui-icon layui-icon-notice",
            "href": reverse('admin_notifications'),
        },
        {
            "id": 15,
            "title": _("系统健康"),
            "type": 1,
            "icon": "layui-icon layui-icon-survey",
            "href": reverse('admin_health'),
        },
        {
            "id": 16,
            "title": _("基础配置"),
            "type": 1,
            "icon": "layui-icon layui-icon-download-circle",
            "href": reverse('admin_storage'),
        },
        {
            "id": 17,
            "title": _("WebHook"),
            "type": 1,
            "icon": "layui-icon layui-icon-link",
            "href": reverse('admin_webhook'),
        },
        {
            "id": 18,
            "title": _("系统日志"),
            "type": 1,
            "icon": "layui-icon layui-icon-file-b",
            "href": reverse('admin_syslog'),
        },
        {
            "id": 20,
            "title": _("认证配置"),
            "type": 1,
            "icon": "layui-icon layui-icon-password",
            "href": reverse('admin_auth'),
        },
        {
            "id": 21,
            "title": _("通知渠道"),
            "type": 1,
            "icon": "layui-icon layui-icon-notice",
            "href": reverse('admin_notification_channels'),
        },
        {
            "id": 22,
            "title": _("关于我们"),
            "type": 1,
            "icon": "layui-icon layui-icon-about",
            "href": reverse('admin_about'),
        },

    ]
    return JsonResponse(menu_data,safe=False)


# ========== v1.0 管理后台新增页面 ==========

@superuser_only
@require_GET
def admin_group(request):
    """分组管理页面。"""
    return render(request, 'app_admin/admin_group.html', locals())


@superuser_only
@require_GET
def admin_org(request):
    """组织架构管理页面。"""
    return render(request, 'app_admin/admin_org.html', locals())


@superuser_only
@require_GET
def admin_doc_trash(request):
    """文档回收站管理页面（软删除恢复）。"""
    return render(request, 'app_admin/admin_doc_trash.html', locals())


@superuser_only
@require_GET
def admin_audit_log(request):
    """操作审计日志页面。"""
    return render(request, 'app_admin/admin_audit_log.html', locals())


# ========== 管理后台 API ==========

@superuser_only
def api_admin_groups(request):
    """分组管理 API：列表 / 创建 / 更新 / 删除。"""
    from backend.apps.doc.models import Group, GroupMember
    from django.contrib.auth.models import User as AuthUser

    if request.method == 'GET':
        q = request.GET.get('q', '').strip()
        groups = Group.objects.all().order_by('-created_at')
        if q:
            groups = groups.filter(name__icontains=q)
        total = groups.count()
        page = int(request.GET.get('page', 1))
        size = int(request.GET.get('size', 20))
        groups = groups[(page - 1) * size:page * size]
        result = [{
            'id': g.id, 'name': g.name, 'description': g.description,
            'owner_name': g.owner.first_name or g.owner.username,
            'member_count': g.member_count,
            'created_at': g.created_at.strftime('%Y-%m-%d %H:%M'),
        } for g in groups]
        return JsonResponse({'status': True, 'groups': result, 'total': total})

    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        desc = data.get('description', '').strip()[:256]
        if not name or len(name) > 64:
            return JsonResponse({'status': False, 'message': '分组名称需在1-64字符之间'})
        if Group.objects.filter(name=name).exists():
            return JsonResponse({'status': False, 'message': '分组名称已存在'})
        Group.objects.create(name=name, description=desc, owner=request.user)
        return JsonResponse({'status': True, 'message': '创建成功'})

    if request.method == 'PUT':
        data = json.loads(request.body)
        gid = data.get('id')
        try:
            g = Group.objects.get(pk=gid)
        except Group.DoesNotExist:
            return JsonResponse({'status': False, 'message': '分组不存在'}, status=404)
        if 'name' in data:
            g.name = data['name'].strip()
        if 'description' in data:
            g.description = data['description'].strip()[:256]
        g.save(update_fields=['name', 'description'])
        return JsonResponse({'status': True, 'message': '更新成功'})

    if request.method == 'DELETE':
        data = json.loads(request.body)
        gid = data.get('id')
        try:
            g = Group.objects.get(pk=gid)
        except Group.DoesNotExist:
            return JsonResponse({'status': False, 'message': '分组不存在'}, status=404)
        g.delete()
        return JsonResponse({'status': True, 'message': '已删除'})


@superuser_only
def api_admin_trash(request):
    """文档回收站 API：列表 / 恢复 / 永久删除。"""
    from django.db.models import Q

    if request.method == 'GET':
        q = request.GET.get('q', '').strip()
        docs = Doc.objects.filter(is_deleted=True).select_related('create_user', 'deleted_by').order_by('-deleted_at')
        if q:
            matching_top_ids = Doc.objects.filter(name__icontains=q, parent_doc=0).values_list('id', flat=True)
            docs = docs.filter(Q(name__icontains=q) | Q(top_doc__in=matching_top_ids))
        total = docs.count()
        page = int(request.GET.get('page', 1))
        size = int(request.GET.get('size', 20))
        docs = docs[(page - 1) * size:page * size]

        # 批量获取 top_doc 名称
        top_ids = [d.top_doc for d in docs if d.top_doc]
        top_names = {}
        if top_ids:
            top_names = {d.id: d.name for d in Doc.objects.filter(id__in=top_ids)}

        result = [{
            'id': d.id, 'name': d.name, 'top_doc_name': top_names.get(d.top_doc, ''),
            'creator_name': d.create_user.first_name or d.create_user.username if d.create_user else '',
            'deleter_name': d.deleted_by.first_name or d.deleted_by.username if d.deleted_by else '',
            'deleted_at': d.deleted_at.strftime('%Y-%m-%d %H:%M') if d.deleted_at else '',
            'parent_id': d.parent_doc,
            'has_children': Doc.objects.filter(parent_doc=d.id).exists(),
        } for d in docs]
        return JsonResponse({'status': True, 'docs': result, 'total': total})

    if request.method == 'POST':
        data = json.loads(request.body)
        doc_ids = data.get('doc_ids', [])
        if not doc_ids:
            return JsonResponse({'status': False, 'message': '请选择要恢复的文档'})
        count = 0
        for did in doc_ids:
            try:
                d = Doc.objects.get(pk=did, is_deleted=True)
                d.is_deleted = False
                d.deleted_at = None
                d.deleted_by = None
                d.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
                count += 1
            except Doc.DoesNotExist:
                pass
        return JsonResponse({'status': True, 'message': f'已恢复 {count} 篇文档'})

    if request.method == 'DELETE':
        data = json.loads(request.body)
        doc_ids = data.get('doc_ids', [])
        if not doc_ids:
            return JsonResponse({'status': False, 'message': '请选择文档'})
        count = Doc.objects.filter(pk__in=doc_ids, is_deleted=True).delete()[0]
        return JsonResponse({'status': True, 'message': f'已永久删除 {count} 篇文档'})


@superuser_only
def api_admin_audit_logs(request):
    """审计日志 API：列表查询（分页+筛选）。"""
    q_type = request.GET.get('type', '')  # 操作类型筛选
    q_user = request.GET.get('user', '')  # 操作人筛选
    q_date_start = request.GET.get('date_start', '')  # 开始日期
    q_date_end = request.GET.get('date_end', '')  # 结束日期

    logs = AuditLog.objects.select_related('user').all().order_by('-created_at')
    if q_type:
        logs = logs.filter(action=q_type)
    if q_user:
        logs = logs.filter(Q(user__username__icontains=q_user) | Q(user__first_name__icontains=q_user))
    if q_date_start:
        logs = logs.filter(created_at__gte=q_date_start)
    if q_date_end:
        logs = logs.filter(created_at__lte=q_date_end + ' 23:59:59')

    total = logs.count()
    page = int(request.GET.get('page', 1))
    size = int(request.GET.get('size', 30))
    logs = logs[(page - 1) * size:page * size]
    result = [{
        'id': l.id,
        'user_name': l.user.first_name or l.user.username if l.user else l.username or '',
        'action_type': l.action,
        'action_name': l.get_action_display(),
        'target_type': l.target_type or '',
        'target_id': str(l.target_id) if l.target_id else '',
        'detail': l.detail or '',
        'ip': l.ip_address or '',
        'created_at': l.created_at.strftime('%Y-%m-%d %H:%M:%S') if l.created_at else '',
    } for l in logs]
    return JsonResponse({'status': True, 'logs': result, 'total': total})


@superuser_only
def api_admin_org_manage(request):
    """组织架构管理 API（超级管理员权限）"""
    from backend.apps.doc.models import OrgNode, OrgUser
    from django.contrib.auth.models import User as AuthUser

    if request.method == 'GET':
        action = request.GET.get('action', 'tree')
        if action == 'tree':
            roots = OrgNode.objects.filter(parent__isnull=True).order_by('sort_order', 'id')
            def build(n):
                d = {'id': n.id, 'name': n.name, 'parent_id': n.parent_id, 'path': n.path,
                     'depth': n.depth, 'sort_order': n.sort_order, 'admin_id': n.admin_id,
                     'member_count': n.org_users.count()}
                children = OrgNode.objects.filter(parent=n).order_by('sort_order', 'id')
                d['children'] = [build(c) for c in children]
                return d
            tree = [build(r) for r in roots]
            return JsonResponse({'status': True, 'tree': tree})
        elif action == 'members':
            nid = request.GET.get('node_id')
            try:
                node = OrgNode.objects.get(pk=nid)
            except OrgNode.DoesNotExist:
                return JsonResponse({'status': False, 'message': '节点不存在'}, status=404)
            ous = OrgUser.objects.filter(org_node=node).select_related('user__profile')
            members = [{
                'id': ou.user.id, 'username': ou.user.username,
                'display_name': ou.user.first_name or ou.user.username,
                'is_primary': ou.is_primary,
            } for ou in ous]
            return JsonResponse({'status': True, 'members': members, 'node_name': node.name})

    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action', 'create')
        if action == 'create':
            name = data.get('name', '').strip()
            parent_id = data.get('parent_id')
            if not name:
                return JsonResponse({'status': False, 'message': '请输入节点名称'})
            parent = None
            if parent_id:
                try:
                    parent = OrgNode.objects.get(pk=parent_id)
                except OrgNode.DoesNotExist:
                    return JsonResponse({'status': False, 'message': '父节点不存在'})
            node = OrgNode.objects.create(name=name, parent=parent)
            from backend.apps.doc.views_org import _rebuild_path
            _rebuild_path(node)
            return JsonResponse({'status': True, 'message': '创建成功', 'id': node.id})
        elif action == 'rename':
            nid = data.get('id')
            name = data.get('name', '').strip()
            if not name:
                return JsonResponse({'status': False, 'message': '请输入名称'})
            OrgNode.objects.filter(pk=nid).update(name=name)
            return JsonResponse({'status': True, 'message': '已重命名'})
        elif action == 'delete':
            nid = data.get('id')
            try:
                node = OrgNode.objects.get(pk=nid)
            except OrgNode.DoesNotExist:
                return JsonResponse({'status': False, 'message': '节点不存在'})
            # 子节点上移
            OrgNode.objects.filter(parent=node).update(parent=node.parent)
            node.delete()
            return JsonResponse({'status': True, 'message': '已删除'})
        elif action == 'move':
            nid = data.get('id')
            new_parent_id = data.get('new_parent_id')
            try:
                node = OrgNode.objects.get(pk=nid)
            except OrgNode.DoesNotExist:
                return JsonResponse({'status': False, 'message': '节点不存在'})
            parent = None
            if new_parent_id:
                try:
                    parent = OrgNode.objects.get(pk=new_parent_id)
                except OrgNode.DoesNotExist:
                    return JsonResponse({'status': False, 'message': '目标父节点不存在'})
            node.parent = parent
            node.save(update_fields=['parent'])
            from backend.apps.doc.views_org import _rebuild_path
            _rebuild_path(node)
            return JsonResponse({'status': True, 'message': '已移动'})
        elif action == 'add_members':
            nid = data.get('id')
            user_ids = data.get('user_ids', [])
            try:
                node = OrgNode.objects.get(pk=nid)
            except OrgNode.DoesNotExist:
                return JsonResponse({'status': False, 'message': '节点不存在'})
            added = 0
            for uid in user_ids:
                _, created = OrgUser.objects.get_or_create(org_node=node, user_id=uid)
                if created:
                    added += 1
                    try:
                        from backend.apps.doc.services import NotificationService
                        added_user = AuthUser.objects.get(pk=uid)
                        NotificationService.send(
                            recipient=added_user, notification_type='perm_change',
                            title='你已被添加到「{}」部门'.format(node.name),
                            sender=request.user, send_email=True,
                            body='{} 将你添加到了「{}」部门'.format(
                                request.user.first_name or request.user.username, node.name),
                            link='/user_center/?tab=my_org',
                        )
                    except Exception:
                        pass
            if added > 0:
                from backend.apps.doc.services import PermissionService
                PermissionService.invalidate_for_org(nid)
            return JsonResponse({'status': True, 'message': f'已添加 {added} 人'})
        elif action == 'remove_member':
            nid = data.get('id')
            uid = data.get('user_id')
            deleted, _ = OrgUser.objects.filter(org_node_id=nid, user_id=uid).delete()
            if deleted:
                try:
                    from backend.apps.doc.services import NotificationService
                    removed_user = AuthUser.objects.get(pk=uid)
                    node = OrgNode.objects.get(pk=nid)
                    NotificationService.send(
                        recipient=removed_user, notification_type='perm_change',
                        title='你已被移出「{}」部门'.format(node.name),
                        sender=request.user, send_email=True,
                        body='{} 将你移出了「{}」部门'.format(
                            request.user.first_name or request.user.username, node.name),
                        link='/user_center/?tab=my_org',
                    )
                except Exception:
                    pass
                from backend.apps.doc.services import PermissionService
                PermissionService.invalidate_for_org(nid)
            return JsonResponse({'status': True, 'message': '已移除'})

    return JsonResponse({'status': False, 'message': '无效请求'}, status=400)


# ========== v1.0 管理后台新增：登录记录 ==========

@superuser_only
@require_GET
def admin_login_records(request):
    """登录记录页面。"""
    return render(request, 'app_admin/admin_login_records.html', locals())


@superuser_only
def api_admin_login_records(request):
    """登录记录 API：列表查询（分页+筛选）。"""
    q_user = request.GET.get('user', '')
    q_result = request.GET.get('result', '')  # success / fail / ''
    q_date_start = request.GET.get('date_start', '')
    q_date_end = request.GET.get('date_end', '')

    records = LoginRecord.objects.select_related('user').all().order_by('-created_at')
    if q_user:
        records = records.filter(username__icontains=q_user)
    if q_result == 'success':
        records = records.filter(success=True)
    elif q_result == 'fail':
        records = records.filter(success=False)
    if q_date_start:
        records = records.filter(created_at__gte=q_date_start)
    if q_date_end:
        records = records.filter(created_at__lte=q_date_end + ' 23:59:59')

    total = records.count()
    page = int(request.GET.get('page', 1))
    size = int(request.GET.get('size', 20))
    records = records[(page - 1) * size:page * size]
    result = [{
        'id': r.id,
        'username': r.username,
        'user_name': (r.user.first_name or r.user.username) if r.user else r.username,
        'ip_address': r.ip_address or '-',
        'user_agent': r.user_agent or '',
        'success': r.success,
        'failure_reason': r.failure_reason or '',
        'created_at': r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else '',
    } for r in records]
    return JsonResponse({'status': True, 'records': result, 'total': total})


# ========== v1.0 管理后台新增：评论管理 ==========

@superuser_only
@require_GET
def admin_comments(request):
    """评论管理页面。"""
    return render(request, 'app_admin/admin_comments.html', locals())


@superuser_only
def api_admin_comments(request):
    """评论管理 API：列表查询（分页+筛选）+ 删除/恢复。"""
    if request.method == 'GET':
        q_doc = request.GET.get('doc', '')
        q_user = request.GET.get('user', '')
        q_status = request.GET.get('status', '')  # active / deleted / ''

        comments = DocComment.objects.select_related('doc', 'user').all().order_by('-create_time')
        if q_doc:
            comments = comments.filter(doc__name__icontains=q_doc)
        if q_user:
            comments = comments.filter(user__username__icontains=q_user)
        if q_status == 'active':
            comments = comments.filter(is_active=True)
        elif q_status == 'deleted':
            comments = comments.filter(is_active=False)

        total = comments.count()
        page = int(request.GET.get('page', 1))
        size = int(request.GET.get('size', 20))
        comments = comments[(page - 1) * size:page * size]
        result = [{
            'id': c.id,
            'doc_id': c.doc_id,
            'doc_name': c.doc.name,
            'user_name': c.user.first_name or c.user.username,
            'content': c.content,
            'content_short': (c.content[:80] + '...') if len(c.content) > 80 else c.content,
            'reply_count': c.reply_count,
            'is_active': c.is_active,
            'create_time': c.create_time.strftime('%Y-%m-%d %H:%M:%S') if c.create_time else '',
        } for c in comments]
        return JsonResponse({'status': True, 'comments': result, 'total': total})

    elif request.method in ('POST', 'PUT'):
        data = json.loads(request.body)
        comment_id = data.get('id')
        action = data.get('action', 'toggle')  # toggle / delete / restore
        try:
            comment = DocComment.objects.get(pk=comment_id)
            if action == 'toggle' or action == 'delete':
                comment.is_active = False
            elif action == 'restore':
                comment.is_active = True
            comment.save(update_fields=['is_active'])
            return JsonResponse({'status': True, 'message': '操作成功'})
        except DocComment.DoesNotExist:
            return JsonResponse({'status': False, 'message': '评论不存在'})

    return JsonResponse({'status': False, 'message': '无效请求'}, status=400)


# ========== v1.0 管理后台新增：通知管理 ==========

@superuser_only
@require_GET
def admin_notifications(request):
    """通知管理页面。"""
    return render(request, 'app_admin/admin_notifications.html', locals())


@superuser_only
def api_admin_notifications(request):
    """通知管理 API：列表查询（分页+筛选）。"""
    q_recipient = request.GET.get('recipient', '')
    q_type = request.GET.get('type', '')  # 通知类型
    q_read = request.GET.get('read', '')  # read / unread / ''

    notifications = Notification.objects.select_related('recipient', 'sender').all().order_by('-created_at')
    if q_recipient:
        notifications = notifications.filter(recipient__username__icontains=q_recipient)
    if q_type:
        notifications = notifications.filter(notification_type=q_type)
    if q_read == 'read':
        notifications = notifications.filter(is_read=True)
    elif q_read == 'unread':
        notifications = notifications.filter(is_read=False)

    total = notifications.count()
    page = int(request.GET.get('page', 1))
    size = int(request.GET.get('size', 20))
    notifications = notifications[(page - 1) * size:page * size]
    result = [{
        'id': n.id,
        'recipient_name': n.recipient.first_name or n.recipient.username,
        'sender_name': (n.sender.first_name or n.sender.username) if n.sender else '-',
        'notification_type': n.notification_type,
        'type_display': n.get_notification_type_display(),
        'title': n.title,
        'body': n.body,
        'is_read': n.is_read,
        'link': n.link,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S') if n.created_at else '',
    } for n in notifications]
    return JsonResponse({'status': True, 'notifications': result, 'total': total})


# ========== v1.0 管理后台新增：系统健康 ==========

@superuser_only
@require_GET
def admin_health(request):
    """系统健康检查页面。"""
    return render(request, 'app_admin/admin_health.html', locals())


@superuser_only
def api_admin_health(request):
    """系统健康检查 API（v1.0 增强版）。"""
    from django.db import connections
    from django.conf import settings
    import os, sys, time

    health = {
        'overall': 'ok',
        'score': 100,
        'anomalies': [],
    }
    anomalies = []

    def _add_anomaly(level, msg):
        anomalies.append({'level': level, 'message': msg})

    # ---- 运行时长 ----
    try:
        import psutil
        proc = psutil.Process()
        start_ts = proc.create_time()
        uptime_seconds = int(time.time() - start_ts)
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        parts = []
        if days: parts.append(f'{days} 天')
        if hours: parts.append(f'{hours} 小时')
        if minutes: parts.append(f'{minutes} 分钟')
        if not parts: parts.append(f'{seconds} 秒')
        health['uptime'] = {
            'seconds': uptime_seconds,
            'display': ' '.join(parts),
            'start_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_ts)),
        }
    except Exception:
        health['uptime'] = {'seconds': 0, 'display': '未知', 'start_time': '-'}

    # ---- CPU ----
    try:
        import psutil
        psutil.cpu_percent()  # prime: first call returns 0.0, starts measurement
        cpu_pct = psutil.cpu_percent(interval=0.3)
        cpu_cores = psutil.cpu_count(logical=True)
        health['cpu'] = {'percent': round(cpu_pct, 1), 'cores': cpu_cores}
        if cpu_pct > 90:
            _add_anomaly('warn', f'CPU 使用率过高（{cpu_pct:.0f}%），请检查是否有异常进程')
    except Exception:
        health['cpu'] = {'percent': 0, 'cores': os.cpu_count() or 1}

    # ---- 内存 ----
    try:
        import psutil
        mem = psutil.virtual_memory()
        health['memory'] = {
            'percent': mem.percent,
            'total': _format_bytes(mem.total),
            'used': _format_bytes(mem.used),
            'available': _format_bytes(mem.available),
        }
        if mem.percent > 90:
            _add_anomaly('warn', f'内存使用率过高（{mem.percent:.0f}%），可能影响服务响应')
    except Exception:
        health['memory'] = {'percent': 0, 'total': '-', 'used': '-', 'available': '-'}

    # ---- 磁盘 ----
    try:
        import shutil
        usage = shutil.disk_usage(settings.BASE_DIR)
        disk_pct = round(usage.used / usage.total * 100, 1)
        health['disk'] = {
            'status': 'ok' if disk_pct < 80 else ('warn' if disk_pct < 95 else 'error'),
            'percent': disk_pct,
            'total': _format_bytes(usage.total),
            'used': _format_bytes(usage.used),
            'free': _format_bytes(usage.free),
        }
        if disk_pct > 95:
            _add_anomaly('error', f'磁盘空间即将耗尽（{disk_pct:.0f}%），请尽快清理')
        elif disk_pct > 80:
            _add_anomaly('warn', f'磁盘使用率较高（{disk_pct:.0f}%），建议关注')
    except Exception as e:
        health['disk'] = {'status': 'error', 'percent': 0, 'total': '-', 'used': '-', 'free': '-'}

    # ---- 数据库 ----
    try:
        db_conn = connections['default']
        cursor = db_conn.cursor()
        cursor.execute('SELECT 1')
        health['database'] = {'status': 'ok', 'message': '连接正常', 'vendor': settings.DATABASES['default']['ENGINE']}
        # Try to get version
        try:
            from django.db import connection as dj_conn
            health['database']['version'] = dj_conn.pg_version if hasattr(dj_conn, 'pg_version') else '-'
        except Exception:
            health['database']['version'] = '-'
    except Exception as e:
        health['database'] = {'status': 'error', 'message': str(e), 'vendor': '', 'version': '-'}
        _add_anomaly('error', f'数据库连接异常：{str(e)[:100]}')

    # ---- 缓存 ----
    try:
        from django.core.cache import cache
        cache.set('_health_check', 'ok', 5)
        time.sleep(0.01)
        if cache.get('_health_check') != 'ok':
            health['cache'] = {'status': 'warn', 'message': '缓存读写异常'}
            _add_anomaly('warn', '缓存读写不一致，可能存在缓存服务问题')
        else:
            health['cache'] = {'status': 'ok', 'message': '读写正常'}
    except Exception as e:
        health['cache'] = {'status': 'error', 'message': f'缓存不可用：{str(e)[:80]}'}
        _add_anomaly('error', '缓存服务不可用')

    # ---- 邮件服务 ----
    try:
        from backend.apps.doc.email_service import EmailService
        if not EmailService.is_enabled():
            health['email'] = {'status': 'disabled', 'message': '邮件功能未启用'}
        else:
            config = EmailService._get_config()
            import socket
            smtp_host = config.get('smtp_host', '')
            smtp_port = int(config.get('smtp_port', 465))
            use_ssl = config.get('smtp_ssl') == 'on'
            if use_ssl:
                import smtplib
                s = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=5)
            else:
                import smtplib
                s = smtplib.SMTP(smtp_host, smtp_port, timeout=5)
            s.login(config['username'], config.get('pwd', ''))
            s.quit()
            health['email'] = {'status': 'ok', 'message': f'SMTP 连接正常 ({smtp_host}:{smtp_port})'}
    except Exception as e:
        err_msg = str(e)[:100]
        health['email'] = {'status': 'error', 'message': err_msg}
        _add_anomaly('warn', f'邮件服务异常：{err_msg}')

    # ---- 媒体文件 ----
    try:
        media_root = settings.MEDIA_ROOT
        if os.path.isdir(media_root):
            total_size = 0
            file_count = 0
            for dirpath, dirnames, filenames in os.walk(media_root):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                        file_count += 1
                    except OSError:
                        pass
            health['media'] = {
                'status': 'ok',
                'file_count': file_count,
                'total_size': _format_bytes(total_size),
            }
        else:
            health['media'] = {'status': 'ok', 'file_count': 0, 'total_size': '0 B'}
    except Exception as e:
        health['media'] = {'status': 'error', 'message': str(e), 'file_count': 0, 'total_size': '-'}

    # ---- 文件存储 ----
    try:
        storage_backend = getattr(settings, 'ISDOC_STORAGE_BACKEND', 'local')
        media_root = settings.MEDIA_ROOT
        # 存储后端类型
        storage_types = {
            'local': '本地文件系统',
            's3': 'Amazon S3',
            'oss': '阿里云 OSS',
            'cos': '腾讯云 COS',
        }
        storage_label = storage_types.get(storage_backend, storage_backend)
        # 本地存储：检查目录是否可读写
        if storage_backend == 'local':
            if os.path.isdir(media_root):
                writable = os.access(media_root, os.W_OK)
                health['storage'] = {
                    'status': 'ok' if writable else 'warn',
                    'type': storage_label,
                    'message': f'{storage_label} — {media_root}' + (' (可读写)' if writable else ' (不可写入)'),
                }
                if not writable:
                    _add_anomaly('warn', f'媒体文件目录不可写入：{media_root}')
            else:
                health['storage'] = {
                    'status': 'warn',
                    'type': storage_label,
                    'message': f'目录不存在：{media_root}',
                }
        else:
            # 远程存储：检查是否配置
            has_config = bool(getattr(settings, 'AWS_ACCESS_KEY_ID', None) or getattr(settings, 'OSS_ACCESS_KEY_ID', None))
            health['storage'] = {
                'status': 'ok' if has_config else 'warn',
                'type': storage_label,
                'message': f'{storage_label}' + (' 已配置' if has_config else ' 未配置密钥'),
            }
            if not has_config:
                _add_anomaly('warn', f'远程存储 "{storage_label}" 未配置访问密钥')
    except Exception as e:
        health['storage'] = {'status': 'error', 'type': '-', 'message': str(e)[:80]}

    # ---- 企业微信 / OA 连接 ----
    try:
        import configparser
        from backend.apps.doc.storage.config import CONFIG_PATH as _cfg_path
        cfp = configparser.ConfigParser()
        cfp.read(_cfg_path, encoding='utf-8')

        if cfp.has_section('auth.wecom') and cfp.getboolean('auth.wecom', 'enabled', fallback=True):
            corp_id = cfp.get('auth.wecom', 'corp_id', fallback='')
            corp_secret = cfp.get('auth.wecom', 'corp_secret', fallback='')
            if corp_id and corp_secret:
                try:
                    resp = requests.get(
                        'https://qyapi.weixin.qq.com/cgi-bin/gettoken',
                        params={'corpid': corp_id, 'corpsecret': corp_secret},
                        timeout=10,
                    )
                    token_data = resp.json()
                    if token_data.get('errcode') == 0:
                        health['wecom'] = {'status': 'ok', 'message': f'企业微信连接正常 (corp_id: {corp_id[:6]}***)'}
                    else:
                        health['wecom'] = {'status': 'error', 'message': f'Token 获取失败: {token_data.get("errmsg", "未知错误")[:60]}'}
                        _add_anomaly('warn', f'企业微信连接异常：{token_data.get("errmsg", "")}')
                except Exception as e:
                    health['wecom'] = {'status': 'error', 'message': f'API 请求失败: {str(e)[:60]}'}
                    _add_anomaly('warn', f'企业微信 API 不可达：{str(e)[:60]}')
            else:
                health['wecom'] = {'status': 'disabled', 'message': '企业微信未配置完整参数'}
        else:
            health['wecom'] = {'status': 'disabled', 'message': '未启用'}
    except Exception as e:
        health['wecom'] = {'status': 'disabled', 'message': str(e)[:60]}

    # ---- 通知渠道 ----
    try:
        from backend.apps.doc.notification_channels import NotificationChannelManager
        channels_status = {}
        manager = NotificationChannelManager()
        for ch_id, ch_instance in manager._channels.items() if hasattr(manager, '_channels') else []:
            channels_status[ch_id] = '已配置'
        # Fallback: manually check core channels
        ch_info = {}
        # 站内通知 — 始终可用
        ch_info['in_app'] = {'status': 'ok', 'message': '站内通知可用'}
        # 邮件通知
        from backend.apps.doc.email_service import EmailService
        ch_info['email'] = {
            'status': 'ok' if EmailService.is_enabled() else 'disabled',
            'message': 'SMTP 已配置' if EmailService.is_enabled() else '未启用',
        }
        # 企业微信通知
        has_wecom = bool(cfp.has_section('auth.wecom') and cfp.get('auth.wecom', 'corp_id', fallback=''))
        ch_info['wecom'] = {
            'status': 'ok' if has_wecom else 'disabled',
            'message': '企业微信通知可用' if has_wecom else '未配置企业微信',
        }
        health['notification_channels'] = ch_info
    except Exception as e:
        health['notification_channels'] = {'error': {'status': 'error', 'message': str(e)[:60]}}

    # ---- 系统负载 (load average) — 基于采样历史的长周期统计 ----
    try:
        import json as _json
        from django.core.cache import cache
        import psutil as _ps

        cpu_cores = _ps.cpu_count(logical=True)
        now_ts = time.time()

        # 获取当前负载（系统 1 分钟 load average 作为瞬时采样点）
        try:
            current_load = _ps.getloadavg()[0]
        except (ImportError, AttributeError):
            # Windows: 用 CPU 使用率近似
            current_load = _ps.cpu_percent(interval=0.1) / 100.0

        # 从缓存读取历史采样队列
        cache_key = '_health_load_samples'
        samples = cache.get(cache_key) or []
        # 追加本次采样
        samples.append({'ts': now_ts, 'v': round(current_load, 3)})

        # 清理过期数据（保留最近 8 天的采样）
        cutoff = now_ts - (8 * 86400)
        samples = [s for s in samples if s['ts'] > cutoff]

        # 写回缓存（24 小时过期）
        cache.set(cache_key, samples, 86400)

        # 计算各窗口平均值
        def _avg_in_window(seconds):
            window_start = now_ts - seconds
            window_samples = [s['v'] for s in samples if s['ts'] > window_start]
            if not window_samples:
                return round(current_load, 2)
            return round(sum(window_samples) / len(window_samples), 2)

        health['load_avg'] = {
            '1h': _avg_in_window(3600),
            '24h': _avg_in_window(86400),
            '1w': _avg_in_window(604800),
            'cpu_cores': cpu_cores,
            'sample_count': len(samples),
            'current': round(current_load, 2),
        }
    except Exception:
        health['load_avg'] = {'1h': None, '24h': None, '1w': None, 'cpu_cores': os.cpu_count() or 1, 'sample_count': 0, 'current': None}

    # ---- 并发数 / 请求统计 ----
    try:
        import psutil
        from django.core.cache import cache
        proc = psutil.Process()
        current_threads = proc.num_threads()
        cpu_load = psutil.cpu_percent(interval=0.1)
        try:
            connections = len(proc.connections()) if hasattr(proc, 'connections') else 0
        except Exception:
            connections = 0

        # 峰值并发追踪：每次检测到更高线程数则更新峰值
        peak_key = '_health_peak_concurrency'
        peak_ts_key = '_health_peak_concurrency_ts'
        stored_peak = cache.get(peak_key) or 0
        peak_ts = cache.get(peak_ts_key) or 0

        if current_threads > stored_peak:
            stored_peak = current_threads
            cache.set(peak_key, stored_peak, 3600 * 24 * 7)  # 7 天峰值
            cache.set(peak_ts_key, time.time(), 3600 * 24 * 7)

        # 获取过去 24 小时的请求统计数据（如果有中间件记录的话）
        req_cache_key = '_health_req_samples'
        req_samples = cache.get(req_cache_key) or []
        now_ts_req = time.time()
        # 清理老旧请求记录
        req_samples = [r for r in req_samples if r > now_ts_req - 86400]
        req_count_24h = len(req_samples)

        health['concurrency'] = {
            'current_threads': current_threads,
            'active_connections': connections,
            'cpu_load': round(cpu_load, 1),
            'recent_peak': max(stored_peak, current_threads),
            'peak_time': time.strftime('%m-%d %H:%M', time.localtime(peak_ts)) if peak_ts else '-',
            'requests_24h': req_count_24h,
        }
    except Exception:
        health['concurrency'] = {
            'current_threads': 0,
            'active_connections': 0,
            'cpu_load': 0,
            'recent_peak': 0,
            'peak_time': '-',
            'requests_24h': 0,
        }

    # ---- Python 进程 ----
    try:
        import psutil
        proc = psutil.Process()
        mem_info = proc.memory_info()
        health['python'] = {
            'pid': proc.pid,
            'memory_mb': round(mem_info.rss / (1024 * 1024), 1),
            'threads': proc.num_threads(),
            'open_files': len(proc.open_files()) if hasattr(proc, 'open_files') else '-',
        }
    except Exception:
        health['python'] = {'pid': os.getpid(), 'memory_mb': 0, 'threads': 0, 'open_files': '-'}

    # ---- 系统信息 ----
    health['system'] = {
        'django_version': import_module_version('django'),
        'python_version': sys.version.split()[0],
        'os': f'{sys.platform}',
        'debug': settings.DEBUG,
    }
    if settings.DEBUG:
        _add_anomaly('warn', '当前站点处于 Debug 模式，生产环境请务必关闭 DEBUG')

    # ---- 计算整体评分 ----
    checks = [
        ('database', _('数据库连接'), 'ok', 20),
        ('cache', _('缓存服务'), 'ok', 10),
        ('email', _('邮件服务'), 'ok', 8),
        ('disk', _('磁盘空间'), 'ok', 15),
        ('storage', _('文件存储'), 'ok', 10),
        ('wecom', _('企业微信'), 'ok', 5),
        ('memory', _('内存使用'), 'ok', 10),
        ('cpu', _('CPU 使用'), 'ok', 8),
    ]
    score = 0
    max_score = sum(c[3] for c in checks)  # 86
    deductions = []
    for key, label, target, weight in checks:
        item = health.get(key, {})
        status = item.get('status', item.get('percent', 100))
        earned = 0
        reason = ''
        if key == 'disk':
            disk_pct = item.get('percent', 0)
            if disk_pct > 95:
                reason = _('磁盘空间即将耗尽 ({pct}%)').format(pct=disk_pct)
            elif disk_pct > 80:
                earned = weight * 0.5
                reason = _('磁盘使用率较高 ({pct}%)').format(pct=disk_pct)
            else:
                earned = weight
        elif key == 'memory':
            mem_pct = health.get('memory', {}).get('percent', 0)
            if mem_pct > 95:
                reason = _('内存使用率极高 ({pct}%)').format(pct=mem_pct)
            elif mem_pct > 80:
                earned = weight * 0.5
                reason = _('内存使用率较高 ({pct}%)').format(pct=mem_pct)
            else:
                earned = weight
        elif key == 'cpu':
            cpu_pct2 = health.get('cpu', {}).get('percent', 0)
            if cpu_pct2 > 95:
                reason = _('CPU 使用率极高 ({pct}%)').format(pct=cpu_pct2)
            elif cpu_pct2 > 80:
                earned = weight * 0.5
                reason = _('CPU 使用率较高 ({pct}%)').format(pct=cpu_pct2)
            else:
                earned = weight
        elif status == target:
            earned = weight
        elif status == 'warn':
            earned = weight * 0.5
            reason = item.get('message', _('状态异常'))
        else:
            reason = item.get('message', _('服务不可用'))
        score += earned
        if earned < weight:
            deductions.append({
                'check': label,
                'weight': weight,
                'earned': round(earned, 1),
                'deducted': round(weight - earned, 1),
                'reason': reason or _('未达标'),
            })
    # 归一化到百分制
    if max_score > 0:
        normalized_score = round(score / max_score * 100)
        total_deducted_norm = 100 - normalized_score
        total_raw_deducted = sum(d['deducted'] for d in deductions)
        if total_raw_deducted > 0 and deductions:
            for i, d in enumerate(deductions):
                if i == len(deductions) - 1:
                    # 最后一项用减法确保总和精确等于 total_deducted_norm
                    d['deducted_norm'] = round(total_deducted_norm - sum(
                        dd.get('deducted_norm', 0) for dd in deductions[:i]
                    ), 1)
                else:
                    d['deducted_norm'] = round(d['deducted'] / total_raw_deducted * total_deducted_norm, 1)
                if d['earned'] == 0:
                    d['earned_norm'] = 0
                else:
                    d['earned_norm'] = round(d['weight'] / max_score * 100 - d['deducted_norm'], 1)
                d['weight_norm'] = round(d['weight'] / max_score * 100, 1)
    else:
        normalized_score = 0
    health['score'] = normalized_score
    health['max_score'] = 100

    if normalized_score >= 90:
        health['overall'] = 'ok'
    elif normalized_score >= 60:
        health['overall'] = 'warn'
    else:
        health['overall'] = 'error'

    health['anomalies'] = anomalies
    health['deductions'] = deductions
    return JsonResponse({'status': True, 'health': health})


def _format_bytes(size):
    """将字节数转换为人类可读的格式。"""
    if size >= 1024 * 1024 * 1024:
        return f'{size / (1024**3):.1f} GB'
    elif size >= 1024 * 1024:
        return f'{size / (1024**2):.1f} MB'
    elif size >= 1024:
        return f'{size / 1024:.1f} KB'
    return f'{size} B'


def import_module_version(name):
    """获取 Python 模块的版本号。"""
    try:
        mod = __import__(name)
        v = getattr(mod, 'VERSION', getattr(mod, '__version__', '-'))
        if isinstance(v, tuple):
            return '.'.join(str(x) for x in v[:3])
        return v
    except Exception:
        return '-'


# 基础设施配置（存储+数据库合并页）
@login_required
@superuser_only
def admin_storage(request):
    """基础设施配置管理页面 —— 存储后端配置 + 数据库连接信息"""
    import configparser
    from backend.apps.doc.storage.config import CONFIG_PATH as _cfg_path
    parser = configparser.ConfigParser()
    parser.read(_cfg_path, encoding='utf-8')
    backend_name = parser.get('storage', 'backend', fallback='local')

    # 公共配置
    public_base_url = parser.get('storage', 'public_base_url', fallback=None)

    # 各后端标签名
    BACKEND_LABELS = {
        'local': '本地存储',
        's3': 'AWS S3 / MinIO / R2',
        'oss': '阿里云 OSS',
        'cos': '腾讯云 COS',
        'kodo': '七牛云 Kodo',
    }

    def _mask(val):
        if not val:
            return '-'
        s = str(val)
        if len(s) <= 4:
            return s[0] + '***'
        return s[:2] + '***' + s[-2:]

    def _read_section(section):
        if section not in parser:
            return {}
        return dict(parser.items(section))

    backend_config = _read_section(f'storage.{backend_name}') if backend_name != 'local' else {}
    rules = _read_section('storage.rules')

    upload_max = {
        'FILE_UPLOAD_MAX_MEMORY_SIZE': getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', None),
        'DATA_UPLOAD_MAX_MEMORY_SIZE': getattr(settings, 'DATA_UPLOAD_MAX_MEMORY_SIZE', None),
    }

    storage_status = 'ok'
    storage_message = ''
    try:
        from backend.apps.doc.storage.config import get_storage
        get_storage()
    except Exception as e:
        storage_status = 'error'
        storage_message = str(e)[:200]

    local_path = ''
    if backend_name == 'local':
        local_path = os.path.join(settings.BASE_DIR, 'media')

    # ===== 数据库部分 =====
    db_config = {}
    if parser.has_section('database'):
        db_config = dict(parser.items('database'))

    engine = db_config.get('engine', 'unknown')
    ENGINE_LABELS = {
        'sqlite': 'SQLite',
        'mysql': 'MySQL',
        'postgresql': 'PostgreSQL',
        'oracle': 'Oracle',
    }

    from django.db import connection as dj_conn
    dj_vendor = dj_conn.vendor
    dj_db_name = dj_conn.settings_dict.get('NAME', '-')
    dj_db_host = dj_conn.settings_dict.get('HOST', '-') or '-'
    dj_db_port = dj_conn.settings_dict.get('PORT', '-') or '-'
    dj_db_user = dj_conn.settings_dict.get('USER', '-') or '-'

    db_status = 'ok'
    db_message = ''
    db_version = ''
    try:
        cursor = dj_conn.cursor()
        cursor.execute('SELECT 1')
        if dj_vendor == 'sqlite':
            import sqlite3
            db_version = sqlite3.sqlite_version
        elif dj_vendor == 'postgresql':
            cursor.execute('SELECT version()')
            db_version = cursor.fetchone()[0][:80]
        elif dj_vendor == 'mysql':
            cursor.execute('SELECT VERSION()')
            db_version = cursor.fetchone()[0]
    except Exception as e:
        db_status = 'error'
        db_message = str(e)[:200]

    return render(request, 'app_admin/admin_storage.html', {
        'backend_name': backend_name,
        'backend_label': BACKEND_LABELS.get(backend_name, backend_name),
        'backend_config': backend_config,
        'public_base_url': public_base_url,
        'rules': rules,
        'upload_max': upload_max,
        'storage_status': storage_status,
        'storage_message': storage_message,
        'local_path': local_path,
        'engine': engine,
        'engine_label': ENGINE_LABELS.get(engine, engine),
        'db_config': db_config,
        'dj_vendor': dj_vendor,
        'dj_db_name': dj_db_name,
        'dj_db_host': dj_db_host,
        'dj_db_port': dj_db_port,
        'dj_db_user': dj_db_user,
        'db_status': db_status,
        'db_message': db_message,
        'db_version': db_version,
    })


# 基础设施配置读写 API
@csrf_exempt
@login_required
@superuser_only
def api_admin_infra_config(request):
    """GET: 读取存储和数据库配置；POST: 保存配置到 config.ini"""
    import configparser
    from backend.apps.doc.storage.config import CONFIG_PATH as _cfg_path

    parser = configparser.ConfigParser()
    parser.read(_cfg_path, encoding='utf-8')

    # 确保 section 存在
    for sec in ['storage', 'database']:
        if sec not in parser:
            parser.add_section(sec)

    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            _apply_infra_config(parser, data)
            with open(_cfg_path, 'w', encoding='utf-8') as f:
                parser.write(f)
            return JsonResponse({'status': True, 'message': '配置已保存，需重启服务生效'})
        except Exception as e:
            return JsonResponse({'status': False, 'message': str(e)}, status=400)

    # GET: 返回当前配置
    storage = dict(parser.items('storage')) if parser.has_section('storage') else {}
    database = dict(parser.items('database')) if parser.has_section('database') else {}

    # 读取各后端配置
    backends = {}
    for bname in ['local', 's3', 'oss', 'cos', 'kodo']:
        sec = f'storage.{bname}'
        backends[bname] = dict(parser.items(sec)) if parser.has_section(sec) else {}

    return JsonResponse({
        'storage': {
            'backend': storage.get('backend', 'local'),
            'public_base_url': storage.get('public_base_url', ''),
            'backends': backends,
        },
        'database': {
            'engine': database.get('engine', 'sqlite'),
            'name': database.get('name', ''),
            'host': database.get('host', ''),
            'port': database.get('port', ''),
            'user': database.get('user', ''),
            'password': database.get('password', ''),
        },
    })


def _apply_infra_config(parser, data):
    """将前端提交的配置数据写入 parser"""
    # 存储配置
    if 'storage' in data:
        s = data['storage']
        if 'backend' in s:
            parser.set('storage', 'backend', s['backend'])
        if 'public_base_url' in s:
            if s['public_base_url'].strip():
                parser.set('storage', 'public_base_url', s['public_base_url'].strip())
            elif parser.has_option('storage', 'public_base_url'):
                parser.remove_option('storage', 'public_base_url')

        if 'backends' in s:
            for bname, bcfg in s['backends'].items():
                sec = f'storage.{bname}'
                if bcfg:
                    if sec not in parser:
                        parser.add_section(sec)
                    for k, v in bcfg.items():
                        if v.strip():
                            parser.set(sec, k, v.strip())
                        elif parser.has_option(sec, k):
                            parser.remove_option(sec, k)

    # 数据库配置
    if 'database' in data:
        d = data['database']
        for key in ['engine', 'name', 'host', 'port', 'user', 'password']:
            if key in d:
                val = d[key]
                if val.strip():
                    parser.set('database', key, val.strip())
                elif parser.has_option('database', key):
                    parser.remove_option('database', key)


# WebHook 管理页面
@login_required
@superuser_only
def admin_webhook(request):
    """WebHook 配置与投递日志管理页面。"""
    return render(request, 'app_admin/admin_webhook.html', locals())


# 系统日志查看器
@login_required
@superuser_only
def admin_syslog(request):
    """系统日志查看页面。"""
    import glob as _glob
    import re as _re
    LOG_DIR = os.path.join(settings.BASE_DIR, 'log')
    available_dates = []
    if os.path.isdir(LOG_DIR):
        for f in sorted(_glob.glob(os.path.join(LOG_DIR, '*.log')), reverse=True):
            basename = os.path.basename(f)
            # 匹配 Loguru 格式: error.YYYY-MM-DD.log 或 YYYY-MM-DD.log
            m = _re.match(r'(?:error\.)?(\d{4}-\d{2}-\d{2})\.log$', basename)
            if m:
                available_dates.append(m.group(1))
    return render(request, 'app_admin/admin_syslog.html', {'available_dates': available_dates})


@login_required
@superuser_only
def api_admin_syslog(request):
    """系统日志查询 API — 读取并解析 Loguru 日志文件。"""
    import glob as _glob
    import re as _re
    from urllib.parse import unquote

    LOG_DIR = os.path.join(settings.BASE_DIR, 'log')
    date_str = request.GET.get('date', '')  # YYYY-MM-DD，空=最新
    level_filter = request.GET.get('level', '').upper()  # ERROR|WARNING|INFO|DEBUG
    keyword = request.GET.get('kw', '').strip()
    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(int(request.GET.get('page_size', 50)), 200)

    # 收集所有 Loguru 格式的日志文件 (error.YYYY-MM-DD.log 或 YYYY-MM-DD.log)
    loguru_files = []
    if os.path.isdir(LOG_DIR):
        for f in _glob.glob(os.path.join(LOG_DIR, '*.log')):
            basename = os.path.basename(f)
            m = _re.match(r'(?:error\.)?(\d{4}-\d{2}-\d{2})\.log$', basename)
            if m:
                loguru_files.append((f, m.group(1)))
    # 按日期排序，最新在前
    loguru_files.sort(key=lambda x: x[1], reverse=True)

    log_file = None
    file_date = ''

    if date_str and len(date_str) == 10 and _re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        # 查找指定日期的文件（优先 error. 前缀，其次无前缀）
        for fpath, fdate in loguru_files:
            if fdate == date_str:
                log_file = fpath
                break
        if not log_file:
            # 兼容无前缀格式
            candidate = os.path.join(LOG_DIR, f'{date_str}.log')
            if os.path.isfile(candidate):
                log_file = candidate
            else:
                candidate2 = os.path.join(LOG_DIR, f'error.{date_str}.log')
                if os.path.isfile(candidate2):
                    log_file = candidate2

    if not log_file and loguru_files:
        log_file, file_date = loguru_files[0]
    elif not log_file:
        # 兜底：任意 .log 文件
        files = sorted(_glob.glob(os.path.join(LOG_DIR, '*.log')), reverse=True)
        for f in files:
            if os.path.isfile(f):
                log_file = f
                break

    if not log_file or not os.path.isfile(log_file):
        return JsonResponse({'entries': [], 'total': 0, 'page': 1, 'file_date': ''})

    if not file_date:
        # 从文件名提取日期
        basename = os.path.basename(log_file)
        m = _re.match(r'(?:error\.)?(\d{4}-\d{2}-\d{2})\.log$', basename)
        file_date = m.group(1) if m else basename.replace('.log', '')

    # 解析 Loguru 日志，格式: {time} | {level} | {module}:{function}:{line} — {message}
    # 实际格式: 2026-05-27 10:30:45.123 | INFO | module:function:123 — message text
    _log_re = _re.compile(
        r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s*\|\s*(\w+)\s*\|\s*([^|]+?)\s*[—\-]\s*(.*)$'
    )

    entries = []
    current_entry = None

    with open(log_file, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.rstrip('\n\r')
            m = _log_re.match(line)
            if m:
                if current_entry:
                    entries.append(current_entry)
                time_str = m.group(1)
                level = m.group(2).upper()
                module_func = m.group(3).strip()
                message = m.group(4).strip()

                # 解析 module:function:line
                mod = module_func
                func = ''
                lnum = ''
                parts = module_func.rsplit(':', 2)
                if len(parts) == 3:
                    mod, func, lnum = parts

                current_entry = {
                    'time': time_str,
                    'level': level,
                    'module': mod,
                    'function': func,
                    'line': lnum,
                    'message': message
                }
            elif current_entry:
                current_entry['message'] += '\n' + line

    if current_entry:
        entries.append(current_entry)

    # 反转（最新在前）
    entries.reverse()

    # 过滤
    if level_filter:
        LEVEL_ORDER = {'ERROR': 0, 'WARNING': 1, 'INFO': 2, 'DEBUG': 3, 'TRACE': 4}
        filter_idx = LEVEL_ORDER.get(level_filter, 9)
        entries = [e for e in entries if LEVEL_ORDER.get(e['level'], 9) <= filter_idx]

    if keyword:
        kw_lower = keyword.lower()
        entries = [e for e in entries if kw_lower in e['message'].lower() or kw_lower in e['module'].lower()]

    total = len(entries)
    start = (page - 1) * page_size
    paged = entries[start:start + page_size]

    # 从文件名提取日期显示
    basename = os.path.basename(log_file)
    _fm = _re.match(r'(?:error\.)?(\d{4}-\d{2}-\d{2})\.log$', basename)
    display_date = _fm.group(1) if _fm else basename.replace('.log', '')

    # 统计各级别数量
    level_counts = {'ERROR': 0, 'WARNING': 0, 'INFO': 0, 'DEBUG': 0, 'TRACE': 0}
    for e in entries:
        lv = e['level']
        if lv in level_counts:
            level_counts[lv] += 1

    return JsonResponse({
        'entries': paged,
        'total': total,
        'page': page,
        'page_size': page_size,
        'file_date': display_date,
        'level_counts': level_counts,
    })


# 数据库配置查看页面
@login_required
@superuser_only
def admin_database(request):
    """数据库配置查看页面 —— 展示当前数据库连接信息（敏感字段脱敏）。"""
    import configparser
    from backend.apps.doc.storage.config import CONFIG_PATH as _cfg_path
    parser = configparser.ConfigParser()
    parser.read(_cfg_path, encoding='utf-8')

    db_config = {}
    if parser.has_section('database'):
        db_config = dict(parser.items('database'))

    engine = db_config.get('engine', 'unknown')
    ENGINE_LABELS = {
        'sqlite': 'SQLite',
        'mysql': 'MySQL',
        'postgresql': 'PostgreSQL',
        'oracle': 'Oracle',
    }

    # Django 当前实际使用的数据库信息
    from django.db import connection as dj_conn
    dj_vendor = dj_conn.vendor
    dj_db_name = dj_conn.settings_dict.get('NAME', '-')
    dj_db_host = dj_conn.settings_dict.get('HOST', '-') or '-'
    dj_db_port = dj_conn.settings_dict.get('PORT', '-') or '-'
    dj_db_user = dj_conn.settings_dict.get('USER', '-') or '-'

    # 连接状态
    db_status = 'ok'
    db_message = ''
    db_version = ''
    try:
        cursor = dj_conn.cursor()
        cursor.execute('SELECT 1')
        # 获取版本号
        if dj_vendor == 'sqlite':
            import sqlite3
            db_version = sqlite3.sqlite_version
        elif dj_vendor == 'postgresql':
            cursor.execute('SELECT version()')
            db_version = cursor.fetchone()[0][:80]
        elif dj_vendor == 'mysql':
            cursor.execute('SELECT VERSION()')
            db_version = cursor.fetchone()[0]
    except Exception as e:
        db_status = 'error'
        db_message = str(e)[:200]

    return render(request, 'app_admin/admin_database.html', {
        'engine': engine,
        'engine_label': ENGINE_LABELS.get(engine, engine),
        'db_config': db_config,
        'dj_vendor': dj_vendor,
        'dj_db_name': dj_db_name,
        'dj_db_host': dj_db_host,
        'dj_db_port': dj_db_port,
        'dj_db_user': dj_db_user,
        'db_status': db_status,
        'db_message': db_message,
        'db_version': db_version,
    })


# ========== v2.0 认证配置管理页面 ==========

@login_required
@superuser_only
def admin_auth(request):
    """认证配置管理页面 —— 查看认证后端配置、OAuth 绑定记录、认证统计。"""
    return render(request, 'app_admin/admin_auth.html', locals())

_AUTH_SENSITIVE = frozenset({'client_secret', 'app_secret', 'corp_secret', 'bind_password'})
_AUTH_PROVIDERS = ['oidc', 'dingtalk', 'wecom', 'ldap']
_AUTH_PROVIDER_LABELS = {
    'oidc': 'OIDC',
    'dingtalk': '钉钉',
    'wecom': '企业微信',
    'ldap': 'LDAP',
}

def _mask_sensitive(value):
    """脱敏：保留前2后2字符，中间 * 替换。"""
    if not value:
        return '-'
    s = str(value)
    if len(s) <= 4:
        return s[:1] + '***'
    return s[:2] + '***' + s[-2:]


@login_required
@superuser_only
def api_admin_auth_configs(request):
    """GET/POST /admin/api/auth/configs/ — 读取/保存各认证后端配置，敏感字段脱敏。"""
    import configparser
    from backend.apps.doc.storage.config import CONFIG_PATH as _cfg_path
    parser = configparser.ConfigParser()
    parser.read(_cfg_path, encoding='utf-8')

    if request.method == 'POST':
        import json as _json
        try:
            data = _json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'status': False, 'message': '无效的请求数据'})
        provider = data.get('provider', '').strip()
        if provider not in _AUTH_PROVIDERS:
            return JsonResponse({'status': False, 'message': f'未知的认证后端: {provider}'})
        config = data.get('config', {})
        section = f'auth.{provider}'

        # 合并模式：如果仅发送 enabled，保留已有其他配置
        is_toggle_only = list(config.keys()) == ['enabled']
        if is_toggle_only and parser.has_section(section):
            parser.set(section, 'enabled', str(config['enabled']).strip())
        else:
            # 完整保存模式
            if parser.has_section(section):
                parser.remove_section(section)
            if config and any(str(v).strip() for v in config.values() if v is not None):
                parser.add_section(section)
                for k, v in config.items():
                    if v is not None and str(v).strip():
                        parser.set(section, k, str(v).strip())
        with open(_cfg_path, 'w', encoding='utf-8') as fh:
            parser.write(fh)
        # 记录敏感字段变更（脱敏）
        log_fields = {k: ('***' if k in _AUTH_SENSITIVE else str(v).strip()) for k, v in config.items()}
        logger.info(f'[认证配置] 用户={request.user.username} 修改 {provider} 配置: {log_fields}')
        return JsonResponse({'status': True, 'message': '保存成功，部分配置需重启服务后生效'})

    configs = {}
    for provider in _AUTH_PROVIDERS:
        section = f'auth.{provider}'
        if parser.has_section(section):
            raw = dict(parser.items(section))
            enabled = parser.getboolean(section, 'enabled', fallback=True)
            items = {}
            for k, v in raw.items():
                if k == 'enabled':
                    continue  # enabled 不作为配置项展示
                if k in _AUTH_SENSITIVE:
                    items[k] = _mask_sensitive(v)
                else:
                    items[k] = v
            configs[provider] = {
                'enabled': enabled,
                'label': _AUTH_PROVIDER_LABELS.get(provider, provider),
                'config': items,
            }
        else:
            configs[provider] = {
                'enabled': False,
                'label': _AUTH_PROVIDER_LABELS.get(provider, provider),
                'config': {},
            }
    return JsonResponse({'status': True, 'configs': configs})


@login_required
@superuser_only
@csrf_exempt
def api_admin_auth_test(request, provider):
    """POST /admin/api/auth/test/<provider>/ — 测试认证后端连接是否可用。"""
    if provider not in _AUTH_PROVIDERS:
        return JsonResponse({'status': False, 'message': f'未知的认证后端: {provider}'})

    if provider == 'oidc':
        try:
            from backend.apps.doc.auth.config import build_auth_backend
            backend = build_auth_backend('oidc')
            discovery_url = getattr(backend, 'discovery_url', None)
            if not discovery_url:
                return JsonResponse({'status': False, 'message': '未配置 discovery_url'})
            resp = requests.get(discovery_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return JsonResponse({
                    'status': True,
                    'message': f'连接成功',
                    'detail': {
                        'issuer': data.get('issuer', '-'),
                        'authorization_endpoint': data.get('authorization_endpoint', '-'),
                        'token_endpoint': data.get('token_endpoint', '-'),
                    }
                })
            return JsonResponse({'status': False, 'message': f'Discovery 端点返回 {resp.status_code}'})
        except Exception as e:
            logger.exception('OIDC 连接测试失败')
            return JsonResponse({'status': False, 'message': str(e)[:200]})

    if provider == 'ldap':
        try:
            from backend.apps.doc.auth.config import build_auth_backend
            backend = build_auth_backend('ldap')
            import ldap as _ldap
            conn = _ldap.initialize(getattr(backend, 'server_uri', 'ldap://localhost:389'))
            conn.set_option(_ldap.OPT_NETWORK_TIMEOUT, 5)
            if getattr(backend, 'use_tls', False):
                conn.start_tls_s()
            bind_dn = getattr(backend, 'bind_dn', None)
            bind_pw = getattr(backend, 'bind_password', None)
            if bind_dn:
                conn.simple_bind_s(bind_dn, bind_pw or '')
            conn.unbind_s()
            return JsonResponse({'status': True, 'message': 'LDAP 连接成功'})
        except Exception as e:
            logger.exception('LDAP 连接测试失败')
            return JsonResponse({'status': False, 'message': str(e)[:200]})

    if provider in ('dingtalk', 'wecom'):
        return JsonResponse({'status': True, 'message': '钉钉/企业微信认证通过 OAuth 登录回调验证，无需额外测试'})


@login_required
@superuser_only
def api_admin_auth_bindings(request):
    """GET /admin/api/auth/bindings/ — 查询 OAuth 绑定记录（分页）。"""
    from backend.apps.doc.models_v2 import IspOAuthBinding
    q_provider = request.GET.get('provider', '').strip()
    q_user = request.GET.get('user', '').strip()
    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(int(request.GET.get('page_size', 20)), 100)

    bindings = IspOAuthBinding.objects.select_related('user').all().order_by('-bound_at')
    if q_provider:
        bindings = bindings.filter(provider=q_provider)
    if q_user:
        bindings = bindings.filter(
            Q(user__username__icontains=q_user) | Q(provider_user_name__icontains=q_user)
        )

    total = bindings.count()
    bindings = bindings[(page - 1) * page_size:page * page_size]
    result = [{
        'id': str(b.id),
        'username': b.user.username,
        'display_name': b.user.first_name or b.user.username,
        'provider': b.provider,
        'provider_label': _AUTH_PROVIDER_LABELS.get(b.provider, b.provider),
        'provider_user_id': _mask_sensitive(b.provider_user_id),
        'provider_user_name': b.provider_user_name or '-',
        'bound_at': b.bound_at.strftime('%Y-%m-%d %H:%M') if b.bound_at else '-',
    } for b in bindings]

    # 各 provider 绑定统计
    stats = {}
    for p in _AUTH_PROVIDERS:
        stats[p] = IspOAuthBinding.objects.filter(provider=p).count()

    return JsonResponse({'status': True, 'bindings': result, 'total': total, 'stats': stats})


@login_required
@superuser_only
@csrf_exempt
def api_admin_auth_unbind(request, bid):
    """DELETE /admin/api/auth/bindings/<id>/ — 解除 OAuth 绑定。"""
    from backend.apps.doc.models_v2 import IspOAuthBinding
    if request.method != 'DELETE':
        return JsonResponse({'status': False, 'message': '仅支持 DELETE'}, status=405)
    try:
        binding = IspOAuthBinding.objects.get(pk=bid)
        username = binding.user.username
        provider = binding.provider
        binding.delete()
        return JsonResponse({'status': True, 'message': f'已解除 {username} 的 {provider} 绑定'})
    except IspOAuthBinding.DoesNotExist:
        return JsonResponse({'status': False, 'message': '绑定记录不存在'}, status=404)


# ========== v2.0 通知渠道管理页面 ==========

@login_required
@superuser_only
def admin_notification_channels(request):
    """通知渠道配置管理页面。"""
    return render(request, 'app_admin/admin_notification_channels.html', locals())


@login_required
@superuser_only
def api_admin_notification_channels(request):
    """GET /admin/api/notification/channels/ — 返回所有通道的状态和配置摘要。"""
    from backend.apps.doc.notification_channels import NOTIFICATION_CHANNEL_ROUTES

    channels_data = [
        {
            'id': 'in_app',
            'name': '站内通知',
            'description': '通过站内通知中心推送，始终启用',
            'enabled': True,
            'configurable': False,
            'summary': {'状态': '已启用'},
        },
        {
            'id': 'email',
            'name': '邮件通知',
            'description': '通过 SMTP 邮件发送通知，支持每日汇总',
            'enabled': _check_channel_config('email'),
            'configurable': True,
            'summary': _get_email_channel_summary(),
        },
        {
            'id': 'wecom',
            'name': '企业微信',
            'description': '通过企业微信自建应用发送通知消息',
            'enabled': _check_channel_config('wecom'),
            'configurable': True,
            'summary': _get_wecom_channel_summary(),
        },
        {
            'id': 'dingtalk',
            'name': '钉钉',
            'description': '通过钉钉工作通知推送（开发中，暂不可用）',
            'enabled': _check_channel_config('dingtalk'),
            'configurable': True,
            'summary': _get_stub_channel_summary('dingtalk'),
        },
        {
            'id': 'oa',
            'name': '企业OA',
            'description': '通过企业 OA 系统推送通知（开发中，暂不可用）',
            'enabled': _check_channel_config('oa'),
            'configurable': True,
            'summary': _get_stub_channel_summary('oa'),
        },
        {
            'id': 'webhook',
            'name': 'Webhook',
            'description': '通过自定义 Webhook URL 推送通知（开发中，暂不可用）',
            'enabled': _check_channel_config('webhook'),
            'configurable': True,
            'summary': _get_stub_channel_summary('webhook'),
        },
    ]

    routes = []
    for notify_type, channel_ids in NOTIFICATION_CHANNEL_ROUTES.items():
        TYPE_LABELS = {
            'system': '系统通知',
            'comment': '评论',
            'reply': '回复',
            'mention': '@提及',
            'doc_change': '文档变更',
            'doc_like': '点赞',
            'perm_apply': '权限申请',
            'perm_change': '权限变更',
        }
        routes.append({
            'type': notify_type,
            'label': TYPE_LABELS.get(notify_type, notify_type),
            'channels': channel_ids,
            'channel_names': [_CHANNEL_NAMES.get(c, c) for c in channel_ids],
        })

    return JsonResponse({'status': True, 'channels': channels_data, 'routes': routes})


_CHANNEL_NAMES = {
    'in_app': '站内通知', 'email': '邮件通知', 'wecom': '企业微信',
    'dingtalk': '钉钉', 'oa': '企业OA', 'webhook': 'Webhook',
}


def _get_email_channel_summary():
    """获取邮件通道的配置摘要。"""
    try:
        from backend.apps.doc.email_service import EmailService
        enabled = EmailService.is_enabled()
        config = EmailService._get_config()
        return {
            'SMTP 状态': '已配置' if enabled else '未配置',
            'SMTP 服务器': config.get('smtp_host', '-') if enabled else '-',
            '发件人': config.get('username', '-') if enabled else '-',
        }
    except Exception:
        return {'SMTP 状态': '检查失败'}


def _check_channel_config(channel_id):
    """检查预留通道是否有配置。"""
    try:
        from backend.apps.admin.models import SysConfig
        enabled = SysConfig.objects.get(key=f'channel.{channel_id}.enabled')
        return enabled.value.lower() == 'true'
    except Exception:
        return False


def _get_wecom_channel_summary():
    """获取企业微信通道的配置摘要。"""
    try:
        import configparser
        from backend.apps.doc.storage.config import _read_config
        parser = _read_config()
        if parser.has_section('auth.wecom'):
            corp_id = parser.get('auth.wecom', 'corp_id', fallback='')
            agent_id = parser.get('auth.wecom', 'agent_id', fallback='')
            if corp_id:
                return {
                    '企业ID': corp_id[:8] + '***' if len(corp_id) > 8 else corp_id,
                    '应用AgentId': agent_id or '未设置',
                    '状态': '已配置，可发送' if _check_channel_config('wecom') else '未启用',
                }
        return {'状态': '未配置企业微信参数'}
    except Exception:
        return {'状态': '检查失败'}


def _get_stub_channel_summary(channel_id):
    """获取预留通道的配置摘要。"""
    if _check_channel_config(channel_id):
        return {'状态': '已启用（开发中，暂不可用）'}
    return {'状态': '未启用'}


@login_required
@superuser_only
@csrf_exempt
def api_admin_notification_channel_action(request, channel_id):
    """PUT /admin/api/notification/channels/<id>/ — 更新通道启用状态。
    POST /admin/api/notification/channels/<id>/test/ — 测试通道连接。
    """
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            enabled = data.get('enabled', False)
            from backend.apps.admin.models import SysConfig
            SysConfig.objects.update_or_create(
                key=f'channel.{channel_id}.enabled',
                defaults={'value': str(enabled).lower()}
            )
            logger.info(f'[通知渠道] 用户={request.user.username} 切换通道 {channel_id} enabled={enabled}')
            return JsonResponse({'status': True, 'message': f'已{"启用" if enabled else "禁用"}通道'})
        except Exception as e:
            logger.exception(f'[通知渠道] 切换通道失败: channel_id={channel_id}')
            return JsonResponse({'status': False, 'message': str(e)})

    if request.method == 'POST':
        if channel_id == 'email':
            try:
                from backend.apps.doc.email_service import EmailService
                if not EmailService.is_enabled():
                    return JsonResponse({'status': False, 'message': 'SMTP 邮件未配置'})
                user_email = request.user.email
                if not user_email:
                    return JsonResponse({'status': False, 'message': '当前管理员未设置邮箱'})
                EmailService.send_email(
                    to_email=user_email,
                    subject='[i·Space Doc] 邮件通道测试',
                    html_body='<p>这是一封来自通知渠道配置页面的测试邮件。</p><p>如果您收到此邮件，说明邮件通知通道配置正确。</p>'
                )
                return JsonResponse({'status': True, 'message': f'测试邮件已发送至 {user_email}'})
            except Exception as e:
                logger.exception('邮件测试发送失败')
                return JsonResponse({'status': False, 'message': str(e)[:200]})

        if channel_id == 'webhook':
            from backend.apps.admin.models import SysConfig
            try:
                url_config = SysConfig.objects.get(key='channel.webhook.url')
                url = url_config.value
                if not url:
                    return JsonResponse({'status': False, 'message': 'Webhook URL 未配置'})
            except SysConfig.DoesNotExist:
                return JsonResponse({'status': False, 'message': 'Webhook URL 未配置'})
            try:
                resp = requests.post(url, json={
                    'event': 'test',
                    'source': 'i·Space Doc Notification Channel Test',
                    'message': '通知渠道测试消息',
                }, timeout=10)
                return JsonResponse({
                    'status': resp.status_code < 400,
                    'message': f'HTTP {resp.status_code}' + (' 发送成功' if resp.status_code < 400 else ' 请求失败'),
                })
            except Exception as e:
                return JsonResponse({'status': False, 'message': str(e)[:200]})

        return JsonResponse({'status': False, 'message': '该通道暂无测试功能'})


@login_required
@superuser_only
def api_admin_notification_routes(request):
    """GET /admin/api/notification/routes/ — 返回通知类型→通道的路由映射。"""
    from backend.apps.doc.notification_channels import NOTIFICATION_CHANNEL_ROUTES
    TYPE_LABELS = {
        'system': '系统通知', 'comment': '评论', 'reply': '回复',
        'mention': '@提及', 'doc_change': '文档变更', 'doc_like': '点赞',
        'perm_apply': '权限申请', 'perm_change': '权限变更',
    }
    routes = []
    for notify_type, channel_ids in NOTIFICATION_CHANNEL_ROUTES.items():
        routes.append({
            'type': notify_type,
            'label': TYPE_LABELS.get(notify_type, notify_type),
            'channels': channel_ids,
            'channel_names': [_CHANNEL_NAMES.get(c, c) for c in channel_ids],
        })
    return JsonResponse({'status': True, 'routes': routes})
