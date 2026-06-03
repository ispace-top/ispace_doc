# 爱思文档 AI-MCP 自动化测试用例

> 本文档为 AI 通过 MCP Chrome DevTools 进行全自动化测试的完整脚本。
> 必须按顺序逐条执行，不跳过任何用例。途中遇到异常仅记录，不修复，不中断。
> 全部执行完毕后输出结构化测试报告。

---

## 第-1章 测试环境自动化准备

> 首次执行测试前，按本章步骤准备环境。已准备过的环境可跳过对应步骤。

### P1. 清理并重建数据库和安装状态
```bash
# 1. 停止服务器
netstat -ano | grep ":8000" | awk '{print $NF}' | sort -u | while read p; do taskkill /F /PID $p 2>/dev/null; done; sleep 2

# 2. 清理所有持久化数据
rm -f .ispace_installed data/db.sqlite3 db.sqlite3 2>/dev/null

# 3. 删除并重建 whoosh 索引
rm -rf whoosh_index/

# 4. 运行 migrate 创建空数据库
python manage.py migrate --noinput

# 5. 启动服务器
python manage.py runserver &
```

### P2. 创建测试用户
```bash
python manage.py shell -c "
from django.contrib.auth.models import User
# P2.1 管理员（安装向导会创建，若系统已安装则直接创建）
u1, _ = User.objects.get_or_create(username='Admin', defaults={'email': 'admin@ispace.com'})
u1.set_password('admin123'); u1.is_superuser = True; u1.is_staff = True; u1.save()
# P2.2 普通用户（用于权限和多用户测试）
u2, _ = User.objects.get_or_create(username='TestUser2', defaults={'email': 'test2@test.com'})
u2.set_password('test123456'); u2.save()
print('P2_done: users=', User.objects.count())
"
```

### P3. 创建测试文档
```bash
python manage.py shell -c "
from backend.apps.doc.models import Doc
from django.contrib.auth.models import User
admin = User.objects.get(username='Admin')
markdown_tpl = '''# 自动化测试基础文档

## Callout 提示块测试

>i **信息提示** — 这是一条 info 级别的提示信息。

>w **警告提示** — 请注意，这个操作可能会影响系统性能。

>e **错误提示** — 数据库连接失败，请检查网络配置。

>s **成功提示** — 文档已成功发布。

## 代码块测试

\`\`\`python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b
\`\`\`

## 表格测试

| 测试项 | 状态 | 备注 |
|--------|------|------|
| Callout 渲染 | 通过 | 4种样式正确 |
| 代码高亮 | 通过 | Python 语法 |
| @提及通知 | 待测 | @Admin |

## 引用测试

> 这是普通引用文本。
>> 这是二级嵌套引用。
'''

# P3.1 公开文档
Doc.objects.create(name='测试文档-Markdown', content='', pre_content=markdown_tpl, create_user=admin, status=1, editor_mode=2, is_public=True)
# P3.2 非公开文档
Doc.objects.create(name='权限测试-非公开文档', content='<p>non-public</p>', pre_content='# 非公开文档', create_user=admin, status=1, editor_mode=2, is_public=False)
print('P3_done: docs=', Doc.objects.filter(is_deleted=False).count())
"
```

### P4. 创建测试图片
```bash
python manage.py shell -c "
import os
from PIL import Image
img_dir = 'media/test'
os.makedirs(img_dir, exist_ok=True)
Image.new('RGB', (100,100), color='red').save(os.path.join(img_dir, 'test_image.png'))
print('P4_done: test_image created')
"
```

### P5. 清除浏览器并验证环境
```js
// 导航到首页前先清除所有状态
localStorage.clear();
sessionStorage.clear();
// 然后服务端清除 sessions
```
```bash
python manage.py shell -c "
from django.contrib.sessions.models import Session
Session.objects.all().delete()
print('P5_done: sessions cleared')
"
```

### P6. 检查环境就绪
```js
// 导航到 BASE/ 后执行
() => ({
  'P6_isAuthenticated': window.__ISPACEDOC__?.isAuthenticated || false,
  'P6_hasLoginLink': !!document.querySelector('a[href*="login"]')
})
```
```bash
python manage.py shell -c "
from django.contrib.auth.models import User
from backend.apps.doc.models import Doc
import os
from django.conf import settings
print('P6_users:', User.objects.count())
print('P6_docs:', Doc.objects.filter(is_deleted=False).count())
print('P6_public:', Doc.objects.filter(is_public=True, is_deleted=False).count())
print('P6_installed:', os.path.exists(os.path.join(settings.BASE_DIR, '.ispace_installed')))
"
```

---

## 第0章 测试前准备

### T0.1 清除浏览器会话
```js
// 清除 localStorage、sessionStorage、cookies
// 然后导航到首页
location.href = BASE;
```

### T0.2 检查认证状态
```js
() => ({
  isAuthenticated: window.__ISPACEDOC__?.isAuthenticated || false,
  userId: window.__ISPACEDOC__?.userId || null,
  username: window.__ISPACEDOC__?.username || ''
})
```
- 预期：按当前会话状态返回
- 若已登录则记录，后续用例可跳过登录步骤

### T0.3 检查安装状态
```bash
python manage.py shell -c "
import os; from django.conf import settings;
print('installed:', os.path.exists(os.path.join(settings.BASE_DIR, '.ispace_installed')));
from django.contrib.auth.models import User;
print('superusers:', User.objects.filter(is_superuser=True).count())"
```

---

## 第1章 安装向导

### T1.1 未安装时重定向
- **前置**：`.ispace_installed` 不存在且无超管
- **步骤**：导航到 `BASE/`
- **验证**：`location.pathname === '/setup/'`，页面含"安装引导"标题
- **边界**：若系统已安装（`.ispace_installed` 存在），此用例自动跳过

### T1.2 站点信息校验
- **T1.2.1 正常输入**：site_name="爱思文档", site_desc="测试", language="中文简体" → 下一步可用
- **T1.2.2 空名称**：site_name="" → 显示错误提示，不可下一步
- **T1.2.3 超长名称**：site_name 输入 65 个字符 → 显示错误提示
- **T1.2.4 超长描述**：site_desc 输入 257 个字符 → 显示错误提示

### T1.3 管理员账号校验
- **T1.3.1 正常输入**：username="Admin", email="admin@test.com", password="admin123", password2="admin123" → 下一步可用
- **T1.3.2 短用户名**：username 输入 3 个字符 → 显示错误提示（不少于5位）
- **T1.3.3 密码不一致**：password="admin123", password2="admin456" → 显示错误提示
- **T1.3.4 弱密码**：password 输入 4 个字符 → 显示错误提示（不少于6位）
- **T1.3.5 无效邮箱**：email="notanemail" → 显示错误提示

### T1.4 数据库配置
- **T1.4.1 SQLite 默认**：选择 SQLite → 直接下一步，无需配置
- **T1.4.2 MySQL 未填参数**：选择 MySQL 但不填参数 → 显示错误提示
- **T1.4.3 PostgreSQL 完整参数**：选择 PG 并填写参数 → 可下一步

### T1.5 邮件配置
- **T1.5.1 跳过**：不填任何邮件信息 → 点击"跳过，确认安装"
- **T1.5.2 填写完整**：填写 SMTP 信息 → 点击下一步

### T1.6 确认安装
- **T1.6.1** 确认页显示前几步汇总 → 点击"确认安装"
- **验证**：跳转 `/login/`，DB 超管存在，`.ispace_installed` 存在

---

## 第2章 用户认证

### T2.1 登录 - 正常流程
- 导航到 `BASE/login/`
- 填入 username="Admin", password="admin123"
- 点击"登录"
- **验证**：`window.__ISPACEDOC__.isAuthenticated === true`，Header 含用户名
- **数据库**：`Session.objects.count() >= 1`

### T2.2 登录 - 错误密码
- 导航到 `BASE/login/`
- 填入正确用户名 + 错误密码 "wrongpass"
- 点击"登录"
- **验证**：留在 `/login/`，显示错误提示

### T2.3 登录 - 不存在的用户
- 填入 username="nonexistent_user_xyz", password="anything"
- 点击"登录"
- **验证**：显示错误提示

### T2.4 登录 - 空字段
- 不填用户名和密码，直接点击"登录"
- **验证**：HTML5 表单校验阻止提交（`required` 属性）

