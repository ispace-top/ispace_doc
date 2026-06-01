# 爱思文档 AI-MCP 自动化测试用例

> 本文档为 AI 通过 MCP Chrome DevTools 进行自动化测试提供结构化用例。
> 每条用例包含：场景、步骤、预期结果、验证方法。

## 测试前准备

```js
// 系统信息
const BASE = 'http://127.0.0.1:8000';
// 测试账号（安装向导创建）
const ADMIN = { username: 'Admin', password: 'admin123', email: 'admin@ispace.com' };
// 全局状态变量
window.__ISPACEDOC__ = { csrfToken, isAuthenticated, userId, username, version };
```

---

## 1. 安装向导

### 1.1 重定向检测
| 项 | 内容 |
|---|---|
| **场景** | 删除 `.ispace_installed` 和数据库后访问首页 |
| **步骤** | 1. 导航到 `/`  2. 检查 URL |
| **预期** | 自动重定向到 `/setup/` |
| **验证** | `location.pathname === '/setup/'`，页面显示"安装引导"标题 |

### 1.2 五步安装流程
| 步骤 | 字段 | 验证规则 |
|---|---|---|
| 站点信息 | site_name, site_desc, language | 名称 1-64 字符必填，描述 ≤256 |
| 管理员 | username, email, password, password2 | 用户名 ≥5 位字母数字，密码 ≥6 位，两次一致 |
| 数据库 | db_type, host/port/user/password | SQLite 默认跳过；MySQL/PG 需连接参数 |
| 邮件 | smtp_host/port/user/password | 全部可选，可跳过 |
| 确认 | 汇总展示前 4 步数据 | 点击"确认安装" |

**验证**：安装成功后跳转到 `/login/`，数据库中 `User.objects.filter(is_superuser=True).exists()` 为 True，`.ispace_installed` 文件存在。

---

## 2. 用户认证

### 2.1 登录
| 项 | 内容 |
|---|---|
| **场景** | 使用安装时创建的账号登录 |
| **步骤** | 1. 导航到 `/login/`  2. 填入 username/password  3. 点击"登录" |
| **预期** | 跳转首页，Header 显示用户名 + 通知铃铛，侧边栏显示文档树 |
| **验证** | `window.__ISPACEDOC__.isAuthenticated === true` |

### 2.2 注册
| 项 | 内容 |
|---|---|
| **场景** | 新用户注册 |
| **步骤** | 1. 导航到 `/register/`  2. 填写表单  3. 提交 |
| **预期** | 成功后跳转登录页 |
| **验证** | 数据库中存在新用户记录 |

### 2.3 退出登录
| 项 | 内容 |
|---|---|
| **场景** | 点击用户菜单中的退出 |
| **步骤** | 1. 点击 Header 用户按钮  2. 点击退出 |
| **预期** | 跳转首页，显示"登录"/"注册"链接 |
| **验证** | `window.__ISPACEDOC__.isAuthenticated === false` |

---

## 3. 文档 CRUD

### 3.1 新建文档（侧边栏右键）
| 项 | 内容 |
|---|---|
| **场景** | 已登录用户右键侧边栏空白处 → 新建文档 |
| **步骤** | 1. 在 `.ispace-sidebar-nav` 上触发 `contextmenu` 事件  2. 点击"新建文档" |
| **预期** | URL 变为 `/?create=1`，main 区域显示 Vditor 编辑器 + 标题输入框 + 发布按钮 |
| **验证** | `document.getElementById('inline-editor')` 可见，`window._inlineEditor` 存在 |
| **权限** | 未登录用户右键不弹出菜单（`_isLoggedIn()` 返回 false） |

### 3.2 填写并发布文档
| 项 | 内容 |
|---|---|
| **步骤** | 1. 填入标题  2. `window._inlineEditor.setValue(md)` 设置 Markdown 内容  3. 点击"发布" |
| **预期** | 跳转到 `/pages/<id>/`，内容正确渲染 |
| **验证** | 数据库中 `Doc.pre_content` 非空，页面 `#vditor-doc-content` 有内容 |

### 3.3 新建子文档
| 项 | 内容 |
|---|---|
| **场景** | 在文档树节点上右键 → 新建文档 |
| **步骤** | 1. 右键 `.ispace-tree-row`  2. 点击"新建文档" |
| **预期** | URL 变为 `/pages/<parent_id>/?create_child=1`，面包屑显示父文档路径 |
| **验证** | `window._inlineParentDoc` 等于父文档 ID |

