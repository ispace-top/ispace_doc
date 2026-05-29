"""WebHook 管理 API URL 路由。"""
from django.urls import path

from . import views

urlpatterns = [
    path("configs/", views.webhook_config_list, name="webhook_configs"),
    path("configs/create/", views.webhook_config_create, name="webhook_config_create"),
    path("configs/<int:config_id>/update/", views.webhook_config_update, name="webhook_config_update"),
    path("configs/<int:config_id>/delete/", views.webhook_config_delete, name="webhook_config_delete"),
    path("configs/<int:config_id>/test/", views.webhook_config_test, name="webhook_config_test"),
    path("deliveries/", views.webhook_deliveries, name="webhook_deliveries"),
    path("deliveries/<int:delivery_id>/", views.webhook_delivery_detail, name="webhook_delivery_detail"),
    path("event-types/", views.webhook_event_types, name="webhook_event_types"),
]
