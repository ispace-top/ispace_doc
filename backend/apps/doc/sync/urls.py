"""目录同步 API URL 路由。"""
from django.urls import path

from . import views

urlpatterns = [
    path("wecom/trigger/", views.wecom_sync_trigger, name="sync_wecom_trigger"),
    path("ldap/trigger/", views.ldap_sync_trigger, name="sync_ldap_trigger"),
    path("<str:provider>/status/", views.sync_status, name="sync_status"),
]