### T2.5 注册 - 正常流程
- 导航到 `BASE/register/`
- 填写完整表单（username="testuser2", email="test2@test.com", password="test123456", password2="test123456"）
- 提交
- **验证**：跳转登录页，`User.objects.filter(username='testuser2').exists()`
- **验证欢迎通知**：
  - `Notification.objects.filter(recipient=user, notification_type='welcome').exists()` → True
  - 欢迎通知的 `title` 含"欢迎"关键词
  - 欢迎通知的 `link` 指向用户指南文档
  - 首页展示欢迎横幅（Welcome Banner）

### T2.5a 注册 - 欢迎通知内容验证
- 登录新注册的用户
- 检查 Header 通知铃铛显示红色角标 "1"
- 打开通知下拉面板 → 第一条通知为欢迎通知，类型图标为信封图标
- 点击欢迎通知 → 跳转到内置用户指南文档
- 铃铛角标消失（欢迎通知标记为已读）

### T2.5b 注册 - 欢迎横幅交互
- 新用户首次登录后首页顶部显示欢迎横幅
- 横幅含站点名称、快速入门引导文案、"查看使用文档"和"开始创作"两个按钮
- 点击"查看使用文档"→ 跳转到用户指南文档
- 点击"开始创作"→ 跳转到新建文档页
- 点击关闭按钮 [✕] → 横幅消失
- 刷新页面 → 横幅不再显示（`localStorage.ispace_welcome_dismissed` 已记录）

### T2.6 注册 - 用户名已存在
- 用已存在的用户名（如 "Admin"）注册
- **验证**：显示错误提示

### T2.7 退出登录
- 已登录状态，导航到 `BASE/logout/` 或点击退出按钮
- 导航回 `BASE/`
- **验证**：`window.__ISPACEDOC__.isAuthenticated === false`，Header 显示"登录"

### T2.8 登录后重定向
- 未登录状态访问 `BASE/pages/1/`（需要登录的页面）
- **验证**：重定向到 `/login/?next=/pages/1/`
- 登录后自动跳回 `/pages/1/`

---

## 第3章 文档 CRUD

### T3.1 新建文档 — 侧边栏空白处右键
- **前置**：已登录
- **T3.1.1 正常创建**：在 `.ispace-sidebar-nav` 上触发 `contextmenu` → 点击"新建文档"
- **验证**：URL 变为 `/?create=1`，编辑器 + 标题输入 + 发布按钮可见
- **T3.1.2 未登录**：清除 session 后，右键侧边栏空白处
- **验证**：不弹出菜单（`_isLoggedIn()` 返回 false）

### T3.2 新建文档 — 填写和发布
- **T3.2.1 正常发布**：标题="T3.2测试文档"，`setValue('# T3.2\n\n内容正文')`，点击"发布"
- **验证**：跳转 `/pages/<id>/`，`#vditor-doc-content` 含渲染内容，DB `pre_content` 非空
- **T3.2.2 空标题**：标题=""，点击"发布"
- **验证**：显示提示或标题自动为"未命名文档"
- **T3.2.3 超长标题**：标题输入 200 字符 → 确认可发布或有限制
- **T3.2.4 空内容**：标题="空内容测试"，不填内容，点击"发布"
- **验证**：可成功发布，内容为空
- **T3.2.5 防重复提交**：新建文档，填写标题和内容，快速双击"发布"按钮
- **验证**：第一次点击后按钮立即变为 `[spinner] 发布中...` 且禁用（opacity 0.6）
- **验证**：第二次点击被 `_isSubmitting` 守卫拦截，不发起第二次请求
- **验证**：请求完成后数据库仅存在 1 条同名文档（`Doc.objects.filter(name=title).count() == 1`）
- **T3.2.6 保存草稿防重复**：同上，快速双击"保存草稿"按钮
- **验证**：按钮变为 `[spinner] 保存中...`，仅执行一次保存
- **T3.2.7 按钮恢复**：提交成功后按钮自动恢复为正常样式（"发布" + 图标，可点击）
- **验证**：`ispace-spinner` 已移除，`opacity` 恢复为 `''`，`disabled` 为 `false`
- **T3.2.8 按钮失败恢复**：模拟网络断开，点击"发布" → 请求失败 → 按钮恢复
- **验证**：失败后按钮恢复为可用状态，不永久禁用

### T3.3 新建表格
- **前置**：已登录
- **T3.3.1 创建表格**：右键侧边栏空白处 → "新建表格"
- **验证**：URL 含 `?create=1&eid=4`，Luckysheet 加载
- **验证**：`window._inlineEditorMode === 4`

### T3.4 新建子文档
- **T3.4.1 从文档节点创建**：右键侧边栏文档节点 → "新建文档"
- **验证**：URL 变为 `/pages/<parent_id>/?create_child=1`
- **T3.4.2 面包屑**：创建完成后查看页面包屑显示父文档路径
- **验证**：数据库 `parent_doc` 字段正确

### T3.5 编辑文档
- **T3.5.1 进入编辑**：在文档查看页 `/pages/<id>/` 点击编辑按钮
- **验证**：URL 变为 `/pages/<id>/?edit=1`，编辑器加载，标题和原内容回显
- **T3.5.2 修改后发布**：修改标题和内容 → 点击"发布"
- **验证**：`Doc.objects.get(id).name` 和 `.pre_content` 已更新
- **T3.5.3 保存草稿**：编辑后点击"保存草稿"（若有此按钮）
- **验证**：`Doc.status === 0`

### T3.6 删除文档
- **T3.6.1 软删除**：右键文档节点 → "删除文档" → 确认
- **验证**：`Doc.objects.get(id).is_deleted === True`
- **T3.6.2 侧边栏移除**：删除后侧边栏不再显示该文档
- **T3.6.3 回收站可见**：导航到 `/documents/recycle/` 可见已删除文档

### T3.7 恢复文档
- 在回收站中恢复已删除的文档
- **验证**：`is_deleted === False`，侧边栏重新出现

### T3.8 查看文档
- **T3.8.1 公开文档**：任何人可查看
- **T3.8.2 浏览记录**：查看后 `BrowseHistory` 表有记录
- **T3.8.3 404**：访问不存在的文档 ID → 显示 404 页面

---

## 第4章 编辑器功能

### T4.1 Markdown 基础语法
每项语法插入到编辑器 → 发布 → 检查 `#vditor-doc-content` 中的 DOM：

| 用例 | 输入 | 预期 DOM |
|---|---|---|
| T4.1.1 H1-H6 | `# H1` ~ `###### H6` | `<h1>`~`<h6>` 带 id 属性 |
| T4.1.2 粗体 | `**bold**` | `<strong>bold</strong>` |
| T4.1.3 斜体 | `*italic*` | `<em>italic</em>` |
| T4.1.4 删除线 | `~~strike~~` | `<del>strike</del>` |
| T4.1.5 内联代码 | `` `code` `` | `<code>code</code>` |
| T4.1.6 代码块 | ` ```python\nprint(1)\n``` ` | `<pre><code class="language-python">` |
| T4.1.7 无序列表 | `- item1\n- item2` | `<ul><li>` |
| T4.1.8 有序列表 | `1. item1\n2. item2` | `<ol><li>` |
| T4.1.9 任务列表 | `- [ ] todo\n- [x] done` | 含 checkbox |
| T4.1.10 链接 | `[text](http://example.com)` | `<a href="...">` |
| T4.1.11 图片 | `![alt](/media/test.png)` | `<img>` |
| T4.1.12 表格 | `\| a \| b \|\n\| --- \| --- \|\n\| 1 \| 2 \|` | `<table>` |

### T4.2 Callout 提示块
| 用例 | 输入 | 预期 CSS class |
|---|---|---|
| T4.2.1 Info | `>i 信息` | `blockquote.info` + 图标 |
| T4.2.2 Warning | `>w 警告` | `blockquote.warning` + 图标 |
| T4.2.3 Error | `>e 错误` | `blockquote.danger` + 图标 |
| T4.2.4 Success | `>s 成功` | `blockquote.success` + 图标 |

**边界测试**：
- T4.2.5：`>i` 后无空格 → 检查是否仍渲染为 callout
- T4.2.6：`>x` 未知类型 → 检查是否渲染为普通 blockquote
- T4.2.7：callout 内含多段落 → 检查渲染是否正确

### T4.3 嵌套引用
- T4.3.1：`> L1\n>> L2\n>>> L3` → 3 层嵌套 `<blockquote>`
- T4.3.2：callout 内嵌套引用 → 检查混合渲染

### T4.4 编辑器模式切换
- T4.4.1：点击"源码模式" → `window._currentVditorMode` 变化
- T4.4.2：切换回 IR 模式 → 内容保留
- T4.4.3：切换到所见即所得 → 内容保留

