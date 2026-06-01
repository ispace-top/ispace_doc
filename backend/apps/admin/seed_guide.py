# coding:utf-8
"""系统初始化时内置用户指南文档。

从 docs/user-guide/ 目录读取 Markdown 文件创建文档树。
"""
import os


def _load_guide(name):
    """读取 docs/user-guide/ 下的 .md 文件内容。"""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), 'docs', 'user-guide', name)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''


def create_builtin_guide(user):
    """在 setup 安装完成后调用，创建内置用户指南文档树。

    以传入的超级管理员为作者，创建一套展示 iSpaceDoc 各项功能
    与特色组件的入门指导文档。
    """
    from backend.apps.doc.models import Doc, DocPermission

    def _mkdoc(name, filename, parent_doc=0, sort=1):
        pre_content = _load_guide(filename)
        if not pre_content:
            return None
        doc = Doc.objects.create(
            name=name,
            pre_content=pre_content,
            content='',
            parent_doc=parent_doc,
            top_doc=0,
            sort=sort,
            create_user=user,
            status=1,
            editor_mode=2,
        )
        DocPermission.objects.create(
            doc=doc, target_type='user', target_id=user.id,
            permission='admin', granted_by=user,
        )
        return doc

    # Root
    guide = _mkdoc('📖 爱思文档用户指南', '01-root.md', sort=1)

    # Level 1 children (under root)
    _mkdoc('🖥️ 系统安装配置', '02-install.md', parent_doc=guide.id, sort=1)
    _mkdoc('⚙️ 管理员后台设置管理', '03-admin.md', parent_doc=guide.id, sort=2)

    # Editor guide (under root)
    editor = _mkdoc('📝 文档编辑指南', '04-editor-overview.md', parent_doc=guide.id, sort=3)

    # Level 2 children (under editor guide)
    if editor:
        _mkdoc('📝 Markdown 基础与 Callout', '05-markdown-callout.md', parent_doc=editor.id, sort=1)
        _mkdoc('📊 ECharts 图表详解', '06-echarts.md', parent_doc=editor.id, sort=2)
        _mkdoc('🗺️ 思维导图与流程图', '07-mindmap-flowchart.md', parent_doc=editor.id, sort=3)
        _mkdoc('⏱️ 时序图详解', '08-sequence.md', parent_doc=editor.id, sort=4)
        _mkdoc('📐 Mermaid、PlantUML 与 Graphviz', '09-mermaid-etc.md', parent_doc=editor.id, sort=5)
        _mkdoc('🔢 数学公式与五线谱', '12-math-abc.md', parent_doc=editor.id, sort=6)
        _mkdoc('💬 协作功能详解', '11-collaboration.md', parent_doc=editor.id, sort=7)

    return guide


def seed_guide(user):
    """对外的快捷入口，效果同 `create_builtin_guide`。"""
    return create_builtin_guide(user)
