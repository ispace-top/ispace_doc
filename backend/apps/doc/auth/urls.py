"""第三方认证 URL 路由。"""
from django.urls import path

from . import views

urlpatterns = [
    path("<str:provider>/login/form/", views.oauth_login_form, name="oauth_login_form"),
    path("<str:provider>/login/", views.oauth_login, name="oauth_login"),
    path("<str:provider>/callback/", views.oauth_callback, name="oauth_callback"),
    path("<str:provider>/sso/", views.oauth_sso, name="oauth_sso"),
    path("<str:provider>/bind/", views.oauth_bind, name="oauth_bind"),
    path("<str:provider>/bind/callback/", views.oauth_bind_callback, name="oauth_bind_callback"),
    path("providers/", views.auth_providers, name="auth_providers"),
]
