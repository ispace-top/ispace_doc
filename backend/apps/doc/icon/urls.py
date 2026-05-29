"""图标 API URL 路由（7.1.1 / 7.1.2）。"""
from django.urls import path

from . import views

urlpatterns = [
    path("search/", views.icon_search, name="icon_search"),
    path("categories/", views.icon_categories, name="icon_categories"),
    path("upload/", views.custom_icon_upload, name="icon_upload"),
    path("custom/<str:icon_id>/", views.custom_icon_delete, name="icon_delete"),
]
