"""可视化绘图 JSON Schema 定义与验证。

支持三种绘图类型：
- mindmap: 思维导图（节点、连线、样式、主题）
- drawio:  Draw.io 流程图（mxGraph XML/JSON）
- excalidraw: Excalidraw 手绘风格图
"""

import json
import logging
from enum import StrEnum

logger = logging.getLogger(__name__)


class DrawingType(StrEnum):
    MINDMAP = "mindmap"
    DRAWIO = "drawio"
    EXCALIDRAW = "excalidraw"


# 思维导图 JSON Schema 文档（供前端参考，不做强制校验）
MINDMAP_SCHEMA_DOC = """
{
  "type": "mindmap",
  "version": "1.0",
  "root": {
    "id": "node-1",
    "text": "中心主题",
    "children": [
      {
        "id": "node-2",
        "text": "子主题",
        "direction": "right",
        "children": [],
        "style": {"fill": "#e8f5e9", "stroke": "#4caf50", "color": "#333"},
        "note": "",
        "image": "",
        "hyperlink": "",
        "collapsed": false
      }
    ],
    "style": {"fill": "#2196f3", "stroke": "#1565c0", "color": "#fff"},
    "note": ""
  },
  "theme": {
    "name": "default",
    "background": "#ffffff",
    "lineColor": "#bdbdbd",
    "lineWidth": 2,
    "fontFamily": "Microsoft YaHei"
  },
  "layout": "mindmap",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
"""

# Draw.io 数据格式说明（存储 mxGraph XML）
DRAWIO_SCHEMA_DOC = """
Draw.io 数据以 mxGraph XML 字符串存储，结构如下：

<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <mxCell id="2" value="开始" style="rounded=1;fillColor=#d5e8d4;strokeColor=#82b366;" vertex="1" parent="1">
      <mxGeometry x="120" y="80" width="120" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="3" value="处理" style="rounded=0;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
      <mxGeometry x="360" y="80" width="120" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="4" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" source="2" target="3">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>

API 存储时包装为:
{
  "type": "drawio",
  "version": "1.0",
  "xml": "<mxGraphModel>...</mxGraphModel>",
  "png_preview": "data:image/png;base64,...",
  "created_at": "...",
  "updated_at": "..."
}
"""

# Excalidraw 数据格式（由前端 Excalidraw 库定义，这里透传）
EXCALIDRAW_SCHEMA_DOC = """
Excalidraw 数据由前端库生成，包含:
{
  "type": "excalidraw",
  "version": 1,
  "source": "https://excalidraw.com",
  "elements": [...],
  "appState": {...},
  "files": {...},
  "created_at": "...",
  "updated_at": "..."
}
"""


def validate_data(data: dict, drawing_type: DrawingType) -> tuple[bool, str]:
    """基础数据校验。

    Returns:
        (valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "数据必须是 JSON 对象"

    actual_type = data.get("type", "")
    if actual_type and actual_type != drawing_type.value:
        return False, f"type 字段不匹配: 期望 {drawing_type.value}, 实际 {actual_type}"

    if drawing_type == DrawingType.MINDMAP:
        if "root" not in data:
            return False, "思维导图数据缺少 root 节点"
        root = data["root"]
        if not isinstance(root, dict):
            return False, "root 必须是对象"
        if "id" not in root or "text" not in root:
            return False, "root 节点缺少 id 或 text"

    elif drawing_type == DrawingType.DRAWIO:
        if "xml" not in data:
            return False, "Draw.io 数据缺少 xml 字段"

    elif drawing_type == DrawingType.EXCALIDRAW:
        if "elements" not in data:
            return False, "Excalidraw 数据缺少 elements 字段"

    return True, ""


def parse_content_json(raw: str | dict | None) -> dict:
    """安全解析 content_json 字段。"""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("content_json JSON 解析失败")
            return {}
    return {}