### 3.4 编辑文档
| 项 | 内容 |
|---|---|
| **场景** | 在文档查看页点击编辑按钮 |
| **步骤** | 1. 导航到 `/pages/<id>/`  2. 点击编辑按钮  3. 修改内容  4. 点击"发布" |
| **预期** | 内容更新成功，页面刷新显示新内容 |
| **验证** | 数据库 `pre_content` 和 `content` 已更新 |

### 3.5 删除文档
| 项 | 内容 |
|---|---|
| **场景** | 右键文档树节点 → 删除文档 |
| **步骤** | 1. 右键文档节点  2. 点击"删除文档"  3. 确认删除 |
| **预期** | 文档移入回收站（软删除 `is_deleted=True`） |
| **验证** | `Doc.objects.get(id).is_deleted === True` |

### 3.6 文档权限控制
| 项 | 内容 |
|---|---|
| **场景** | 非公开文档，无权限用户访问 |
| **步骤** | 1. 创建非公开文档  2. 用另一用户访问 `/pages/<id>/` |
| **预期** | 显示权限拒绝页面 + 申请权限按钮 |
| **验证** | 页面包含 "无权访问" 或权限申请表单 |

---

## 4. 编辑器功能

### 4.1 Markdown 渲染
| 语法 | 预期渲染 |
|---|---|
| `# H1` ~ `###### H6` | 1-6 级标题，自动生成 id 锚点 |
| `**粗体**` | `<strong>` 标签 |
| `*斜体*` | `<em>` 标签 |
| `` `code` `` | `<code>` 内联代码 |
| ```` ```lang ``` ```` | 代码块 + 语法高亮（Prism.js/hljs） |
| `- item` / `1. item` | 无序/有序列表 |
| `[text](url)` | 链接 |
| `![alt](url)` | 图片 |
| `\| col \| col \|` | 表格 |

**验证**：`#vditor-doc-content` 中包含对应的 HTML 元素。

### 4.2 Callout 提示块
| 语法 | 预期 CSS class | 说明 |
|---|---|---|
| `>i` | `blockquote.info` | 信息提示 |
| `>w` | `blockquote.warning` | 警告提示 |
| `>e` | `blockquote.danger` | 错误提示 |
| `>s` | `blockquote.success` | 成功提示 |

**验证**：`#vditor-doc-content blockquote.info` 存在，`processCallouts()` 已执行。

### 4.3 图表组件（ECharts）
| 项 | 内容 |
|---|---|
| **场景** | 编辑器插入 ECharts 图表 |
| **步骤** | 1. 编辑模式下点击"图表"按钮  2. 配置图表选项  3. 保存 |
| **预期** | 渲染为 ` ```echarts\n{json}\n``` ` 代码块，查看页渲染为 Canvas |
| **验证** | 查看页 `#vditor-doc-content canvas` 存在 |

