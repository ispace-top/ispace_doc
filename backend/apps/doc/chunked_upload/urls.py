"""分片上传 API URL 路由。"""
from django.urls import path

from . import views

urlpatterns = [
    path("init/", views.chunked_upload_init, name="chunked_upload_init"),
    path("<str:upload_id>/", views.chunked_upload_chunk, name="chunked_upload_chunk"),
    path("<str:upload_id>/complete/", views.chunked_upload_complete, name="chunked_upload_complete"),
    path("<str:upload_id>/status/", views.chunked_upload_status, name="chunked_upload_status"),
    path("<str:upload_id>/abort/", views.chunked_upload_abort, name="chunked_upload_abort"),
]