### T4.5 撤销/重做
- T4.5.1：输入文字 → Ctrl+Z 撤销 → 文字消失
- T4.5.2：Ctrl+Y 重做 → 文字恢复

### T4.6 图表（ECharts）
- **T4.6.1 柱状图**：编辑模式点击"图表"下拉 → 选择柱状图 → 配置数据 → 插入 ` ```echarts\n{json}\n``` ` 代码块 → 发布
- **验证**：查看页 `#vditor-doc-content canvas` 存在（≥2 个 canvas 元素），图表正确渲染
- **T4.6.2 折线图**：同上，选择折线图类型 → 插入并发布 → Canvas 渲染
- **T4.6.3 饼图**：同上，选择饼图类型 → Canvas 渲染
- **T4.6.4 散点图**：同上，选择散点图类型 → Canvas 渲染
- **T4.6.5 雷达图**：同上 → Canvas 渲染
- **T4.6.6 空数据**：插入无 series 数据的 ECharts → 不崩溃，显示空图表或提示
- **T4.6.7 JSON 语法错误**：插入含语法错误的 JSON → 不崩溃，渲染容错处理
- **T4.6.8 图表下拉 UI**：点击"图表"按钮 → 弹出下拉面板，含 5+ 种图表类型图标+名称

### T4.7 思维导图 / 流程图 / 手绘图
- **T4.7.1 思维导图**：编辑模式点击"思维导图" → 插入 ` ```mindmap ` 代码块（Markdown 嵌套列表格式） → 发布
- **验证**：查看页渲染为 SVG（`#vditor-doc-content svg` 存在）
- **T4.7.2 流程图**：编辑模式点击"流程图" → 插入 ` ```flowchart ` 代码块（flowchart.js 语法：st=>start/e=>end/op=>operation/cond=>condition） → 发布
- **验证**：查看页渲染为 SVG（9 个 flowchart 元素），节点和连线正确显示
- **T4.7.3 手绘图**：编辑模式点击"手绘图" → 插入 ` ```excalidraw ` 代码块 → 发布
- **验证**：查看页渲染为 SVG/Canvas，支持缩放和拖拽
- **T4.7.4 思维导图空内容**：插入空的 ` ```mindmap ``` ` → 不崩溃，显示空 SVG 或占位
- **T4.7.5 流程图语法错误**：插入含错误语法的流程图 → 渲染降级，至少显示原始文本
- **T4.7.6 代码块语言标记**：验证 pre code 的 class 正确对应：`language-mindmap` / `language-flowchart` / `language-echarts`

**验证脚本**：
```js
() => ({
  'T4.6_echarts_canvas': document.querySelectorAll('#vditor-doc-content canvas').length,
  'T4.7_mindmap_svg': !!document.querySelector('#vditor-doc-content svg'),
  'T4.7_flowchart_elements': document.querySelectorAll('#vditor-doc-content [class*="flowchart"], #vditor-doc-content [class*="flow"]').length,
  'T4.6_hasECharts': !!document.querySelector('#vditor-doc-content [class*="echarts"]'),
  'pre_count': document.querySelectorAll('#vditor-doc-content pre').length
})
```

---

### T4.8 数学公式 (KaTeX)
- **T4.8.1 行内公式**：编辑器中输入 `$E=mc^2$` → 发布 → 查看页渲染为 KaTeX HTML（`.katex` 元素 > 0）
- **T4.8.2 块级公式**：`$$\n\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}\n$$` → KaTeX 块级渲染
- **T4.8.3 分数公式**：`$\\frac{a}{b}$` → KaTeX 渲染
- **T4.8.4 矩阵公式**：`$$\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}$$` → KaTeX 渲染
- **T4.8.5 无效公式**：`$未闭合公式 → 显示原始文本，不崩溃
- **验证**：`#vditor-doc-content .katex` 元素数量 ≥ 输入公式数

### T4.9 Mermaid 图表
- **T4.9.1 流程图 (graph TD)**：` ```mermaid\ngraph TD\nA-->B\n``` ` → 渲染为 SVG 流程图
- **T4.9.2 时序图 (sequenceDiagram)**：mermaid 时序图语法 → SVG
- **T4.9.3 类图 (classDiagram)**：UML 类图 → SVG
- **T4.9.4 状态图 (stateDiagram-v2)**：状态机图 → SVG
- **T4.9.5 Gantt 图**：甘特图 → SVG
- **验证**：`#vditor-doc-content` 含 mermaid 渲染 SVG 或 Canvas

### T4.10 时序图 (sequence)
- **T4.10.1**：` ```sequence\n客户端->服务器: 请求\n服务器-->客户端: 响应\n``` ` → 发布
- **验证**：渲染为 SVG 时序图（`Raphael` + `js-sequence-diagrams`），`#vditor-doc-content svg` 存在

### T4.11 PlantUML
- **T4.11.1**：` ```plantuml\n@startuml\nAlice -> Bob: Hello\n@enduml\n``` ` → 发布
- **验证**：通过客户端 `plantumlEncoder` 编码后调用 `https://www.plantuml.com/plantuml/svg/` 渲染为 SVG，`.language-plantuml object` 或 `img` 存在

### T4.12 Graphviz (DOT)
- **T4.12.1**：` ```graphviz\ndigraph G { rankdir=LR; A -> B -> C; A -> C; }\n``` ` → 发布
- **验证**：✅ `.language-graphviz` DIV 含 SVG，有向图正确渲染（节点 A/B/C + 连线 A→B, B→C, A→C）

### T4.13 音乐乐谱 (abcjs)
- **T4.13.1**：` ```abc\nX:1\nT:小星星\nK:C\nC C G G | A A G2 |\n``` ` → 发布
- **验证**：✅ `.language-abc` DIV 含 SVG，五线谱正确渲染

### T4.14 手绘图 (Excalidraw)
- **T4.14.1**：编辑模式点击"手绘图" → 插入 ` ```excalidraw ` 代码块 → 发布
- **验证**：通过独立 Excalidraw 编辑模板（`editor_mode=7`）渲染为 SVG/Canvas

### T4.15 代码块增强
- **T4.15.1 语法高亮**：` ```python\n...\n``` ` → 查看页 `<code class="language-python hljs">`
- **T4.15.2 代码标题**：` ```python title=文件名.py\n...\n``` ` → 代码块顶部显示文件名标签
- **T4.15.3 行号**：代码块可配置行号显示
- **T4.15.4 复制按钮**：代码块右上角复制按钮 → 点击复制内容到剪贴板

### T4.14 编辑器图表插入综合验证
```js
() => ({
  'katex_elements': document.querySelectorAll('.katex').length,
  'mermaid_svg': document.querySelectorAll('[id*="mermaid"] svg, .mermaid svg').length,
  'total_svg': document.querySelectorAll('#vditor-doc-content svg').length,
  'total_canvas': document.querySelectorAll('#vditor-doc-content canvas').length,
  'code_blocks': document.querySelectorAll('#vditor-doc-content pre code').length,
  'isT4.8_katex': document.querySelectorAll('.katex').length > 0,
  'isT4.9_mermaid': document.querySelectorAll('#vditor-doc-content svg').length >= 4,
  'isT4.6_echarts': document.querySelectorAll('#vditor-doc-content canvas').length >= 2
})
```

---

## 第5章 文档树

### T5.1 层级显示
- T5.1.1：父文档下创建子文档 → 侧边栏缩进展示
- T5.1.2：点击展开/折叠箭头 → `.ispace-tree-children` 切换 `display`
- T5.1.3：图标状态切换（folder-closed ↔ folder-open）

### T5.2 拖拽排序
- T5.2.1：拖拽同级文档改变排序 → API `POST /api/docs/<id>/move/` 调用成功
- T5.2.2：拖拽文档到另一父文档下 → `parent_doc` 更新
- T5.2.3：拖拽父文档到自己的子文档下 → 应被阻止或提示错误

### T5.3 重命名
- T5.3.1：右键文档 → "重命名" → 输入新名称 → 回车
- 验证：文档名称更新，侧边栏和面包屑同步更新
- T5.3.2：重命名为空 → 应提示错误

### T5.4 侧边栏折叠
- T5.4.1：点击折叠按钮 → 侧边栏收起
- T5.4.2：再次点击 → 侧边栏展开

---

## 第6章 评论系统

### T6.1 文档评论 — 发表
- T6.1.1：点击"回复"展开评论输入框
- T6.1.2：输入 "T6测试评论" → 点击"发表评论"
- 验证：评论列表新增 1 条，计数 N+1，"评论 ( 1 )"
- T6.1.3：空评论 → 应阻止提交
- T6.1.4：超长评论（2000+ 字符）→ 应截断或提示

### T6.2 文档评论 — 回复
- T6.2.1：点击已有评论的"回复" → 输入框展开（嵌套在评论下方）
- T6.2.2：输入回复内容 → 点击"回复"
- 验证：嵌套显示在父评论下方
- T6.2.3：多级嵌套 → 第3层以上不再缩进或折叠

### T6.3 文档评论 — 头像
- T6.3.1：每条评论显示圆形头像（24px）
- T6.3.2：无头像图片时显示用户名首字母
- T6.3.3：悬停头像触发 author-card（`[data-user-id]`）

### T6.4 文档评论 — 删除
- T6.4.1：作者点击"删除" → 评论软删除
- 验证：`is_active=False`，页面移除

### T6.5 划词评论 — 创建
- T6.5.1：在 `#vditor-doc-content` 内选中文字 → 浮动工具栏出现
- T6.5.2：工具栏含"评论"、"复制"、"高亮"三个按钮
- T6.5.3：点击"评论" → 评论面板打开 → 输入内容 → "发表"
- 验证：高亮 `MARK.ispace-inline-marker`，面板内显示新评论
- T6.5.4：选中空文本 → 不显示工具栏

