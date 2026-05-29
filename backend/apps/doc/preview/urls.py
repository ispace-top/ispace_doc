"""附件预览 API URL 路由（4.2.2 / 4.2.3 / 4.3.2）。"""
from django.urls import path

from . import views

urlpatterns = [
    path("pdf/<int:attachment_id>/", views.preview_pdf, name="preview_pdf"),
    path("docx/<int:attachment_id>/", views.preview_docx, name="preview_docx"),
    path("xlsx/<int:attachment_id>/", views.preview_xlsx, name="preview_xlsx"),
    path("pptx/<int:attachment_id>/", views.preview_pptx, name="preview_pptx"),
    path("zip/<int:attachment_id>/", views.preview_zip, name="preview_zip"),
    path("text/<int:attachment_id>/", views.preview_text, name="preview_text"),
    path("video/<int:attachment_id>/", views.stream_video, name="stream_video"),
    path("info/<int:attachment_id>/", views.file_info, name="file_info"),
]
