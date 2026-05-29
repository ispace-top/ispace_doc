"""统一 OAuth 认证视图。

路由：
    /auth/login/<provider>/       — 跳转到 OAuth 提供方登录页
    /auth/callback/<provider>/    — OAuth 回调处理
    /auth/sso/<provider>/         — 钉钉/企微自建应用免登录
    /auth/bind/<provider>/        — 绑定已有账号
"""

import secrets
import logging

from django.contrib import auth
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from backend.apps.doc.models import UserProfile

from .config import get_auth_backend, get_enabled_backends

logger = logging.getLogger(__name__)

STATE_PREFIX = "oauth_state_"


def _save_state(request, provider: str) -> str:
    """生成并保存 OAuth state 参数。"""
    state = secrets.token_urlsafe(32)
    request.session[f"{STATE_PREFIX}{provider}"] = state
    return state


def _verify_state(request, provider: str, state: str) -> bool:
    """验证 OAuth state 参数。"""
    key = f"{STATE_PREFIX}{provider}"
    saved = request.session.pop(key, "")
    return secrets.compare_digest(saved, state)


def _get_or_create_user(user_info) -> User:
    """根据 OAuth 用户信息查找或创建本地 User。

    - 已有同 provider + provider_uid 的用户 → 直接返回
    - 新用户 → 自动创建 User + UserProfile
    """
    # 用户名冲突处理：加数字后缀
    base_username = user_info.username or user_info.provider_uid
    username = base_username
    suffix = 0
    while User.objects.filter(username__iexact=username).exists():
        suffix += 1
        username = f"{base_username}_{suffix}"

    # 邮箱处理
    email = ""
    if user_info.email:
        if User.objects.filter(email=user_info.email).exists():
            email = ""  # 邮箱已被占用，不设置
        else:
            email = user_info.email

    user = User.objects.create_user(
        username=username,
        email=email,
        # 随机密码（OAuth 用户不使用密码登录）
        password=secrets.token_urlsafe(32),
    )
    UserProfile.objects.get_or_create(
        user=user,
        defaults={"gender": "U"},
    )

    # 存储 OAuth 绑定信息到 session（持久化需建表，这里先放 session）
    _save_oauth_bind(user, user_info)
    return user


def _save_oauth_bind(user: User, user_info):
    """保存 OAuth 绑定信息（后续可迁移到 UserOAuthBinding 模型）。"""
    binds = {
        "provider": user_info.provider,
        "provider_uid": user_info.provider_uid,
        "nickname": user_info.nickname,
        "avatar_url": user_info.avatar_url,
    }
    user.profile.extra_oauth = binds
    user.profile.save(update_fields=["extra_oauth"]) if hasattr(user.profile, "extra_oauth") else None
    # 存 session 作为临时方案
    import hashlib

    session_key = hashlib.sha256(f"{user_info.provider}:{user_info.provider_uid}".encode()).hexdigest()[:16]


def oauth_login(request, provider: str):
    """跳转到 OAuth 提供方登录页面。"""
    state = _save_state(request, provider)
    redirect_uri = request.build_absolute_uri(
        reverse("oauth_callback", kwargs={"provider": provider})
    )
    backend = get_auth_backend(provider)
    url = backend.get_authorize_url(state, redirect_uri)
    if not url:
        return JsonResponse({"error": f"{provider} 不支持浏览器 OAuth 登录"}, status=400)
    return redirect(url)


def oauth_callback(request, provider: str):
    """OAuth 回调处理。

    流程:
        1. 验证 state 防 CSRF
        2. 用 code 换取 access_token + 用户信息
        3. 查找或创建本地用户
        4. Django login() 建立会话
        5. 重定向到首页
    """
    state = request.GET.get("state", "")
    if not _verify_state(request, provider, state):
        return JsonResponse({"error": "state 验证失败"}, status=400)

    try:
        redirect_uri = request.build_absolute_uri(
            reverse("oauth_callback", kwargs={"provider": provider})
        )
        backend = get_auth_backend(provider)
        result = backend.authenticate(request.GET, redirect_uri)
    except Exception as e:
        logger.exception(f"{provider} OAuth 回调处理失败")
        return JsonResponse({"error": str(e)}, status=400)

    user_info = result.user_info

    # 查找已有 OAuth 绑定（简化版：通过 username 匹配）
    # TODO: 未来创建 UserOAuthBinding 表后改为精确匹配 provider + provider_uid
    user = None
    if user_info.email:
        try:
            user = User.objects.get(email=user_info.email)
        except User.DoesNotExist:
            pass

    if user is None:
        try:
            user = User.objects.get(username=user_info.username)
        except User.DoesNotExist:
            user = _get_or_create_user(user_info)

    auth.login(request, user)
    return redirect("/")