### T6.6 划词评论 — 回复
- T6.6.1：在面板中点击"回复" → 输入回复 → 发表
- 验证：嵌套显示

### T6.7 划词评论 — 头像
- T6.7.1：每条评论展示圆形头像（有图片显示 `<img class="ispace-inline-comment-avatar">`，无图片显示首字母 `<span>`）
- T6.7.2：头像元素含 `data-user-id` → 悬停触发 author-card

### T6.8 划词高亮
- T6.8.1：选中文字 → 点击"高亮"
- 验证：`SPAN.ispace-inline-highlight` 黄色背景
- T6.8.2：多次选中不同文字高亮 → 多处高亮

### T6.9 划词评论 — 删除
- T6.9.1：点击评论的删除按钮 → 软删除

### T6.10 评论头部布局 — 用户名截断
- **T6.10.1 短用户名**：创建划词评论，用户名为 2-4 个中文字符
- **验证**：头像 + 用户名 + 时间 + 删除按钮 在同一行，不换行
- **T6.10.2 5 字用户名**：用户名为 5 个中文字符（如"张三四五六"）
- **验证**：头像 + 用户名 + 时间 + 删除按钮 在同一行，不换行（原 bug：5 字用户名会换行）
- **T6.10.3 超长用户名**：用户名 > 5 个中文字符（如"张三四五六七八九十一二"）
- **验证**：用户名中间省略（CSS flex 实现），首部字符 + "..." + 尾部 2 字符
- **验证**：头像 24px 始终完整可见，时间列始终完整可见（`flex-shrink: 0`）
- **T6.10.4 窄面板场景**：将评论面板缩窄到 250px 宽度
- **验证**：三行（短/中/长用户名）均不换行，超长用户名正确截断
- **T6.10.5 普通评论同样适用**：在文档评论区检查相同布局规则
- **验证**：`.ispace-comment-user` 有 `overflow: hidden; text-overflow: ellipsis; white-space: nowrap`
- **T6.10.6 用户卡片可查看全名**：悬停截断后的用户名或头像
- **验证**：弹出 author-card 显示完整用户名

---

## 第7章 @提及与通知

### T7.1 文档正文 @提及
- T7.1.1：编辑文档 → `setValue('# Test\n@Admin 请查看')` → 发布
- 验证：查看页 `@Admin` 为可点击链接
- 验证：`Notification.objects.filter(notification_type='mention', recipient=admin_user).exists()`
- T7.1.2：编辑已有文档，新增 @用户 → 仅通知新增的
- T7.1.3：@不存在的用户 → 文本保留但不创建通知

### T7.2 评论 @提及
- T7.2.1：文档评论中包含 `@Admin` → 创建 mention 通知
- T7.2.2：划词评论中包含 `@Admin` → 创建 mention 通知

### T7.3 自 @提及
- T7.3.1：自己 @自己 "Admin 在文档中 @了 Admin" → 创建通知

### T7.4 通知面板 UI
- T7.4.1：点击 Header 通知铃铛 → 下拉面板展开
- 验证：显示未读通知列表（头像 + 标题 + 摘要 + 时间）
- T7.4.2：未读时有红点或数字角标
- T7.4.3：无通知时显示"暂无通知"

### T7.5 通知操作
- T7.5.1：点击"全部已读" → 所有通知 `is_read=True`
- T7.5.2：点击某条通知 → 跳转到对应文档
- T7.5.3：点击"查看全部通知" → 跳转 `/my/?tab=notifications`

### T7.6 通知类型覆盖
| 类型 | 触发方式 | notification_type |
|---|---|---|
| T7.6.1 文档@提及 | 文档正文 @用户 | `mention` |
| T7.6.2 评论@提及 | 文档评论 @用户 | `mention` |
| T7.6.3 评论回复 | 回复他人评论 | `reply` |
| T7.6.4 划词评论通知 | 在他人文档划词评论 | `comment` |
| T7.6.5 划词评论@提及 | 划词评论 @用户 | `mention` |
| T7.6.6 权限变更 | 文档授权 | `perm_change` |
| T7.6.7 权限申请 | 用户申请访问 | `perm_apply` |

### T7.7 欢迎通知

| 用例 | 测试内容 | 验证点 |
|------|----------|--------|
| T7.7.1 通知创建 | 注册新用户 → 检查 Notification 表 | `notification_type='welcome'`, `recipient` 正确 |
| T7.7.2 通知内容 | 查看欢迎通知的 title 和 body | title 含"欢迎加入", body 含站点名称和入门引导 |
| T7.7.3 通知链接 | 点击欢迎通知 | 跳转到内置用户指南文档 |
| T7.7.4 欢迎横幅 | 新用户首次登录首页 | 顶部展示欢迎横幅，含"查看使用文档"按钮 |
| T7.7.5 横幅关闭 | 点击横幅关闭按钮 → 刷新页面 | 横幅不再显示 |
| T7.7.6 欢迎邮件 | 检查邮件是否发送（需 SMTP 已配置） | 注册邮箱收到欢迎邮件，含用户名和站点名称 |
| T7.7.7 不重复推送 | 老用户登录（非首次） | 不显示欢迎横幅，无新的 welcome 通知 |

---

## 第8章 搜索

### T8.1 关键词搜索
- T8.1.1：Header 搜索框输入 "测试" → 回车
- 验证：跳转 `/search/?kw=测试&type=doc`，结果含相关文档
- T8.1.2：搜索不存在的关键词 → 显示"无结果"
- T8.1.3：空关键词搜索 → 显示全部文档
- T8.1.4：特殊字符搜索 → 不报错

### T8.2 搜索结果高亮
- 验证：结果中的关键词用 `<em class="highlight">` 包装

---

## 第9章 主题切换

### T9.1 深色/亮色模式
- T9.1.1：点击 Header 主题按钮 → `<html data-theme>` 切换
- T9.1.2：默认亮色 → `data-theme="light"`
- T9.1.3：切换到深色 → `data-theme="dark"`
- T9.1.4：再次点击切回 → `data-theme="light"`

---

## 第10章 水印

### T10.1 全局水印层
- T10.1.1：文档页 `#watermark-layer` 存在
- T10.1.2：`aria-hidden="true"`
- T10.1.3：包含 `<span>` 元素平铺用户名
- T10.1.4：CSS opacity 0.06-0.1，倾斜 -15 度

### T10.2 文档级水印开关
- T10.2.1：`is_watermark=False` → 水印层仍需存在（全局），但文档内容无水印覆盖
- T10.2.2：`is_watermark=True, watermark_type=1` → 文档正文区域有水印

---

## 第11章 用户中心

### T11.1 用户信息浮窗（author-card）
- T11.1.1：悬停 `[data-user-id]` 元素 → 300ms 后弹出卡片
- 验证：卡片含头像、用户名、性别、组织、简介
- T11.1.2：鼠标移出 → 200ms 后卡片消失
- T11.1.3：快速连续悬停多个用户 → 不闪烁

### T11.2 个人设置页
- T11.2.1：导航到 `/my/settings/` → 显示个人资料编辑表单
- T11.2.2：修改 first_name → 保存 → 页面显示新名称
- T11.2.3：修改密码 → 旧密码错误 → 提示错误
- T11.2.4：修改密码 → 旧密码正确 → 成功，需重新登录

