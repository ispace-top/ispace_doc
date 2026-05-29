"""搜索 API URL 路由（2.1.6 / 2.1.7 / 2.1.8）。"""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.search_api, name="api_search"),
    path("suggest/", views.suggest_api, name="api_search_suggest"),
    path("stats/", views.search_stats, name="api_search_stats"),
    path("related/<int:doc_id>/", views.related_docs_api, name="api_search_related"),
]
