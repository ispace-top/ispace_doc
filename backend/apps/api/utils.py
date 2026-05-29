from backend.apps.doc.models import Doc
from django.utils.html import strip_tags
import markdown

# 摘取文档部分正文
def remove_doc_tag(doc):
    try:
        if doc.editor_mode == 1:
            result = "此为表格文档，进入文档查看详细内容"
        else: # 其他文档
            result = strip_tags(markdown.markdown(doc.pre_content))[:100]
    except Exception as e:
        result = doc.pre_content[:100]
    result = result.replace("&nbsp;",'')
    return result