### T11.3 收藏功能
- T11.3.1：文档查看页点击收藏按钮 → 图标变为实心
- 验证：`MyCollect` 表有记录
- T11.3.2：再次点击 → 取消收藏，图标变空心
- T11.3.3：首页"最近收藏"区域显示已收藏文档

---

## 第12章 安全测试

### T12.1 未登录访问控制
- T12.1.1：未登录访问 `BASE/pages/1/`（公开文档）→ 可查看但无编辑按钮
- T12.1.2：未登录访问非公开文档 → 重定向登录页
- T12.1.3：未登录 POST `/documents/create/` → 302 重定向登录页
- T12.1.4：未登录右键侧边栏 → 不弹出菜单
- T12.1.5：未登录访问 `/admin/` → 要求登录

### T12.2 XSS 防护
- T12.2.1：文档标题输入 `<script>alert(1)</script>` → 发布后页面不弹窗
- T12.2.2：评论输入 `<img src=x onerror=alert(1)>` → 发布后不执行
- T12.2.3：`pre_content` 中 `<script>` 标签 → 被转义

### T12.3 CSRF 防护
- T12.3.1：不带 CSRF Token POST 到 `/documents/create/` → 403

---

## 第13章 边界与异常测试

### T13.1 并发创建
- 快速连续点击"新建文档"2次 → 检查是否创建了重复文档

### T13.2 网络异常
- T13.2.1：发布文档时断开网络 → 显示错误提示
- T13.2.2：网络恢复后重新发布 → 成功

### T13.3 空状态
- T13.3.1：无文档时首页 → 显示"暂无文档"
- T13.3.2：无评论时 → 显示"暂无评论，来发表第一条评论吧"
- T13.3.3：无收藏时 → 显示"暂无收藏"
- T13.3.4：无通知时 → 显示空状态
- T13.3.5：浏览记录中有已删除文档 → 显示文档名+灰色"已删除"标签，不可点击（保留记录，避免用户困惑）

### T13.4 分页
- T13.4.1：创建 15 篇文档 → 首页分页显示（12条/页）
- T13.4.2：翻页 → 第2页显示剩余文档

### T13.5 草稿功能
- T13.5.1：创建文档时保存草稿 → `status=0`
- T13.5.2：草稿文档仅在作者视角可见（标题前缀"【预览草稿】"）
- T13.5.3：草稿发布 → `status=1`

### T13.6 软删除边界
- T13.6.1：删除有子文档的父文档 → 子文档状态检查
- T13.6.2：删除已删除的文档 → 不报错

### T13.7 特殊字符
- T13.7.1：标题含 emoji "测试 🚀 文档" → 正常保存和显示
- T13.7.2：内容含 Unicode 特殊字符 → 正常渲染
- T13.7.3：Markdown 转义字符 `\* \_ \#` → 正确渲染为文本

---

## 第14章 性能指标检查

### T14.1 页面加载
- T14.1.1：首页首次加载 → 检查 console 无 JS 错误
- T14.1.2：文档查看页加载 → `#vditor-doc-content` 在 3s 内渲染完成
- T14.1.3：编辑器加载 → `window._inlineEditor` 在 5s 内可用

### T14.2 API 响应
- T14.2.1：`GET /api/notifications/unread-count/` → 200 OK
- T14.2.2：`GET /api/user/browse-history/` → 200 OK
- T14.2.3：API 响应 Content-Type 为 `application/json`

---

## 测试报告模板

```
=================================================================
  iSpaceDoc AI-MCP 自动化测试报告
  执行时间: YYYY-MM-DD HH:MM
  环境: BASE_URL
  分支: BRANCH_NAME
=================================================================

总用例数: XX  |  通过: XX  |  失败: XX  |  跳过: XX  |  通过率: XX%

-----------------------------------------------------------------
## 失败/异常详情

### [T-X.Y] 用例名称
- **复现步骤**: ...
- **预期结果**: ...
- **实际结果**: ...
- **错误信息**: ...
- **截图/日志**: ...

-----------------------------------------------------------------
## 各章汇总

| 章节 | 总数 | 通过 | 失败 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| 1. 安装向导 | | | | | |
| 2. 用户认证 | | | | | |
| ... | | | | | |
=================================================================
```

---

## 第15章 个人中心

> URL: `/my/` (默认 tab: overview)
> API 前缀: `/api/user/`

### T15.1 个人中心首页
- **T15.1.1** 导航到 `/my/` → 左侧菜单 + 右侧内容区（默认显示概览 tab）
- **T15.1.2** 验证 16 个菜单项分组正确（API: `GET /my/sidebar-menu/`）
- **T15.1.3** 点击各 tab 切换 → 右侧内容区更新
- **T15.1.4** 验证统计数据：文档数、收藏数、组织数

### T15.2 个人资料编辑
- **T15.2.1** 导航到 `/my/settings/` 或 `/my/?tab=profile`
- **T15.2.2** 修改昵称 → 保存 → `POST /api/user/profile/edit/`
- **T15.2.3** 修改性别 → 保存
- **T15.2.4** 修改手机号 → 保存（需验证唯一性）
- **T15.2.5** 修改个人简介 → 保存
- **T15.2.6** 空昵称 → 应提示错误
- **T15.2.7** 重复手机号 → 应提示错误

### T15.3 头像上传
- **T15.3.1** 点击头像 → 打开文件选择器
- **T15.3.2** 选择图片 → Cropper.js 裁剪框出现（200x200）
- **T15.3.3** 裁剪并保存 → `POST /api/user/avatar/upload/`
- **T15.3.4** 上传非图片文件 → 应被拒绝（MIME 校验）
- **T15.3.5** 上传 >5MB 图片 → 应被拒绝

### T15.4 修改密码
- **T15.4.1** 输入旧密码 + 新密码 + 确认新密码 → 保存
- **T15.4.2** 旧密码错误 → 提示错误
- **T15.4.3** 新密码 < 6 位 → 提示错误
- **T15.4.4** 两次新密码不一致 → 提示错误
- **T15.4.5** 修改成功后 session 是否保持 → 不需要重新登录（API 中 `update_session_auth_hash`）

### T15.5 通知设置
- **T15.5.1** 导航到通知设置 tab → `GET /api/user/notify-settings/`
- **T15.5.2** 各开关默认状态正确（邮件/企微/钉钉等）
- **T15.5.3** 切换开关 → 保存 → `POST /api/user/notify-settings/save/`
- **T15.5.4** 每日摘要设置（时间选择）

### T15.6 我的分组
- **T15.6.1** 导航到 `/my/groups/` → `GET /api/user/my-groups/`
- **T15.6.2** 显示创建的分组和加入的分组
- **T15.6.3** 区分 Owner 和 Member 角色标签

### T15.7 组织架构
- **T15.7.1** 导航到组织 tab → `GET /api/user/my-orgs/`
- **T15.7.2** 显示所属部门（含主属部门标记）
- **T15.7.3** 部门路径完整显示

### T15.8 我的文档
- **T15.8.1** 导航到 `/documents/manage/` → 显示我创建的文档列表
- **T15.8.2** 搜索过滤
- **T15.8.3** 分页浏览

### T15.9 文档模板
- **T15.9.1** 导航到 `/content-templates/manage/` → 显示我的模板列表
- **T15.9.2** 创建新模板 → `POST /content-templates/create/`
- **T15.9.3** 编辑模板 → `POST /content-templates/edit/`
- **T15.9.4** 删除模板 → `POST /content-templates/delete/`
- **T15.9.5** API 获取模板内容 → `POST /content-templates/get/`

### T15.10 标签管理
- **T15.10.1** 导航到 `/content-tags/manage/` → 显示标签列表
- **T15.10.2** 按标签筛选文档 → `/content-tags/<id>/documents/`

### T15.11 分享管理
- **T15.11.1** 导航到 `/shared-links/manage/` → 显示分享链接列表
- **T15.11.2** 创建分享链接 → `POST /shared-links/create/`

### T15.12 图片管理
- **T15.12.1** 导航到 `/files/images/` → 显示上传的图片列表
- **T15.12.2** 分页/搜索
- **T15.12.3** 图片分组管理 → `/files/image-groups/`

### T15.13 附件管理
- **T15.13.1** 导航到 `/files/attachments/` → 显示附件列表
- **T15.13.2** 分页/搜索

### T15.14 回收站
- **T15.14.1** 导航到 `/documents/recycle/` → 显示已删除文档
- **T15.14.2** 恢复文档 → `POST /documents/restore/`
- **T15.14.3** 回收站为空 → 空状态显示