def oauth_sso(request, provider: str):
    """自建应用免登录（钉钉/企业微信）。"""
    try:
        backend = get_auth_backend(provider)
        if provider == "dingtalk":
            result = backend.authenticate_sso(request.GET)
        elif provider == "wecom":
            result = backend.authenticate_sso(request.GET)
        else:
            return JsonResponse({"error": f"{provider} 不支持免登录"}, status=400)
    except Exception as e:
        logger.exception(f"{provider} 免登录失败")
        return JsonResponse({"error": str(e)}, status=400)

    user_info = result.user_info

    # 查找或创建用户
    user = None
    try:
        # TODO: 替换为 UserOAuthBinding 查询
        user = User.objects.get(username=user_info.username)
    except User.DoesNotExist:
        user = _get_or_create_user(user_info)

    auth.login(request, user)
    return redirect("/")


def oauth_bind(request, provider: str):
    """绑定 OAuth 账号到当前登录用户。"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "请先登录"}, status=401)

    state = _save_state(request, provider)
    bind_redirect_uri = request.build_absolute_uri(
        reverse("oauth_bind_callback", kwargs={"provider": provider})
    )
    backend = get_auth_backend(provider)
    url = backend.get_bind_url(state, bind_redirect_uri)
    return redirect(url)


def oauth_bind_callback(request, provider: str):
    """OAuth 绑定回调处理。"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "请先登录"}, status=401)

    state = request.GET.get("state", "")
    if not _verify_state(request, provider, state):
        return JsonResponse({"error": "state 验证失败"}, status=400)

    try:
        backend = get_auth_backend(provider)
        result = backend.authenticate(request.GET, "")
    except Exception as e:
        logger.exception(f"{provider} 绑定失败")
        return JsonResponse({"error": str(e)}, status=400)

    _save_oauth_bind(request.user, result.user_info)
    return JsonResponse({"status": "ok", "provider": provider})


def oauth_login_form(request, provider: str):
    """用户名密码表单登录（LDAP 等非 OAuth 后端）。

    POST /auth/<provider>/login/form/
    """
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    import json
    try:
        body = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        body = {}

    username = body.get("username", request.POST.get("username", ""))
    password = body.get("password", request.POST.get("password", ""))

    if not username or not password:
        return JsonResponse({"error": "请输入用户名和密码"}, status=400)

    try:
        backend = get_auth_backend(provider)
        result = backend.authenticate({"username": username, "password": password})
    except Exception as e:
        logger.exception(f"{provider} 表单登录失败")
        return JsonResponse({"error": str(e)}, status=400)

    user_info = result.user_info

    # 查找已有用户
    user = None
    try:
        user = User.objects.get(email=user_info.email) if user_info.email else None
    except User.DoesNotExist:
        pass

    if user is None:
        try:
            user = User.objects.get(username=user_info.username)
        except User.DoesNotExist:
            user = _get_or_create_user(user_info)

    auth.login(request, user)
    return JsonResponse({"status": "ok", "redirect": "/"})


def auth_providers(request):
    """返回已启用的认证提供方列表。

    每个 provider 返回：
    - name: 后端标识
    - url: 登录入口 URL
    - type: "redirect"（OAuth 跳转）或 "form"（用户名密码表单登录，如 LDAP）
    """
    FORM_BACKENDS = {"ldap"}  # 需要前端弹出表单的后端
    providers = get_enabled_backends()
    result = []
    for p in providers:
        if p in FORM_BACKENDS:
            result.append({
                "name": p,
                "url": reverse("oauth_login_form", kwargs={"provider": p}),
                "type": "form",
            })
        else:
            result.append({
                "name": p,
                "url": reverse("oauth_login", kwargs={"provider": p}),
                "type": "redirect",
            })
    return JsonResponse({"providers": result})