### 4.4 思维导图 / 流程图 / 手绘图
| 项 | 内容 |
|---|---|
| **步骤** | 编辑模式下点击对应按钮 |
| **预期** | 插入对应代码块（` ```mindmap` / ` ```flow` / ` ```excalidraw` ），查看页渲染 |

### 4.5 图片上传
| 项 | 内容 |
|---|---|
| **场景** | 编辑器中上传图片 |
| **步骤** | 1. 点击"图片"按钮  2. 选择文件或填入 URL |
| **预期** | 插入 `![](url)` 到编辑器 |
| **API** | `POST /files/upload/image/` |

### 4.6 附件上传
| 项 | 内容 |
|---|---|
| **场景** | 编辑器中上传附件 |
| **步骤** | 点击"附件"按钮 → 选择文件 |
| **预期** | 插入 `[【附件】name](url)` |
| **API** | `POST /files/upload/ice-image/` |

### 4.7 编辑器模式切换
| 项 | 内容 |
|---|---|
| **场景** | 切换 Markdown / 所见即所得 / 源码模式 |
| **步骤** | 点击工具栏模式切换按钮 |
| **预期** | 编辑器模式更新，内容保留 |
| **验证** | `window._inlineEditorMode` 值变化，`_updateEditorSwitchLabel` 更新标签 |

---

## 5. 文档树

### 5.1 层级展示
| 项 | 内容 |
|---|---|
| **场景** | 侧边栏展示多级文档树 |
| **验证** | 子文档在父文档下方，可折叠/展开（`.ispace-tree-children` display toggle） |

### 5.2 拖拽排序
| 项 | 内容 |
|---|---|
| **场景** | 拖拽文档节点改变排序或层级 |
| **步骤** | 使用 SortableJS 拖拽 `.ispace-tree-row` |
| **预期** | 文档 `sort` 或 `parent_doc` 更新 |
| **API** | `POST /api/docs/<id>/move/` |

### 5.3 重命名
| 项 | 内容 |
|---|---|
| **场景** | 右键文档 → 重命名 |
| **预期** | 弹出输入框，确认后文档名称更新 |

### 5.4 搜索高亮
| 项 | 内容 |
|---|---|
| **场景** | 在 Header 搜索框输入关键词搜索 |
| **步骤** | 1. 输入关键词  2. 回车 |
| **预期** | 跳转 `/search/?kw=xxx&type=doc`，结果中关键词高亮 |

---

## 6. 评论系统

### 6.1 文档评论
| 项 | 内容 |
|---|---|
| **场景** | 在文档底部发表评论 |
| **步骤** | 1. 点击"回复"展开评论框  2. 输入评论内容  3. 点击"发表评论" |
| **预期** | 评论出现在列表中，计数 +1 |
| **验证** | 页面显示 "评论 ( N )" 且 N 递增；`DocComment.objects.filter(doc=doc, is_active=True).count() === N` |
| **API** | `POST /pages/<id>/comments/` |

### 6.2 评论回复（嵌套）
| 项 | 内容 |
|---|---|
| **场景** | 回复已有评论 |
| **步骤** | 1. 点击评论的"回复"按钮  2. 输入回复内容  3. 点击"回复" |
| **预期** | 回复嵌套显示在父评论下方 |
| **验证** | `DocComment.objects.filter(parent=parent_comment, is_active=True).exists()` |

### 6.3 划词评论
| 项 | 内容 |
|---|---|
| **场景** | 选中文档正文文字 → 创建划词评论 |
| **步骤** | 1. 在 `#vditor-doc-content` 内选中文字  2. 点击浮动工具栏"评论"  3. 输入内容  4. 发表 |
| **预期** | 选中文字高亮（`MARK.ispace-inline-marker`），锚点图标出现，评论面板打开 |
| **验证** | `InlineComment.objects.filter(doc=doc, is_active=True).exists()` |
| **API** | `GET/POST /pages/<id>/inline-comments/` |

### 6.4 划词高亮
| 项 | 内容 |
|---|---|
| **场景** | 选中文字 → 点击"高亮" |
| **预期** | 选中文字添加 `SPAN.ispace-inline-highlight` 黄色背景 |
| **验证** | `#vditor-doc-content .ispace-inline-highlight` 存在 |

### 6.5 划词评论头像展示
| 项 | 内容 |
|---|---|
| **场景** | 划词评论面板中每条评论应展示头像 |
| **验证** | 有头像图片时显示 `<img class="ispace-inline-comment-avatar">` ，无头像时显示首字母 `<span class="ispace-inline-comment-avatar-initial">` |
| **交互** | 悬停头像或用户名触发 `[data-user-id]` author-card 弹窗 |

### 6.6 评论删除
| 项 | 内容 |
|---|---|
| **场景** | 评论作者或管理员删除评论 |
| **步骤** | 点击评论的"删除"按钮 |
| **预期** | 评论软删除（`is_active=False`），页面移除该评论 |
| **API** | `POST /comments/<id>/delete/` |

---

## 7. @提及与通知

### 7.1 文档正文 @提及
| 项 | 内容 |
|---|---|
| **场景** | 编辑文档时输入 `@username` |
| **步骤** | 1. 编辑模式  2. 在内容中写入 `@Admin`  3. 发布 |
| **预期** | 查看页 `@Admin` 渲染为可点击链接，通知表中创建 `mention` 类型通知 |
| **验证** | `Notification.objects.filter(notification_type='mention', recipient=mentioned_user).exists()` |

### 7.2 评论 @提及
| 项 | 内容 |
|---|---|
| **场景** | 文档评论/划词评论中 @用户 |
| **步骤** | 评论内容包含 `@用户` |
| **预期** | 被 @ 的用户收到通知 |
| **验证** | 同上 |