### T15.15 浏览记录
- **T15.15.1** 访问 `/api/user/browse-history/` → 返回最近浏览列表
- **T15.15.2** 记录类型正确（仅 doc 类型）
- **T15.15.3** 分页支持

### T15.16 草稿
- **T15.16.1** 访问 `/api/user/my-drafts/` → 返回最近 5 条草稿
- **T15.16.2** 草稿标题含"【预览草稿】"前缀

### T15.17 Token 管理
- **T15.17.1** 访问 `/api/user/token-info/` → 返回当前用户的 API Token

### T15.18 登录记录
- **T15.18.1** 访问 `/api/user/login-records/` → 返回最近 20 条登录记录
- **T15.18.2** 记录含 IP、时间、成功/失败状态

---

## 第16章 管理后台 — 仪表盘

> 所有 URL 以 `/admin/` 开头，需要 superuser 权限。
> 未登录访问应重定向到 `/login/?next=/admin/...`，非超管访问应返回 403。

### T16.1 仪表盘首页
- **T16.1.1** 导航到 `/admin/dashboard/` → 侧边栏菜单 + 概览 iframe/内容区
- **T16.1.2** 菜单 API `GET /admin/dashboard/menu/` → 返回 22 个菜单项 JSON

### T16.2 概览面板 `/admin/dashboard/overview/`
- **T16.2.1** 统计卡片：用户总数、文档总数、今日文档数
- **T16.2.2** 统计卡片：7日活跃用户数
- **T16.2.3** 统计卡片：图片数、附件数、评论数
- **T16.2.4** 最近文档活动列表（含文档名、作者、时间）
- **T16.2.5** 最近审计日志列表
- **T16.2.6** 系统资源监控（CPU、内存、磁盘使用率）— 需要 psutil

---

## 第17章 管理后台 — 用户管理 `/admin/users/`

### T17.1 用户列表
- **T17.1.1** 分页列表 → `GET /admin/api/users`
- **T17.1.2** 用户名搜索过滤
- **T17.1.3** 用户状态标签（激活/禁用、超管/普通）
- **T17.1.4** 点击编辑 → 打开用户详情

### T17.2 创建用户
- **T17.2.1** 打开创建表单
- **T17.2.2** 填写用户名、邮箱、密码 → `POST /admin/api/users`
- **T17.2.3** 勾选"设为超管" → 创建超管
- **T17.2.4** 用户名重复 → 提示错误
- **T17.2.5** 密码 < 6 位 → 提示错误

### T17.3 编辑用户
- **T17.3.1** 修改昵称、邮箱 → `PUT /admin/api/user/<id>`
- **T17.3.2** 修改密码 → `PUT` with `obj=pwd`
- **T17.3.3** 禁用/启用用户 (`is_active` toggle)
- **T17.3.4** 升级/降级超管 (`is_superuser` toggle)

### T17.4 删除用户
- **T17.4.1** 删除确认 → `DELETE /admin/api/user/<id>`
- **T17.4.2** 删除自己 → 应被阻止或提示
- **T17.4.3** 删除后列表中不再显示

### T17.5 用户个人资料页
- **T17.5.1** 导航到 `/admin/users/profile/` → 显示资料编辑表单
- **T17.5.2** 头像、昵称、邮箱、角色等字段

---

## 第18章 管理后台 — 文档管理

### T18.1 文档列表 `/admin/documents/`
- **T18.1.1** 分页列表 → `POST /admin/documents/`
- **T18.1.2** 关键词搜索
- **T18.1.3** 状态筛选：已发布/草稿/全部
- **T18.1.4** 按父文档 ID 筛选
- **T18.1.5** 已发布/草稿数量标签

### T18.2 文档历史 `/admin/documents/<id>/history/`
- **T18.2.1** 版本列表 → `GET /admin/api/doc_history/<id>/`
- **T18.2.2** 对比两个历史版本 → `/documents/<id>/diff/<his_id>/`
- **T18.2.3** 删除单个历史记录 → `DELETE /admin/api/doc_history_detail/`
- **T18.2.4** 清空全部历史 → `DELETE /admin/api/doc_history/<id>/`

### T18.3 文档模板 `/admin/templates/`
- **T18.3.1** 分页模板列表
- **T18.3.2** 关键词搜索
- **T18.3.3** 模板内容预览

### T18.4 回收站管理 `/admin/documents/trash/`
- **T18.4.1** 已删除文档列表 → `GET /admin/api/trash/manage/`
- **T18.4.2** 按文档名/作者/删除人搜索
- **T18.4.3** 恢复文档 → `POST /admin/api/trash/manage/`
- **T18.4.4** 永久删除 → `DELETE /admin/api/trash/manage/`

---

## 第19章 管理后台 — 文件管理

### T19.1 图片管理 `/admin/files/images/`
- **T19.1.1** 分页图片列表 → `GET /admin/api/imgs/`
- **T19.1.2** 按关键词搜索（文件名）
- **T19.1.3** 按上传用户筛选
- **T19.1.4 扫描未引用**：`mode=scan` → 返回未被任何文档引用的图片
- **T19.1.5** 单张删除 → `DELETE /admin/api/img/<id>/`
- **T19.1.6** 批量删除 → `DELETE /admin/api/imgs/` (comma-separated IDs)

### T19.2 附件管理 `/admin/files/attachments/`
- **T19.2.1** 分页附件列表 → `GET /admin/api/attachments/`
- **T19.2.2** 按关键词/用户筛选
- **T19.2.3** 单件删除 → `DELETE /admin/api/attachment/<id>/`
- **T19.2.4** 批量删除 → `DELETE /admin/api/attachments/`

### T19.3 Logo 上传 `/admin/system/logo/upload/`
- **T19.3.1** 上传 site_logo → 验证格式和大小
- **T19.3.2** 上传 site_logo_admin / site_logo_user_center / site_logo_footer
- **T19.3.3** 无效文件类型 → 拒绝
- **T19.3.4** 上传后旧 Logo 被覆盖

---

## 第20章 管理后台 — 系统设置

### T20.1 基本设置 `/admin/settings/`
- **T20.1.1** 站点名称、关键词、描述 → 保存
- **T20.1.2** ICP 备案号 → 保存
- **T20.1.3** 广告代码 (页头/页尾/侧边栏/内容区)
- **T20.1.4** 注册开关 (`close_register`)
- **T20.1.5** 全站强制登录 (`require_login`)
- **T20.1.6** 图片缩放宽度设置
- **T20.1.7** 界面语言设置

### T20.2 邮件设置
- **T20.2.1** SMTP 主机、端口、用户名 → 保存
- **T20.2.2** SMTP 密码 → 加密存储 (enctry)
- **T20.2.3** SSL 开关 (端口465自动启用)
- **T20.2.4** 发件人地址
- **T20.2.5** 测试邮件发送 → `POST /admin/email/test/` → 发送测试邮件到管理员邮箱

### T20.3 文档设置
- **T20.3.1** 图片大小限制 → 保存
- **T20.3.2** 附件后缀白名单 → 保存
- **T20.3.3** 附件大小限制 → 保存

### T20.4 站点配置 API `/admin/settings/site/`
- **T20.4.1** 批量保存 → `POST` JSON `[{type, name, value}]`
- **T20.4.2** 密码字段自动加密

### T20.5 忘记密码 `/admin/password/forgot/`
- **T20.5.1** 发送验证码 → `POST /admin/email/verify-code/`
- **T20.5.2** 验证码错误 → 提示
- **T20.5.3** 验证码过期 (>30min) → 提示
- **T20.5.4** 重置密码成功 → 可登录
- **T20.5.5** 5 次错误 → 10 分钟锁定

---

## 第21章 管理后台 — 注册码管理

### T21.1 注册码列表 `/admin/register-codes/`
- **T21.1.1** 分页列表 → `GET /admin/api/register_code/`
- **T21.1.2** 显示：代码、最大使用次数、已使用次数、状态、过期时间
- **T21.1.3** 状态标签：有效/已用完/已过期

### T21.2 生成注册码
- **T21.2.1** 设置最大使用次数 → 生成 → `POST /admin/api/register_code/`
- **T21.2.2** 设置过期日期 → 生成
- **T21.2.3** 不设上限 → max_uses=0
- **T21.2.4** 验证码为 10 位随机字母数字

### T21.3 删除注册码
- **T21.3.1** 删除未使用的注册码 → `DELETE /admin/api/register_code/`
- **T21.3.2** 已使用过的注册码 → 可删除（已失效）

---

## 第22章 管理后台 — 系统运维

