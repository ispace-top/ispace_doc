# 🗺️ 思维导图与流程图

>i **点击工具栏按钮或手动输入代码块。下方展示写法和渲染效果。**

## 1. 思维导图 (Mindmap)

**使用方式：用 ```mindmap 包裹以下 Markdown 列表**

```text
- 爱思文档
  - 前端
    - Vditor 编辑器
    - SPA 路由
  - 后端
    - Django 4.2
    - Whoosh 搜索
  - 部署
    - Docker
    - Nginx
```

**渲染效果：**

```mindmap
- 爱思文档
  - 前端
    - Vditor 编辑器
    - SPA 路由
  - 后端
    - Django 4.2
    - Whoosh 搜索
  - 部署
    - Docker
    - Nginx
```

## 2. 流程图 (Flowchart.js)

| 关键字 | 含义 |
|--------|------|
| st=>start: 标签 | 开始节点 |
| e=>end: 标签 | 结束节点 |
| op=>operation: 标签 | 操作步骤 |
| cond=>condition: 标签 | 条件判断 |

**使用方式：用 ```flowchart 包裹以下内容**

```text
st=>start: 开始
e=>end: 结束
op=>operation: 处理步骤
cond=>condition: 条件判断?
st->op->cond
cond(yes)->e
cond(no)->op
```

**渲染效果：**

```flowchart
st=>start: 开始
e=>end: 结束
op=>operation: 处理步骤
cond=>condition: 条件判断?
st->op->cond
cond(yes)->e
cond(no)->op
```