### 7.3 自 @提及
| 项 | 内容 |
|---|---|
| **场景** | 用户 @自己（备忘场景） |
| **步骤** | 评论/编辑中写 `@自己的用户名` |
| **预期** | 创建通知（不再过滤自己） |
| **验证** | 自己收到 mention 通知 |

### 7.4 通知列表
| 项 | 内容 |
|---|---|
| **场景** | 点击 Header 通知铃铛 |
| **步骤** | 点击铃铛按钮 → 下拉面板展开 |
| **预期** | 显示未读通知列表，每条有头像/标题/摘要/时间 |
| **验证** | 通知面板可见，`unread-count` API 返回正确数量 |
| **API** | `GET /api/notifications/`，`GET /api/notifications/unread-count/` |

### 7.5 全部已读
| 项 | 内容 |
|---|---|
| **场景** | 点击"全部已读" |
| **步骤** | 通知面板中点击"全部已读"按钮 |
| **预期** | 所有通知 `is_read=True` |
| **API** | `POST /api/notifications/read/` |

---

## 8. 文件管理

### 8.1 图片上传
| API | 说明 |
|---|---|
| `POST /files/upload/image/` | 编辑器图片上传 |
| `GET /files/images/` | 图片管理列表 |
| `POST /files/image-groups/` | 图片分组管理 |

### 8.2 附件管理
| API | 说明 |
|---|---|
| `GET /files/attachments/` | 附件列表 |
| 编辑器中上传 | 插入 `[【附件】name](url)` |

---

## 9. 权限系统

### 9.1 文档权限授权
| 项 | 内容 |
|---|---|
| **场景** | 文档设置中授予用户/组/组织权限 |
| **步骤** | 1. 打开文档设置  2. 选择权限 Tab  3. 添加用户/组/组织  4. 选择权限级别（view/edit/admin） |
| **API** | `POST /api/docs/<id>/permissions/grant/` |
| **权限合并** | 直接授权 + 组授权 + 组织授权 → 取最高级别 |

### 9.2 权限撤销
| API | 说明 |
|---|---|
| `POST /api/docs/<id>/permissions/revoke/` | 撤销某条授权 |
| `GET /api/docs/<id>/permissions/` | 查看权限列表 |

### 9.3 权限申请
| 项 | 内容 |
|---|---|
| **场景** | 无权用户访问非公开文档 |
| **预期** | 显示申请权限按钮，点击后向文档管理员发送 `perm_apply` 通知 |

---

## 10. 文档分享

### 10.1 创建分享链接
| 项 | 内容 |
|---|---|
| **场景** | 为私密文档创建分享链接 |
| **API** | `POST /shared-links/create/` |

### 10.2 分享链接验证
| 项 | 内容 |
|---|---|
| **场景** | 通过分享链接访问文档 |
| **API** | `POST /shared-links/verify/` |

---

## 11. 水印功能

### 11.1 水印渲染
| 项 | 内容 |
|---|---|
| **场景** | 文档启用文字水印 |
| **步骤** | 1. 文档设置中启用 `is_watermark=True`, `watermark_type=1`  2. 查看文档 |
| **预期** | 水印层 `.ispace-watermark-layer` 包含 `<span>` 平铺水印文字，透明度 0.06-0.1，倾斜 -15° |
| **验证** | `#watermark-layer` 存在且 `aria-hidden="true"` |

### 11.2 默认水印值
| 项 | 内容 |
|---|---|
| **场景** | 未设置 `watermark_value` |
| **预期** | 水印显示当前用户名 |

---

## 12. 主题切换

### 12.1 深色/亮色模式
| 项 | 内容 |
|---|---|
| **场景** | 点击 Header 主题切换按钮 |
| **步骤** | 点击"切换主题"按钮 |
| **预期** | 页面在 `light` / `dark` CSS 主题间切换 |
| **验证** | `<html>` 的 `data-theme` 属性变化 |

---

## 13. 搜索功能

### 13.1 关键词搜索
| 项 | 内容 |
|---|---|
| **场景** | 搜索文档 |
| **步骤** | 1. 输入关键词  2. 回车 |
| **预期** | 跳转 `/search/?kw=xxx&type=doc` |
| **API** | `GET /search/query/` (Whoosh 全文检索) |