### T22.1 备份 `/admin/system/backup/`
- **T22.1.1** 数据备份 (mode=data) → JSON 导出 app_admin/app_doc/app_api → ZIP
- **T22.1.2** 媒体备份 (mode=media) → ZIP media 目录
- **T22.1.3** 备份完成后返回下载路径

### T22.2 缓存清理 `/admin/system/cache/clear/`
- **T22.2.1** POST → `cache.clear()` → 返回成功
- **T22.2.2** 清理后权限缓存等被重置

### T22.3 索引重建 `/admin/system/index/rebuild/`
- **T22.3.1** POST → 删除 whoosh 索引目录 → 下次搜索自动重建
- **T22.3.2** 重建前后搜索结果对比

### T22.4 版本更新检查 `/admin/system/update/`
- **T22.4.1** GET → 查询 GitHub Releases API
- **T22.4.2** 比较 semver → 返回 current/latest/changelog/download_url
- **T22.4.3** 已是最新版本 → 提示
- **T22.4.4** 网络不通 → 提示检查失败

---

## 第23章 管理后台 — 认证配置

### T23.1 认证配置页 `/admin/system/auth/`
- **T23.1.1** 显示 4 种认证方式：OIDC、钉钉、企业微信、LDAP
- **T23.1.2** 各配置展开/折叠面板

### T23.2 认证配置 CRUD `/admin/api/auth/configs/`
- **T23.2.1** GET → 返回所有配置（敏感字段脱敏）
- **T23.2.2** POST → 保存/更新某 provider 配置
- **T23.2.3** 仅开关模式 (toggle-only) → 不保存敏感信息
- **T23.2.4** 敏感操作记录到审计日志

### T23.3 连接测试 `/admin/api/auth/test/<provider>/`
- **T23.3.1** OIDC → 测试 discovery URL
- **T23.3.2** LDAP → bind 测试
- **T23.3.3** 企微/钉钉 → 跳过（需 OAuth 回调）

### T23.4 OAuth 绑定管理 `/admin/api/auth/bindings/`
- **T23.4.1** GET → 分页绑定列表
- **T23.4.2** 按 provider/用户筛选
- **T23.4.3** 各 provider 绑定数量统计
- **T23.4.4** 解除绑定 → `DELETE /admin/api/auth/bindings/<bid>/`

---

## 第24章 管理后台 — 审计与监控

### T24.1 审计日志 `/admin/audit-logs/`
- **T24.1.1** 分页列表 → `GET /admin/api/audit-logs/`
- **T24.1.2** 按操作类型筛选（8 种 action type）
- **T24.1.3** 按操作用户筛选
- **T24.1.4** 按日期范围筛选
- **T24.1.5** 每条记录显示：时间、用户、IP、操作类型、目标、详情

### T24.2 登录记录 `/admin/login-history/`
- **T24.2.1** 分页列表 → `GET /admin/api/login-records/`
- **T24.2.2** 按用户名筛选
- **T24.2.3** 按成功/失败筛选
- **T24.2.4** 按日期范围筛选
- **T24.2.5** 显示：用户名、IP、User-Agent、时间、成功/失败原因

### T24.3 系统日志 `/admin/system/logs/`
- **T24.3.1** 日志列表 → `GET /admin/api/syslog/`
- **T24.3.2** 按日期筛选（从 `log/` 目录读取可用日期）
- **T24.3.3** 按级别筛选（ERROR / WARNING / INFO / DEBUG）
- **T24.3.4** 按关键词搜索
- **T24.3.5** 返回各级别日志条数统计
- **T24.3.6** 分页浏览

### T24.4 系统健康 `/admin/system/health/`
- **T24.4.1** 健康页加载 → `GET /admin/api/health/`
- **T24.4.2** 系统运行时间 (uptime)
- **T24.4.3** CPU 使用率
- **T24.4.4** 内存使用率
- **T24.4.5** 磁盘使用率
- **T24.4.6** 数据库连接状态
- **T24.4.7** 缓存状态
- **T24.4.8** 邮件 SMTP 连通性
- **T24.4.9** 媒体文件目录
- **T24.4.10** 存储后端状态
- **T24.4.11** 通知渠道状态
- **T24.4.12** 综合健康评分 (0-100)
- **T24.4.13** DEBUG 模式警告横幅

---

## 第25章 管理后台 — 组织、分组、评论、通知

### T25.1 分组管理 `/admin/groups/`
- **T25.1.1** 分组列表 → `GET /admin/api/groups/manage/`
- **T25.1.2** 搜索分组
- **T25.1.3** 创建分组 → `POST` (name + description)
- **T25.1.4** 修改分组 → `PUT`
- **T25.1.5** 删除分组 → `DELETE`

### T25.2 组织管理 `/admin/organization/`
- **T25.2.1** 组织树 → `GET /admin/api/org/manage/` (action=tree)
- **T25.2.2** 查看节点成员 → `GET` (action=members, node_id=X)
- **T25.2.3** 创建节点 → `POST` (action=create)
- **T25.2.4** 重命名节点 → `POST` (action=rename)
- **T25.2.5** 删除节点 → `POST` (action=delete) — 子节点移至父节点
- **T25.2.6** 移动节点 → `POST` (action=move)
- **T25.2.7** 添加成员 → `POST` (action=add_members) → 发送通知 + 清除权限缓存
- **T25.2.8** 移除成员 → `POST` (action=remove_member) → 发送通知 + 清除权限缓存

### T25.3 评论管理 `/admin/comments/manage/`
- **T25.3.1** 评论列表 → `GET /admin/api/comments/`
- **T25.3.2** 按文档名/用户名筛选
- **T25.3.3** 按状态筛选（活跃/已删除）
- **T25.3.4** 切换评论状态 → `POST/PUT` with action=toggle
- **T25.3.5** 软删除评论 → action=delete
- **T25.3.6** 恢复评论 → action=restore

### T25.4 通知管理 `/admin/notifications/manage/`
- **T25.4.1** 通知列表 → `GET /admin/api/notifications/`
- **T25.4.2** 按收件人筛选
- **T25.4.3** 按通知类型筛选
- **T25.4.4** 按已读/未读筛选
- **T25.4.5** 分页浏览

---

## 第26章 管理后台 — 高级配置

### T26.1 存储配置 `/admin/system/storage/`
- **T26.1.1** 查看当前存储后端和配置 → `GET /admin/api/infra/config/`
- **T26.1.2** 切换到其他存储后端 → `POST /admin/api/infra/config/`
- **T26.1.3** 修改后提示需重启服务

### T26.2 数据库配置 `/admin/system/database/`
- **T26.2.1** 显示当前数据库引擎、主机、端口、版本
- **T26.2.2** 连接状态信息（脱敏显示密码）

### T26.3 WebHook 管理 `/admin/system/webhooks/`
- **T26.3.1** WebHook 配置列表
- **T26.3.2** 创建/编辑/删除 WebHook
- **T26.3.3** 投递日志查看

### T26.4 通知渠道 `/admin/system/notification-channels/`
- **T26.4.1** 渠道列表 → `GET /admin/api/notification/channels/`
- **T26.4.2** 显示 6 种渠道状态：in_app / email / wecom / dingtalk / oa / webhook
- **T26.4.3** 启用/禁用渠道 → `PUT /admin/api/notification/channels/<id>/`
- **T26.4.4** 测试邮件渠道 → `POST /admin/api/notification/channels/<id>/`
- **T26.4.5** 测试 WebHook 渠道 → `POST` 发送测试 payload
- **T26.4.6** 通知路由映射 → `GET /admin/api/notification/routes/`

### T26.5 关于页面 `/admin/system/about/`
- **T26.5.1** 显示应用版本号
- **T26.5.2** 显示 Django 版本
- **T26.5.3** 显示 Python 版本
- **T26.5.4** 显示操作系统信息
- **T26.5.5** 显示数据库引擎

---

## 第27章 管理后台 — 权限与安全测试

### T27.1 超管权限保护
- **T27.1.1** 普通用户访问 `/admin/dashboard/` → 403 或重定向
- **T27.1.2** 普通用户访问 `/admin/api/users` → 403
- **T27.1.3** 未登录访问任何 `/admin/` URL → 重定向登录页

### T27.2 审计日志完整性
- **T27.2.1** 创建用户 → 审计日志有记录
- **T27.2.2** 删除文档 → 审计日志有记录
- **T27.2.3** 修改系统设置 → 审计日志有记录
- **T27.2.4** 认证配置修改 → 审计日志有记录（含敏感性标记）

### T27.3 全站强制登录
- **T27.3.1** 启用 `require_login` → 未登录访问任意页面均重定向
- **T27.3.2** 白名单路径不受影响（登录/注册/忘记密码/静态文件）

