"""
文档大纲解析工具 — 从文档内容中提取标题，生成大纲目录 JSON。

支持 Markdown 编辑器格式：
- Vditor (editor_mode=2)：Markdown 格式，正则匹配 # ~ ###### 行首标题
"""

import json
import re

# 匹配 Markdown ATX 标题：# 后跟至少一个空格，可选的关闭 # 序列
_RE_MD_HEADING = re.compile(r'^(#{1,6})\s+(.*?)(?:\s+#+\s*)?$', re.MULTILINE)


def parse_outline(doc_content, editor_mode):
    """
    从文档内容中提取标题，返回大纲目录 JSON 字符串。

    Args:
        doc_content: 文档内容（Markdown 格式的 pre_content）
        editor_mode: 编辑器模式 (2=Vditor/Markdown, 4=Luckysheet/表格)

    Returns:
        JSON 字符串：[{"id": "heading-0", "level": 2, "text": "1. 引言"}, ...]
        无标题时返回 None
    """
    if not doc_content or not doc_content.strip():
        return None

    if editor_mode == 4:
        return None

    headings = []

    # Vditor / Markdown 模式：匹配 # heading 行
    for m in _RE_MD_HEADING.finditer(doc_content):
        level = len(m.group(1))
        text = m.group(2).strip()
        if text:
            headings.append({'level': level, 'text': text})

    if not headings:
        return None

    outline = []
    for idx, h in enumerate(headings):
        outline.append({
            'id': 'heading-{}'.format(idx),
            'level': h['level'],
            'text': h['text'],
        })

    return json.dumps(outline, ensure_ascii=False)