### 13.2 搜索结果高亮
| 项 | 内容 |
|---|---|
| **预期** | 搜索结果中关键词用 `<em class="highlight">` 高亮 |

---

## 14. 用户中心

### 14.1 个人资料
| API | 说明 |
|---|---|
| `GET /api/users/<id>/profile/` | 用户信息浮窗 |
| `POST /api/user/profile/edit/` | 编辑个人资料 |
| `POST /api/user/avatar/upload/` | 头像上传（Cropper.js 200x200 裁剪） |
| `POST /api/user/change-password/` | 修改密码 |

### 14.2 通知设置
| 项 | 内容 |
|---|---|
| **场景** | 配置邮件通知开关 |
| **API** | `GET/POST /api/user/notify-settings/` |

### 14.3 浏览记录
| API | 说明 |
|---|---|
| `GET /api/user/browse-history/` | 最近浏览的文档 |

### 14.4 收藏
| 项 | 内容 |
|---|---|
| **场景** | 收藏/取消收藏文档 |
| **API** | `POST /my/bookmarks/toggle/` |

---

## 15. 安全测试

### 15.1 未登录访问控制
| 测试点 | 预期 |
|---|---|
| 访问 `/pages/<id>/`（公开文档） | 正常显示（只读，无编辑/评论按钮） |
| 访问 `/pages/<id>/`（非公开文档） | 重定向到登录页或显示权限拒绝 |
| 直接访问 `/documents/create/` | 重定向到登录页 |
| 右键侧边栏空白处 | 不弹出菜单（`_isLoggedIn()` 返回 false） |
| 右键文档树节点 | 不弹出菜单 |

### 15.2 XSS 防护
| 测试点 | 预期 |
|---|---|
| 文档标题输入 `<script>alert(1)</script>` | 转义显示，不执行 |
| 评论输入 HTML 标签 | 转义显示 |

### 15.3 CSRF 防护
| 测试点 | 预期 |
|---|---|
| 不带 CSRF Token 的 POST 请求 | 返回 403 |

---

## 16. 调试模式

### 16.1 DEBUG 自动检测
| 场景 | 预期 DEBUG |
|---|---|
| 本地 `python manage.py runserver`（无 env var） | `True` |
| `DEBUG=false python manage.py runserver` | `False` |
| `DEBUG=true python manage.py shell` | `True` |
| Docker + `DEBUG=false` env var | `False` |

---

## 验证工具函数

```js
// 通用验证函数集合，用于 MCP evaluate_script

function _tc_check() {
  return {
    // 安装状态
    isInstalled: !!document.querySelector('.ispace-installed') || window.__ISPACEDOC__,
    // 认证状态
    isLoggedIn: window.__ISPACEDOC__?.isAuthenticated || false,
    // 编辑器状态
    editorExists: !!window._inlineEditor,
    editorMode: window._inlineEditorMode,
    // 文档内容
    contentRendered: document.getElementById('vditor-doc-content')?.innerHTML?.length > 0,
    blockquoteInfo: document.querySelectorAll('#vditor-doc-content blockquote.info').length,
    blockquoteWarning: document.querySelectorAll('#vditor-doc-content blockquote.warning').length,
    blockquoteDanger: document.querySelectorAll('#vditor-doc-content blockquote.danger').length,
    blockquoteSuccess: document.querySelectorAll('#vditor-doc-content blockquote.success').length,
    // 评论
    commentCount: document.querySelectorAll('.ispace-comment-item, [class*="comment-item"]').length,
    inlineCommentMarkers: document.querySelectorAll('MARK.ispace-inline-marker').length,
    inlineHighlights: document.querySelectorAll('SPAN.ispace-inline-highlight').length,
    // 水印
    watermarkExists: !!document.getElementById('watermark-layer'),
    watermarkAriaHidden: document.getElementById('watermark-layer')?.getAttribute('aria-hidden') === 'true',
    // 通知
    notificationCount: parseInt(document.querySelector('[class*="notification-badge"]')?.textContent || '0'),
    // 主题
    theme: document.documentElement.getAttribute('data-theme'),
    // 侧边栏
    sidebarTreeNodes: document.querySelectorAll('.ispace-tree-node').length,
    // 错误
    consoleErrors: 0  // 需用 list_console_messages 工具检查
  };
}
```
