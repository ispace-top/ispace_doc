# coding:utf-8
"""系统初始化时内置用户指南文档。"""


def create_builtin_guide(user):
    """在 setup 安装完成后调用，创建内置用户指南文档树。

    以传入的超级管理员为作者，创建一套展示 iSpaceDoc 各项功能
    与特色组件的入门指导文档。
    """
    from backend.apps.doc.models import Doc, DocPermission

    def _mkdoc(name, pre_content, parent_doc=0, sort=1):
        """创建一篇 Vditor Markdown 文档并授予作者 admin 权限。"""
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

    # ── 根文档：用户指南 ──────────────────────────────────
    guide = _mkdoc('📖 用户指南', _GUIDE_ROOT, sort=1)

    # ── 子文档 ────────────────────────────────────────────
    _mkdoc('🚀 快速入门', _QUICK_START, parent_doc=guide.id, sort=1)
    _mkdoc('✏️ 文档编辑与特色组件', _EDITOR_FEATURES, parent_doc=guide.id, sort=2)
    _mkdoc('📂 文档管理与协作', _MANAGEMENT, parent_doc=guide.id, sort=3)

    return guide


# ══════════════════════════════════════════════════════════════
# 以下为各文档的 Markdown 正文（使用系统自身组件演示特性）
# ══════════════════════════════════════════════════════════════

_GUIDE_ROOT = """# 欢迎使用 iSpaceDoc 🎉

感谢你选择 **iSpaceDoc** —— 一款企业级私有云文档与知识管理平台。

## 核心理念

> "一切皆文档" —— 用统一的文档模型承载知识组织、权限管理和团队协作。
> info 这是 Callout 提示块，支持 `info` / `warning` / `error` / `success` / `tip` 五种样式，在 Markdown IR 模式下输入 `> info` 即可触发。

## 你可以用它做什么

| 场景 | 说明 |
|------|------|
| 📝 个人云笔记 | Markdown IR 实时预览、全文搜索、标签管理 |
| 🏢 团队知识库 | 多级文档树、细粒度权限、划词评论、@提及 |
| 📖 产品手册 | 公开分享、SPA 无刷新导航、SEO 优化 |
| 🔒 合规文档 | 水印保护、审计日志、软删除恢复、访问密码 |

## 快速上手

点击左侧文档树中的 **"🚀 快速入门"** 了解基本操作，或查看 **"✏️ 文档编辑与特色组件"** 了解编辑器的各种高级功能。

---

> tip **提示**：本指南由系统初始化时自动生成，作者为超级管理员。你可以随时修改或删除这些文档。
"""

_QUICK_START = """# 快速入门

## 创建你的第一篇文档

1. 在左侧文档树中点击右键，选择 **"新建文档"**
2. 输入文档标题，选择上级目录（可选）
3. 点击确定，自动进入编辑器

## 编辑器切换

iSpaceDoc 提供三种编辑模式：

- **Markdown IR**（默认）：所见即所得的 Markdown 编辑器，支持实时预览
- **富文本编辑器**：类 Word 的排版体验
- **在线表格**：内嵌 Luckysheet 电子表格

在创建文档时可以选择编辑器类型，也可以在文档设置中切换。

## 文档树操作

- **拖拽排序**：直接拖动文档到目标位置即可调整层级和顺序
- **右键菜单**：提供新建、重命名、删除、权限设置等快捷操作
- **手风琴模式**：同级节点展开时自动折叠其他节点，保持侧栏清爽

## 搜索你的知识库

顶部搜索栏支持：

- 🔍 全文搜索，jieba 中文分词
- 📅 按时间范围筛选
- 🌲 限定在某棵子树内搜索

> success 恭喜！你已经掌握了 iSpaceDoc 的基本操作。继续阅读其他指南了解更多高级功能。
"""

_EDITOR_FEATURES = """# 文档编辑与特色组件

本文档集中展示 iSpaceDoc 的各种编辑器特色组件。

## Callout 提示块

在 Markdown IR 模式下，用 `> 类型` 开头的引用块会自动渲染为彩色提示：

> info **信息提示** — 蓝色，用于补充说明
> warning **警告提示** — 橙色，提醒注意事项
> error **错误提示** — 红色，标记重要警告
> success **成功提示** — 绿色，确认好消息
> tip **小贴士** — 紫色，分享小技巧

## 表格编辑

| 功能 | 支持情况 | 快捷键 |
|------|:---:|------|
| 行插入 | ✅ | 点击表格浮动工具栏 |
| 列插入 | ✅ | 点击表格浮动工具栏 |
| 行列删除 | ✅ | 浮动工具栏操作 |
| 对齐设置 | ✅ | 冒号语法 `:---:` |

## 数学公式

行内公式：$E = mc^2$

块级公式：

$$
\\int_{a}^{b} f(x)\\,dx = F(b) - F(a)
$$

## ECharts 图表

```echarts
{
  "title": { "text": "月度文档创建趋势" },
  "xAxis": { "type": "category", "data": ["1月","2月","3月","4月","5月","6月"] },
  "yAxis": { "type": "value" },
  "series": [{ "data": [12, 25, 38, 56, 72, 95], "type": "line", "smooth": true }]
}
```

## 思维导图

```mindmap
# 知识体系
## 编程语言
### Python
### JavaScript
### Go
## 数据库
### PostgreSQL
### Redis
## 前端框架
### React
### Vue
```

## 流程图

```flow
st=>start: 开始
op=>operation: 编写文档
cond=>condition: 需要协作？
pub=>operation: 发布分享
end=>end: 完成

st->op->cond
cond(yes)->pub->end
cond(no)->end
```

## 代码块语法高亮

```python
def greet(name: str) -> str:
    """向用户问好"""
    return f"你好，{name}！欢迎使用 iSpaceDoc。"

print(greet("世界"))
```

> tip 以上所有组件在 Markdown IR 编辑模式下即可直接编辑和预览。
"""

_MANAGEMENT = """# 文档管理与协作

## 权限控制

iSpaceDoc 支持三级细粒度权限：

| 权限级别 | 允许的操作 |
|---------|----------|
| `view` | 查看文档内容 |
| `edit` | 编辑文档 |
| `admin` | 管理权限、删除文档 |

权限可以通过 **用户**、**分组**、**组织节点** 三个维度授予，系统自动合并计算最高权限。

## 团队协作功能

### 划词评论

选中任意文本，即可添加评论。评论以高亮下划线标记，支持回复和 @提及其他用户。

### @提及通知

在评论或文档正文中输入 `@用户名`，被提及的用户会收到站内通知（铃铛图标）和邮件通知。

### 文档分享

文档可以生成分享链接，支持：
- 公开分享（无需登录）
- 密码保护
- 随时禁用分享链接

## 水印保护

在文档设置中启用水印，支持：
- 文字水印（显示当前用户名或自定义文字）
- 图片水印

## 数据安全

- **软删除**：删除的文档进入回收站，可随时恢复
- **历史版本**：每次保存自动产生快照，支持 diff 对比和回滚
- **审计日志**：管理后台记录所有关键操作

## 管理后台

访问 `/admin/` 进入管理后台，可以：
- 查看系统健康状态和运行指标
- 管理用户、文档、评论
- 配置认证方式（OIDC / LDAP / 企业微信 / 钉钉）
- 设置邮件服务
- 备份与导出数据

> success 现在你已经全面了解了 iSpaceDoc 的功能。开始构建你的知识库吧！
"""


def seed_guide(user):
    """对外的快捷入口，效果同 `create_builtin_guide`。"""
    return create_builtin_guide(user)
