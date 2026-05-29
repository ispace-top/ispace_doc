"""可视化绘图 API URL 路由（6.2.1 / 6.2.2）。"""
from django.urls import path

from . import views

urlpatterns = [
    # 思维导图
    path("mindmap/<int:doc_id>/", views.get_mindmap, name="drawing_mindmap_get"),
    path("mindmap/<int:doc_id>/save/", views.save_mindmap, name="drawing_mindmap_save"),
    # Draw.io 流程图
    path("drawio/<int:doc_id>/", views.get_drawio, name="drawing_drawio_get"),
    path("drawio/<int:doc_id>/save/", views.save_drawio, name="drawing_drawio_save"),
    path("drawio/<int:doc_id>/export/", views.export_drawio, name="drawing_drawio_export"),
    # Excalidraw 手绘图
    path("excalidraw/<int:doc_id>/", views.get_excalidraw, name="drawing_excalidraw_get"),
    path("excalidraw/<int:doc_id>/save/", views.save_excalidraw, name="drawing_excalidraw_save"),
]