### T27.4 注册开关
- **T27.4.1** 关闭注册 (`close_register=on`) → `/register/` 返回 404
- **T27.4.2** 开启注册 → `/register/` 正常访问

---

## 第28章 企业微信账号绑定

> 前置条件：`[auth.wecom]` 已配置且 `enabled=true`

### T28.1 绑定入口

- **T28.1.1** 登录 → 个人中心 → 账号安全 Tab → 第三方账号绑定区域可见
- **T28.1.2** 绑定区域展示：企业微信、钉钉、OIDC 三行（已配置的显示"未绑定"，未配置的显示"未配置"）
- **T28.1.3** 未绑定状态显示"绑定企业微信"按钮（outline 样式）
- **T28.1.4** 未配置状态显示"暂不可用"灰色 disabled 按钮

### T28.2 绑定流程

- **T28.2.1** 点击"绑定企业微信"→ 跳转到 `/auth/wecom/bind/`
- **T28.2.2** 302 重定向到企业微信 OAuth 授权页
- **T28.2.3** 用户扫码确认 → 回调 `/auth/wecom/bind/callback/`
- **T28.2.4** 绑定成功 → 重定向回个人中心 → Toast "企业微信账号绑定成功"
- **验证**：`UserProfile.wecom_userid` 非空，`IspOAuthBinding` 表有记录
- **验证**：页面刷新后绑定状态变为绿色"已绑定" + 企微用户名 + 绑定日期

### T28.3 绑定后通知渠道联动

- **T28.3.1** 绑定企微后，通知设置中的企微渠道开关自动开启
- **T28.3.2** 用户被 @提及 → 站内通知 + 企微消息均送达（需企微应用消息 API 正常）

### T28.4 解绑流程

- **T28.4.1** 已绑定状态显示红色"解绑"文字按钮
- **T28.4.2** 点击"解绑"→ 弹出确认对话框："确定要解除企业微信账号绑定吗？解绑后将无法通过企业微信接收通知消息。"
- **T28.4.3** 确认解绑 → AJAX POST `/api/user/bindings/wecom/unbind/` → Toast "已解除绑定"
- **验证**：`UserProfile.wecom_userid` 变为空字符串，`IspOAuthBinding` 记录删除
- **验证**：通知设置中企微渠道开关自动关闭并置灰

### T28.5 解绑后通知回退

- **T28.5.1** 解绑后，被 @提及 → 仅站内通知 + 邮件（不再尝试企微渠道）

### T28.6 管理后台绑定管理

- **T28.6.1** 超管进入 `/admin/system/auth/` → 企业微信面板 → 点击"绑定管理"
- **T28.6.2** 弹出绑定管理模态框（720px），表格展示所有用户的绑定状态
- **T28.6.3** 按用户名搜索 → 结果过滤
- **T28.6.4** 按状态筛选（全部/已绑定/未绑定）→ 结果过滤
- **T28.6.5** 管理员手动解绑某用户 → 二次确认 → 解绑成功
- **验证**：解绑操作记录到审计日志（`action='unbind', target_type='oauth_binding'`）

### T28.7 边界测试

- **T28.7.1** 已绑定用户再次绑定 → 更新绑定信息（覆盖旧 `wecom_userid`）
- **T28.7.2** 一个企微账号绑定到多个本地用户 → 最后一个绑定生效，之前的自动解绑
- **T28.7.3** 企微配置随后被禁用 → 已绑定的用户显示"已绑定（平台已禁用）"灰色标签

### T28.8 API 验证

---
## 第29章 文档导出与回收站

### T29.1 文档导出
- **T29.1.1** Markdown 导出：访问 `GET /documents/<id>/export/md/` → 返回 `.md` 文件下载
- **T29.1.2** PDF 导出：访问 `GET /documents/<id>/export/pdf/` → 返回 `.pdf` 文件下载
- **T29.1.3** HTML 导出：访问 `GET /documents/<id>/export/html/` → 返回 `.html` 文件下载
- **T29.1.4** 不存在的文档导出 → 返回 404

### T29.2 回收站管理
- **T29.2.1** 导航到 `/documents/recycle/` → 显示已删除文档列表
- **T29.2.2** 按文档名/作者/删除人搜索 → 结果正确过滤
- **T29.2.3** 恢复文档 → `POST /documents/restore/` → `is_deleted=False`
- **T29.2.4** 永久删除文档 → `DELETE` → 数据库记录物理删除
- **T29.2.5** 清空回收站 → 所有回收站记录被清除
- **T29.2.6** 回收站为空 → 显示空状态提示

---
## 第30章 删除验证与安全操作

### T30.1 删除验证码
- **T30.1.1** 访问 `GET /delete-verify/image/` → 返回验证码图片（Content-Type: image/png）
- **T30.1.2** 提交正确验证码 → `POST /delete-verify/check/` → 返回 `{"code": 0}`
- **T30.1.3** 提交错误验证码 → 返回错误提示

### T30.2 关于我们页面
- **T30.2.1** 未登录访问 `/about/` → 正常显示，含项目简介、技术栈、开源协议、版本信息
- **T30.2.2** 页面响应式 → 移动端卡片堆叠显示

### T30.3 嵌入模式
- **T30.3.1** 访问 `/docs/<id>/?embed=1` → Header/Sidebar/Footer 隐藏，仅正文内容可见
- **T30.3.2** 不传 embed 参数 → 正常布局（Header/Sidebar/Footer 可见）

---
## 第31章 管理后台高级运维

### T31.1 数据备份
- **T31.1.1** 触发数据备份 → `POST /admin/system/backup/` (mode=data) → 返回 ZIP 下载路径
- **T31.1.2** 触发媒体备份 → `POST` (mode=media) → 返回 ZIP 下载路径

### T31.2 缓存清理
- **T31.2.1** `POST /admin/system/cache/clear/` → 返回成功，缓存被清除

### T31.3 索引重建
- **T31.3.1** `POST /admin/system/index/rebuild/` → whoosh 索引目录被删除，可重新搜索

### T31.4 版本更新检查
- **T31.4.1** `GET /admin/system/update/` → 返回 current/latest/changelog/download_url
- **T31.4.2** 已是最新版本 → 提示"已是最新版本"
- **T31.4.3** 网络不通 → 提示检查失败

### T31.5 系统日志
- **T31.5.1** `GET /admin/api/syslog/` → 返回日志列表，按日期/级别筛选
- **T31.5.2** 按关键词搜索 → 结果过滤

### T31.6 通知独立页面
- **T31.6.1** 导航到独立通知页 → 显示所有通知列表（含已读/未读）
- **T31.6.2** 按类型筛选 → 结果正确过滤
- **T31.6.3** 点击"全部已读" → 所有通知标记已读
- **T31.6.4** 点击通知跳转 → 自动标记已读

### T31.7 分享链接管理
- **T31.7.1** 创建分享链接 → 设置公开/私密类型 → 返回分享链接
- **T31.7.2** 私密分享 → 需输入分享码验证 → 验证成功后可见文档内容
- **T31.7.3** 禁用分享链接 → 访问该链接返回 404 或提示已禁用
- **T31.7.4** 删除分享链接 → 链接不再可用

### T31.8 分片上传（Chunked Upload）
- **T31.8.1** 初始化分片上传 → `POST /api/upload/chunked/init/` → 返回 upload_id
- **T31.8.2** 上传单个分片 → `POST /api/upload/chunked/<upload_id>/` → 返回已接收分片列表
- **T31.8.3** 查询上传进度 → `GET /api/upload/chunked/<upload_id>/status/` → 返回 uploaded_chunks 和 progress
- **T31.8.4** 合并分片 → `POST /api/upload/chunked/<upload_id>/complete/` → 文件组装完成
- **T31.8.5** 取消上传 → `POST /api/upload/chunked/<upload_id>/abort/` → 清理临时文件

### T31.9 登录记录管理
- **T31.9.1** 超管访问 `/admin/login-history/` → 分页登录记录列表
- **T31.9.2** 按用户名/成功状态/日期筛选 → 结果过滤
- **T31.9.3** 每条记录显示：用户名、IP、User-Agent、时间、结果

```bash
# 查询当前用户绑定状态
python manage.py shell -c "
from django.contrib.auth.models import User
from backend.apps.doc.models import UserProfile
u = User.objects.get(username='Admin')
p = UserProfile.objects.get(user=u)
print('wecom_userid:', repr(p.wecom_userid))
print('dingtalk_userid:', repr(p.dingtalk_userid))
"
```
