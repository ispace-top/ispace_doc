# 爱思文档 i·Space Doc — RD 代码复审报告

> **复审角色**：资深后端/前端开发工程师  
> **复审范围**：本轮 14 个代码提交（不含纯文档提交）  
> **复审日期**：2026-06-03  

---

## 复审结论

| 严重度 | 数量 | 状态 |
|--------|------|------|
| 🔴 **P0 — 必须修复** | 2 | 见下文 |
| 🟡 **P1 — 建议修复** | 4 | 见下文 |
| 🔵 **P2 — 后续优化** | 3 | 见下文 |
| ⚪ **信息/确认** | 2 | 无需修复 |

---

## 🔴 P0 — 必须修复

### BUG-1: `api_save_table_widths` 缺少登录和请求方法校验

| 维度 | 内容 |
|------|------|
| **文件** | `backend/apps/doc/views.py` — `api_save_table_widths` |
| **问题** | 视图函数缺少 `@login_required` 和 `@require_POST` 装饰器。当前任何未登录用户都可以 POST 修改任意文档的 `content_json` 字段 |
| **风险** | 中。攻击者可以覆盖文档的 content_json（包括绘图数据等有价值内容） |
| **修复** | 添加 `@login_required()` 和 `@require_POST` 装饰器 |

```python
@login_required()
@require_POST
def api_save_table_widths(request, doc_id):
```

### BUG-2: 钉钉 `_get_access_token` 使用 POST 请求调用 GET 风格的 API

| 维度 | 内容 |
|------|------|
| **文件** | `backend/apps/doc/notification_channels.py` — `DingTalkChannel._get_access_token` |
| **问题** | 钉钉 `gettoken` API 文档指定使用 `GET` 请求 (`https://oapi.dingtalk.com/gettoken?appkey=KEY&appsecret=SECRET`)，当前代码使用 `requests.post(url, params=...)`，参数虽通过查询字符串传递，但 HTTP 方法不匹配 |
| **风险** | 低。部分版本的钉钉 API 接受 POST 请求，但非标准用法可能在新版本中失效 |
| **修复** | 改为 `requests.get` |

```python
resp = requests.get(
    'https://oapi.dingtalk.com/gettoken',
    params={'appkey': cfg['app_key'], 'appsecret': cfg['app_secret']},
    timeout=15,
)
```

---

## 🟡 P1 — 建议修复

### ISSUE-3: `views_format.py` 不应使用 `@csrf_exempt`

| 维度 | 内容 |
|------|------|
| **文件** | `backend/apps/doc/views_format.py:api_format_code` |
| **问题** | `@csrf_exempt` 完全绕过 CSRF 保护。前端 `code-formatter.js` 实际已正确设置了 `X-CSRFToken` header，移除 `@csrf_exempt` 也能正常工作 |
| **修复** | 移除 `@csrf_exempt` 装饰器 |

### ISSUE-4: 批量通知补推无并发控制

| 维度 | 内容 |
|------|------|
| **文件** | `backend/apps/doc/auth/views.py:_backfill_wecom_notifications` |
| **问题** | 用户有大量未读通知(如 100+)时，`for notification in unread` 循环逐个发送企微 API 请求，无并发限制，串行耗时可能很长 |
| **建议** | 限制补推数量（如最近 20 条），或使用 `ThreadPoolExecutor` 并发发送 |

### ISSUE-5: `persistWidths` 无错误处理

| 维度 | 内容 |
|------|------|
| **文件** | `frontend/static/js/theme/table-resize.js:persistWidths` |
| **问题** | 列宽保存请求使用 `XMLHttpRequest` 但不监听 `onerror`，保存失败时用户无任何反馈。列宽看似已保存但实际未持久化 |
| **修复** | 添加 `xhr.onerror` 回调，失败时 `console.warn` |

### ISSUE-6: `code-formatter.js` 语言检测准确率低

| 维度 | 内容 |
|------|------|
| **文件** | `frontend/static/js/theme/code-formatter.js:detectLanguage` |
| **问题** | 使用简单的 `startsWith` 检测：`import` 可能是 Python、Go、Java 等；`class` 可能是 Python、Java、PHP 等。误判率高 |
| **建议** | 优先使用代码块的 `language-xxx` CSS class（已有此逻辑），内容检测仅作 fallback。当前实现正确，无需修改 |

---

## 🔵 P2 — 后续优化

### ISSUE-7: 表格列宽保存使用 XMLHttpRequest 而非 fetch

`table-resize.js` 的 `persistWidths` 和 `loadWidths` 使用 `XMLHttpRequest`，而项目中其他 AJAX 调用已统一使用 `fetch` API。建议统一为 `fetch`。

### ISSUE-8: `_backfill_wecom_notifications` 可能推送过多通知

如果用户长时间未读（如数百条通知），补推功能会调用数百次企微 API。建议限制最近 N 条（如 50 条）。

### ISSUE-9: `table-resize.js` 初始化未销毁 MutationObserver

MutationObserver 在页面卸载时未断开（`observer.disconnect()`），可能造成轻微内存泄漏。

---

## ⚪ 信息/确认 — 无需修复

### INFO-10: `api_load_table_widths` 的 `@login_required` 参数格式

```python
@login_required(login_url='/login/')
def api_load_table_widths(request, doc_id):
```
对比项目其他视图：
```python
@login_required()
def some_view(request):
```
参数格式不同但功能正常（`login_url` 参数有效）。风格不统一但不影响运行。

### INFO-11: `ForceDefaultLanguageMiddleware` 无条件激活语言

当 `LANGUAGE_FORCE=True` 时，中间件对每个请求都 `translation.activate()` + `deactivate()`。这是正确行为，无需优化。

---

## 修复行动计划

| 优先级 | Issue | 工作量 | 行动 |
|--------|-------|--------|------|
| 🔴 P0 | BUG-1: 缺少 login_required | 1 行 | 立即修复 |
| 🔴 P0 | BUG-2: 钉钉 API HTTP 方法 | 1 行 | 立即修复 |
| 🟡 P1 | ISSUE-3: 移除 csrf_exempt | 1 行 | 建议修复 |
| 🟡 P1 | ISSUE-5: persistWidths 错误处理 | 3 行 | 建议修复 |
| 🟡 P1 | ISSUE-4: 补推并发限制 | 5 行 | 建议优化 |
| 🔵 P2 | ISSUE-7/8/9 | 若干 | 后续迭代 |
