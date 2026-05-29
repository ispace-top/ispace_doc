# 爱思文档 i·Space Doc UI 界面与交互设计文档

<h2 align="center">UI/UX Design Specification — v0.9.0-dev</h2>

---

## 目录

1. [设计理念与设计系统](#1-设计理念与设计系统)
   - 1.1 [设计原则](#11-设计原则)
   - 1.2 [Design Tokens](#12-design-tokens)
   - 1.3 [色彩体系](#13-色彩体系)
   - 1.4 [字体体系](#14-字体体系)
   - 1.5 [间距与网格系统](#15-间距与网格系统)
   - 1.6 [圆角与阴影](#16-圆角与阴影)
   - 1.7 [动效规范](#17-动效规范)
   - 1.8 [暗色模式](#18-暗色模式)
   - 1.9 [响应式断点](#19-响应式断点)
2. [全局布局与 Shell](#2-全局布局与-shell)
3. [组件库](#3-组件库)
4. [身份认证页面](#4-身份认证页面)
   - 4.1 [登录页](#41-登录页-login)
   - 4.2 [注册页](#42-注册页-register)
   - 4.3 [忘记密码页](#43-忘记密码页)
   - 4.4 [OIDC 认证流程](#44-oidc-认证流程)
   - 4.5 [企业微信扫码登录](#45-企业微信扫码登录)
   - 4.6 [LDAP 表单登录](#46-ldap-表单登录)
   - 4.7 [钉钉扫码登录](#47-钉钉扫码登录)
   - 4.8 [认证提供者动态加载](#48-认证提供者动态加载)
5. [首页（文档工作台）](#5-首页文档工作台)
6. [文档浏览页](#6-文档浏览页)
   - 6.1 [页面布局](#61-页面布局)
   - 6.2 [文档工具栏](#62-文档工具栏)
   - 6.3 [文档正文区域](#63-文档正文区域)
   - 6.4 [子文档展示区](#64-子文档展示区)
   - 6.5 [文档设置面板](#65-文档设置面板)
   - 6.6 [点赞交互](#66-点赞交互)
   - 6.7 [文档历史版本](#67-文档历史版本)
   - 6.8 [右侧大纲导航面板](#68-右侧大纲导航面板)
7. [文档编辑器](#7-文档编辑器)
8. [文档树侧边栏](#8-文档树侧边栏)
9. [个人中心](#9-个人中心)
10. [分组管理](#10-分组管理)
11. [组织架构管理](#11-组织架构管理)
12. [文档权限管理](#12-文档权限管理)
13. [评论系统](#13-评论系统)
14. [通知系统](#14-通知系统)
15. [全文搜索](#15-全文搜索)
16. [文档分享](#16-文档分享)
17. [文档导入导出](#17-文档导入导出)
18. [素材管理](#18-素材管理)
19. [API 开放平台](#19-api-开放平台)
20. [安装初始化引导](#20-安装初始化引导)
21. [管理后台](#21-管理后台)
22. [新增功能](#22-新增功能)
    - 22.1 [可视化绘图](#221-可视化绘图)
    - 22.2 [水印功能](#222-水印功能)
    - 22.3 [访问密码保护](#223-访问密码保护)
    - 22.4 [WebHook 管理](#224-webhook-管理)
    - 22.5 [认证配置管理](#225-认证配置管理)
    - 22.6 [系统健康监控增强](#226-系统健康监控增强)
    - 22.7 [关于我们页面](#227-关于我们页面)
23. [附录：CSS 命名规范与 Class 速查](#23-附录css-命名规范与-class-速查)

---

## 1. 设计理念与设计系统

### 1.1 设计原则

| 原则 | 说明 |
| ---- | ---- |
| **清晰优先** | 信息层级分明，操作路径最短。用户应在 2 步内触达核心功能 |
| **内容为王** | 文档内容是核心，UI 作为陪衬，减少装饰性元素占用视觉空间 |
| **一致性** | 所有页面遵循统一的间距、色彩、动效规则。同一交互在不同位置行为一致 |
| **即时反馈** | 每个操作必须有即时反馈（loading/成功/失败）。异步操作使用 Toast，同步操作用微交互 |
| **渐进呈现** | 常用功能直接可见，高级功能按需展开。默认显示最常用 3-4 个操作，更多收入"…"菜单 |
| **可访问性** | 符合 WCAG 2.1 AA 标准：键盘可操作、跳过导航链接、合理的色彩对比度（≥4.5:1 正文） |
| **移动端适配** | 768px 以下切换为单栏布局，侧边栏收起，工具栏精简 |
| **企业级体验** | 暖色调深色/亮色双主题，手写体 Logo，专业克制的动效，适配企业 VI 定制需求 |

### 1.2 Design Tokens

所有视觉属性通过 CSS 自定义属性（Design Tokens）统一管理，命名空间 `--ispace-`，格式 `--ispace-{category}-{property}[-{variant}]`。

**核心 Token 定义**（位于 `css/theme/tokens.css`）：

```css
:root {
  /* 字体 */
  --ispace-font-sans: 'Inter', 'PingFang SC', 'Hiragino Sans GB', -apple-system, ...;
  --ispace-font-mono: 'JetBrains Mono', 'SF Mono', 'Consolas', monospace;
  --ispace-font-xs: 0.75rem;
  --ispace-font-sm: 0.875rem;
  --ispace-font-base: 1rem;
  --ispace-font-lg: 1.125rem;
  --ispace-font-xl: 1.25rem;
  --ispace-font-2xl: 1.5rem;
  --ispace-font-3xl: 1.875rem;
  --ispace-font-4xl: 2.25rem;

  /* 间距 (8px grid) */
  --ispace-space-0: 0;       --ispace-space-1: 0.25rem;
  --ispace-space-2: 0.5rem;  --ispace-space-3: 0.75rem;
  --ispace-space-4: 1rem;    --ispace-space-5: 1.25rem;
  --ispace-space-6: 1.5rem;  --ispace-space-8: 2rem;
  --ispace-space-10: 2.5rem; --ispace-space-12: 3rem;
  --ispace-space-16: 4rem;   --ispace-space-20: 5rem;

  /* 圆角 */
  --ispace-radius-sm: 0.25rem;  --ispace-radius-md: 0.5rem;
  --ispace-radius-lg: 0.75rem;  --ispace-radius-xl: 1rem;
  --ispace-radius-full: 9999px;

  /* 阴影 */
  --ispace-shadow-xs: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --ispace-shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.1) ...;
  --ispace-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1) ...;
  --ispace-shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1) ...;
  --ispace-shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1) ...;

  /* Z-Index 层级 */
  --ispace-z-dropdown: 1000;  --ispace-z-sticky: 1020;
  --ispace-z-sidebar: 1030;   --ispace-z-modal-backdrop: 1040;
  --ispace-z-modal: 1050;     --ispace-z-toast: 1060;
  --ispace-z-tooltip: 1070;

  /* 动画 */
  --ispace-duration-fast: 150ms;   --ispace-duration-normal: 200ms;
  --ispace-duration-slow: 300ms;
  --ispace-ease-out: cubic-bezier(0, 0, 0.2, 1);

  /* 布局尺寸 */
  --ispace-header-height: 64px;
  --ispace-sidebar-width: 260px;
  --ispace-sidebar-collapsed-width: 64px;
  --ispace-content-max-width: 1200px;
  --ispace-doc-content-max-width: 860px;
}
```

### 1.3 色彩体系

#### 1.3.1 暖色调主题（默认 Light）

i·Space Doc 采用暖色调设计语言，以温暖的琥珀/橙色调替代传统冷蓝色调，营造知识管理平台的温馨、专注氛围。

| Token | 色值 | 用途 |
| ----- | ---- | ---- |
| `--ispace-color-surface-0` | `#ffffff` | 卡片、模态框背景 |
| `--ispace-color-surface-50` | `#faf8f5` | 表头、页面背景区 |
| `--ispace-color-surface-100` | `#f5f0eb` | Hover 态背景 |
| `--ispace-color-surface-200` | `#ebe3da` | 禁用态、分隔线 |
| `--ispace-color-text-primary` | `#1a1410` | 标题、正文 |
| `--ispace-color-text-secondary` | `#4a3f35` | 次要文本、表单标签 |
| `--ispace-color-text-tertiary` | `#7a6f65` | 辅助说明、时间戳 |
| `--ispace-color-text-quaternary` | `#a89888` | 占位符、禁用文本 |
| `--ispace-color-brand-500` | `#d4843a` | 主按钮、链接、选中态（暖橙色） |
| `--ispace-color-brand-600` | `#b8702e` | 按钮 Hover |

#### 1.3.2 语义状态色

| 状态 | 背景 Token | 文字 Token | 边框 Token |
| ---- | ---------- | ---------- | ---------- |
| Success | `success-bg: #d1fae5` | `success-text: #065f46` | `success-border: #10b981` |
| Warning | `warning-bg: #fef3c7` | `warning-text: #92400e` | `warning-border: #f59e0b` |
| Error | `error-bg: #fee2e2` | `error-text: #991b1b` | `error-border: #ef4444` |
| Info | `info-bg: #cffafe` | `info-text: #164e63` | `info-border: #06b6d4` |

#### 1.3.3 状态色使用规则

- **Error**：表单校验错误、删除确认按钮、Toast 错误提示
- **Warning**：调试模式 Banner、即将过期提醒、草稿状态
- **Success**：操作成功 Toast、发布状态标签
- **Info**：提示面板、功能引导
- 不混合使用语义色：一个组件内最多使用一种状态色

### 1.4 字体体系

| 层级 | 字号 | 字重 | 行高 | 用途 |
| ---- | ---- | ---- | ---- | ---- |
| H1 | 2.25rem (36px) | Bold 700 | 1.25 | 页面主标题 |
| H2 | 1.875rem (30px) | Bold 700 | 1.25 | 区块标题 |
| H3 | 1.5rem (24px) | Semibold 600 | 1.25 | 卡片标题 |
| H4 | 1.25rem (20px) | Semibold 600 | 1.25 | 小节标题 |
| Body | 1rem (16px) | Normal 400 | 1.5 | 正文内容 |
| Body-Small | 0.875rem (14px) | Normal 400 | 1.5 | 表单标签、表格内容、侧边栏 |
| Caption | 0.75rem (12px) | Normal 400 | 1.5 | 辅助说明、时间戳、Badge |

- **正文/UI 字体**：Inter → PingFang SC → Hiragino Sans GB → system-ui 降级链
- **代码字体**：JetBrains Mono → SF Mono → Consolas → monospace 降级链
- **标题字体**：思源宋体（Source Han Serif CN），仅用于文档正文标题，营造知识沉淀的庄重感
- **Logo 字体**：Ma Shan Zheng（站酷免费商用手写体），仅用于导航栏 Logo，不回退

### 1.5 间距与网格系统

- 基于 **8px 网格**：所有间距为 4px 的倍数（0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80px）
- **页面级垂直节奏**：相邻区块间距 ≥ 24px，相邻段落间距 16px
- **表单内间距**：标签与输入框间距 8px，表单组间距 16px

### 1.6 圆角与阴影

| 元素类型 | 圆角 | 说明 |
| -------- | ---- | ---- |
| 小型元素（Badge、Tag） | `radius-sm` (4px) | 小尺寸需要紧凑感 |
| 按钮、输入框、下拉菜单项 | `radius-md` (8px) | 标准交互元素 |
| 卡片、模态框、Panel | `radius-lg` (12px) | 容器型元素 |
| 头像、圆形按钮 | `radius-full` | 圆形 |

**阴影分配**：

- `shadow-xs`：默认卡片
- `shadow-sm`：Hover 卡片
- `shadow-md`：下拉菜单
- `shadow-lg`：拖拽元素、右键菜单（文档树拖拽使用 3D 投影 `0 8px 24px rgba(0,0,0,0.12)`）
- `shadow-xl`：模态框

### 1.7 动效规范

| 类型 | 时长 | 缓动函数 | 适用场景 |
| ---- | ---- | -------- | -------- |
| 微交互 | 150ms | `ease-out` | Hover 变色、Icon 旋转、Toggle |
| 标准过渡 | 200ms | `ease-out` | 面板展开/收起、Tab 切换、Fade In/Out |
| 入场动画 | 300ms | `ease-out` | 模态框打开、Toast 滑入、页面切换 |

**禁止**：
- 不使用弹跳（bounce）/弹性（spring）动效——保持专业克制
- 不在滚动列表中使用逐个入场 stagger 动画——影响性能
- 持续时长不超过 500ms 的加载动画使用骨架屏或旋转 Spinner

### 1.8 暗色模式

通过 `[data-ispace-theme="dark"]` 选择器覆盖全部 Design Token。实现策略：

- 所有颜色值定义在 Token 层，组件 CSS 只引用 Token 变量
- 切换时改变 `<html data-ispace-theme="dark|light|auto">`，无需重新渲染
- 切换按钮位于 Header 右侧：Sun/Moon 图标，点击三态循环 light → dark → auto
- 用户偏好存储于 `localStorage.ispace-theme`，跨会话保持
- `auto` 模式跟随系统 `prefers-color-scheme` 媒体查询
- FOUC 防护：`<head>` 内联同步脚本在 CSS 加载前设置 `data-ispace-theme` 属性

**暗色模式色板**（暖色调暗黑）：

| Token | 色值 | 用途 |
| ----- | ---- | ---- |
| `--ispace-color-surface-0` | `#1a1a1a` | 卡片、模态框背景 |
| `--ispace-color-surface-50` | `#212121` | 表头、页面背景区 |
| `--ispace-color-surface-100` | `#2a2a2a` | Hover 态背景 |
| `--ispace-color-surface-200` | `#333333` | 禁用态、分隔线 |
| `--ispace-color-text-primary` | `#e8e0d5` | 标题、正文 |
| `--ispace-color-text-secondary` | `#b0a595` | 次要文本 |
| `--ispace-color-brand-500` | `#e8943a` | 主按钮、链接（亮暖橙） |

### 1.9 响应式断点

| 断点 | 宽度 | 布局变化 |
| ---- | ---- | -------- |
| Desktop | ≥ 1025px | 完整双栏布局：侧边栏(260px) + 内容区 |
| Tablet | 769px ~ 1024px | 双栏布局，侧边栏可折叠，Header 搜索居中 |
| Mobile | ≤ 768px | 单栏布局：侧边栏隐藏，Header 精简，内容全宽 |
| Small Mobile | ≤ 480px | 按钮缩小，表单元素堆叠 |

**移动端适配策略**：

- 侧边栏默认隐藏，通过汉堡菜单按钮呼出（滑入 Overlay）
- 表格转为卡片列表（每行数据渲染为一张卡片）
- 模态框宽度调整为 `90vw`
- Toast 固定底部居中

---

## 2. 全局布局与 Shell

### 2.1 布局结构

```
┌──────────────────────────────────────────────────┐
│ Header (sticky, 64px)              [Logo] [···] [🔔] [👤] │
├────────────┬─────────────────────────────────────┤
│ Sidebar    │ Main Content                        │
│ (260px)    │ (max-width: 1200px, centered)      │
│            │                                     │
│ 📁 后端    │ ┌─────────────────────────────────┐ │
│  📄 Django │ │ Page Title                     │ │
│  📄 API    │ │                                 │ │
│ 📁 前端    │ │ Content Area                   │ │
│            │ │                                 │ │
│ [+ 新建]   │ └─────────────────────────────────┘ │
│            │                                     │
├────────────┴─────────────────────────────────────┤
│ Footer (三栏 Grid + 版权 + 版本号)                  │
└──────────────────────────────────────────────────┘
```

**CSS Grid 实现**：`grid-template-columns: 260px 1fr; grid-template-rows: 64px 1fr auto;`

### 2.2 Header（全局导航栏）

- **高度**：64px，sticky 吸顶，`z-index: 1020`
- **背景**：`surface-0`，底部 `1px solid border-light` 分隔
- **三段式布局**：
  - **Left**：Logo（手写体 "爱思文档" + 图标 28×28）→ 面包屑 → 页面标题
  - **Center**：搜索框（首页和文档浏览页显示，420px 最大宽度，带搜索图标）
  - **Right**：主题切换按钮 → 通知铃铛 → 用户下拉菜单
- **未登录态**：Right 区显示"登录"按钮（Ghost）+"注册"按钮（Primary）
- **移动端**（≤768px）：Center 区隐藏，Logo 字号缩小，按钮精简

#### 面包屑（Breadcrumb）

- 位置：Header Left 区，Logo 之后
- 格式：`首页 / 文档A / 文档B / 当前文档`
- 每级可点击，最后一级为纯文本（当前页）
- 分隔符使用 `/`（text-quaternary 颜色，无下划线）
- 宽度溢出时优先保留最后边的几级，前面的层级用 `...` 替换
- 面包屑使用 `inline-flex` 布局，内容自适应宽度，不拉伸填满容器

### 2.3 Footer

- 顶部 border 分隔
- 三栏 Grid：品牌描述(2fr) | 产品链接(1fr) | 资源链接(1fr)
  - 品牌描述：Logo + 简介文字 + 版本号
  - 产品链接：关于我们、使用文档、API 文档、更新日志
  - 资源链接：GitHub、问题反馈、开源协议
- 底部版权信息 + 版本号，居中，text-quaternary
- 移动端三栏堆叠为单栏

### 2.4 可访问性

- **跳过导航**：`<a href="#main-content" class="ispace-skip-link">` — 键盘 Tab 第一个元素，获得焦点时可见（蓝色边框 + 白色背景，左上角浮层）
- **语义化**：`<header>` `<nav>` `<main>` `<aside>` `<footer>` 正确使用
- **ARIA**：侧边栏 `aria-label="文档导航"`，通知铃铛 `aria-label="通知"`

---

## 3. 组件库

所有组件使用 `ispace-` 前缀的 CSS class，引用统一的 Design Token。

### 3.1 按钮 Button

| Class | 用途 | 样式 |
| ----- | ---- | ---- |
| `.ispace-btn` | 基础按钮 | 内联 flex，gap 8px，radius-md，transition 150ms |
| `.ispace-btn-primary` | 主操作 | Brand-500 背景，白色文字，hover 加深至 brand-600 |
| `.ispace-btn-secondary` | 次要操作 | 白色背景，border-medium 边框，hover 浅灰背景 |
| `.ispace-btn-ghost` | 无边框操作 | 透明背景，hover 浅灰背景 |
| `.ispace-btn-danger` | 危险操作 | Error-text 背景，白色文字 |
| `.ispace-btn-sm` | 小按钮 | padding 4px 12px，font-xs |
| `.ispace-btn-lg` | 大按钮 | padding 12px 24px，font-base |
| `.ispace-btn-icon` | 纯图标按钮 | 36×36px 正方形，居中。小号 28×28px |
| `.ispace-btn-outline` | 轮廓按钮 | 透明背景，brand-500 边框和文字，hover 浅品牌色背景 |

**Disabled 态**：`opacity: 0.5; cursor: not-allowed;`

### 3.2 表单 Form

| Class | 说明 |
| ----- | ---- |
| `.ispace-form-group` | 表单组容器，`margin-bottom: 16px` |
| `.ispace-form-label` | 标签，`font-sm`，`font-medium`，`text-secondary` |
| `.ispace-form-label-required` | 必填标记，`::after { content: ' *'; color: error-border }` |
| `.ispace-form-input` | 文本输入框，全宽，padding 8px 12px，border-medium，radius-md |
| `.ispace-form-textarea` | 多行文本，`min-height: 100px`，`resize: vertical` |
| `.ispace-form-select` | 下拉选择，样式同 input |
| `.ispace-form-hint` | 提示文字，`font-xs`，`text-quaternary` |
| `.ispace-form-error-text` | 校验错误文字，`font-xs`，`error-text`，默认隐藏 |

**Focus 态（统一）**：`outline: none; border-color: brand-500; box-shadow: 0 0 0 3px brand-100`

**Error 态**：`border-color: error-border; focus: box-shadow: 0 0 0 3px error-bg`

### 3.3 表格 Table

- `.ispace-table`：全宽，`border-collapse: collapse`，radius-lg 圆角容器，overflow hidden
- `thead`：surface-50 背景，th 字号 font-xs uppercase
- `tbody tr`：底部 border-light 分隔，hover 态 surface-hover 背景
- `.ispace-selected` tr：brand-50 背景
- 最后一行的 `td` 无底部 border

### 3.4 卡片 Card

- `.ispace-card`：surface-0 背景，border-light 边框，radius-lg，shadow-xs，hover 时 shadow-sm
- `.ispace-card-header`：flex space-between，底部 border，内含 card-title（font-base semibold）
- `.ispace-card-body`：padding 24px
- `.ispace-card-footer`：顶部 border

### 3.5 徽章 Badge

| Class | 颜色 |
| ----- | ---- |
| `.ispace-badge` | 基础：inline-flex，font-xs，font-medium，padding 0 8px，radius-sm |
| `.ispace-badge-primary` | brand-100 背景 / brand-700 文字 |
| `.ispace-badge-success` | success-bg / success-text |
| `.ispace-badge-warning` | warning-bg / warning-text |
| `.ispace-badge-error` | error-bg / error-text |
| `.ispace-badge-info` | info-bg / info-text |

### 3.6 模态框 Modal

- `.ispace-modal-backdrop`：固定定位全屏，半透明黑色遮罩（`rgb(0 0 0 / 0.5)`），opacity 过渡动画
- `.ispace-modal`：surface-0 背景，radius-lg，shadow-xl，flex column 布局
- 尺寸：`.ispace-modal-sm` (400px) / `.ispace-modal-md` (560px) / `.ispace-modal-lg` (720px) / `.ispace-modal-xl` (960px)
- `.ispace-modal-header`：flex，标题（font-lg semibold）+ 关闭按钮（32×32 圆形 X 图标）
- 打开/关闭动画：300ms opacity + scale 过渡

### 3.7 Toast 通知

- 容器：`#toast-container`，fixed，右上角（移动端底部居中），z-toast
- 单条 Toast：max-width 380px，padding 16px，radius-lg，shadow-lg，flex 布局（图标 + 文字 + 关闭按钮）
- 类型：Success（绿色左边框）/ Error（红色左边框）/ Warning（黄色左边框）/ Info（蓝色左边框）
- 入场：从右侧滑入 + fade in，300ms
- 自动消失：Success/Info 3s，Warning 5s，Error 需手动关闭
- JS API：`showSuccess(msg)`, `showError(msg)`, `showWarning(msg)`, `showInfo(msg)`

### 3.8 加载状态 Loading

| 场景 | 方案 |
| ---- | ---- |
| 页面初始加载 | 居中 Spinner + "加载中..." |
| 按钮提交中 | 按钮文字替换为 Spinner + "提交中..."，按钮 disabled |
| 列表加载更多 | 底部 Spinner，滚动触发 |
| 局部刷新 | 区域覆盖半透明 Spinner（不遮挡已有内容） |
| 骨架屏 | 首页卡片列表和文档列表首次加载使用灰色占位块（带 shimmer 动画） |

### 3.9 空状态 Empty State

- 居中布局：图标（40-60px，text-quaternary 颜色）+ 标题 + 描述文字 + CTA 按钮
- 图标选用与上下文相关的 SVG（文档图标、文件夹图标等）
- 描述文字建议下一步操作，而非仅仅"暂无数据"
- 示例：首页无文档时 — "当前没有可查看的文档" + "创建第一个文档"按钮

### 3.10 右键上下文菜单 Context Menu

- 固定定位（`position: fixed`），`z-index: 1100`
- min-width 170px，surface-0 背景，border-medium 边框，radius-lg，shadow-lg
- 菜单项：flex 布局，图标(14px) + 文字(font-sm)，padding 8px 12px，hover 态 surface-100 背景
- 危险操作项（如删除）：文字使用 error-text 颜色，hover 态 error-bg 背景
- 点击菜单外部或 Esc 键关闭
- 位置自适应：超出视窗时向左/向上调整

### 3.11 Toggle 开关

- `.ispace-toggle`：inline-flex，width 44px，height 24px，radius-full
- 关闭态：surface-200 背景，圆形滑块居左
- 开启态：brand-500 背景，圆形滑块居右
- 过渡：200ms ease-out
- 用于通知设置、认证配置启用/禁用等场景

### 3.12 密码输入框

- `.ispace-input-password`：在标准 input 基础上，右侧添加显示/隐藏密码切换按钮（眼睛图标）
- 点击切换 `type="password"` ↔ `type="text"`
- 适用于登录、注册、LDAP 登录等密码输入场景

---

## 4. 身份认证页面

### 4.1 登录页 Login

**URL**：`/login/`

**布局**：全屏暖色渐变背景 + 居中白色卡片。支持多认证方式统一入口。

```
┌──────────────────────────────────────────┐
│         [Header: Logo 爱思文档 · 思泉汹涌]   │
│                                          │
│      ┌──────────────────────┐           │
│      │     🔵 Logo           │           │
│      │                      │           │
│      │  登录到 爱思文档       │           │
│      │  使用您的账户访问...    │           │
│      │                      │           │
│      │  [用户名输入框]        │           │
│      │  [密码输入框 👁]       │           │
│      │  [验证码] [图片]       │ (条件)     │
│      │                      │           │
│      │  [  → 登 录  ]        │           │
│      │                      │           │
│      │  ─── 或使用以下方式登录 ─── │       │
│      │                      │           │
│      │  [OIDC 单点登录]       │ (条件)     │
│      │  [企业微信扫码]        │ (条件)     │
│      │  [LDAP 域账号登录]     │ (条件)     │
│      │  [钉钉扫码登录]        │ (条件)     │
│      │                      │           │
│      │  注册新账户 · 忘记密码  │           │
│      │  返回首页              │           │
│      └──────────────────────┘           │
└──────────────────────────────────────────┘
```

**卡片规格**：
- 宽度：max-width 420px，padding 40px，radius-xl，shadow-xl
- Logo：60×60px 圆形 Brand 背景 + 白色 SVG 图标
- 标题："登录到 爱思文档"（font-2xl semibold）
- 副标题："使用您的账户访问知识管理平台"（font-sm text-tertiary）

**表单字段**：
- 用户名：text input，placeholder "请输入用户名"
- 密码：password input（带显示/隐藏切换），placeholder "请输入密码"
- 验证码（条件渲染，`enable_login_check_code == 'on'` 时显示）：text input + 图片（120×40px，点击刷新）

**按钮**：全宽 Primary，"登录"，带 SVG 箭头图标

**OAuth 按钮区**（border-top 分隔，标题"或使用以下方式登录"）：
- 每个已启用的认证方式渲染一个 OAuth 按钮（全宽 outline 样式，品牌图标 + 文字）
- redirect 类型（OIDC/企业微信/钉钉）：点击跳转到 `/auth/<provider>/login/`
- form 类型（LDAP）：点击弹出 LDAP 登录模态框（见 4.6）

**错误态**：表单上方显示 Error Banner（error-bg 背景，error-text 文字，error-border 左边框）

**链接区**（border-top 分隔）：
- 注册新账户（条件渲染，`close_register != 'on'`）
- 忘记密码（条件渲染，`enable_email == 'on'`）
- 返回首页

**交互**：表单通过 AJAX 提交（fetch POST），成功后刷新页面（由服务端 Session 接管）；失败后显示错误 Banner。

### 4.2 注册页 Register

**URL**：`/register/`

**布局**：与登录页一致（复用 `auth-page` 样式）

**表单字段**：
- 用户名（5-20 位字母数字，大小写不敏感唯一）
- 邮箱
- 密码（≥6 位，带显示/隐藏切换）
- 确认密码
- 邀请码（条件渲染，`close_register == 'on'` 时显示"暂不开放注册"）

**校验**：
- 实时前端校验：用户名格式、两次密码一致性、邮箱格式
- 失焦（blur）校验：用户名唯一性 AJAX 检查
- 错误文字显示在对应字段下方

### 4.3 忘记密码页

**URL**：`/forget_pwd/`

**布局**：与登录页一致

**步骤一**：输入邮箱 → 发送验证码 → 提示"验证码已发送至您的邮箱"

**步骤二**：输入邮箱 + 验证码 + 新密码 + 确认密码 → 重置密码

**交互**：发送验证码按钮 60 秒冷却倒计时

### 4.4 OIDC 认证流程

**支持 IdP**：Keycloak / Auth0 / Azure AD / Okta / 其他标准 OIDC Provider

**交互流程**：
1. 用户在登录页点击 "OIDC 单点登录" 按钮
2. 浏览器跳转到 `/auth/oidc/login/` → 302 重定向到 IdP 授权页面
3. 用户在 IdP 完成认证 → IdP 回调 `/auth/oidc/callback/`
4. 后端验证 id_token + 获取 userinfo → 匹配或创建本地用户 → 建立 Session
5. 跳转到首页

**按钮样式**：全宽 outline 按钮，左侧 OIDC 图标（盾牌 SVG），文字显示 `config.ini` 中配置的 `provider_name`

### 4.5 企业微信扫码登录

**交互流程**：
1. 用户在登录页点击 "企业微信扫码登录" 按钮
2. 跳转到 `/auth/wecom/login/` → 302 重定向到企业微信 OAuth 授权页
3. 用户在企业微信 App 中扫码确认
4. 回调 `/auth/wecom/callback/` → 匹配 `wecom_userid` 或创建用户 → 建立 Session

**免登支持**（企业微信自建应用内）：
- 通过 `code` 参数调用 `/auth/wecom/sso/` 实现免密登录
- 前端检测是否在企业微信环境中，自动触发免登流程

**按钮样式**：全宽 outline 按钮，左侧微信图标（绿色聊天气泡 SVG），文字 "企业微信扫码登录"

### 4.6 LDAP 表单登录

用户在登录页可直接输入 LDAP 凭据认证。

**触发方式**：登录页点击 "LDAP 域账号登录" 按钮 → 弹出 LDAP 登录模态框

**模态框布局**（`.ispace-modal-sm`，宽度 400px）：

```
┌─────────────────────────────────┐
│  LDAP 域账号登录           [✕]  │
├─────────────────────────────────┤
│                                 │
│  使用企业 LDAP / AD 账号登录      │
│                                 │
│  用户名                         │
│  ┌─────────────────────────┐   │
│  │ 请输入域账号              │   │
│  └─────────────────────────┘   │
│                                 │
│  密码                           │
│  ┌─────────────────────────┐   │
│  │ 请输入密码           👁   │   │
│  └─────────────────────────┘   │
│                                 │
│  [ 登 录 ]                      │
│                                 │
└─────────────────────────────────┘
```

**交互**：
- AJAX POST `/auth/ldap/login/form/` 提交认证
- 支持两种 LDAP 绑定模式：
  - **搜索模式**：先用 `bind_dn` 绑定 → 搜索用户 DN → 用用户 DN + 密码重新绑定
  - **直接绑定模式**：用配置的 DN 模板（如 `uid=%(user)s,ou=users,dc=example,dc=com`）直接替换 %(user)s 后绑定
- 成功后关闭模态框 → 刷新页面
- 失败后显示错误信息（如"账号或密码错误"、"LDAP 服务器不可用"）

### 4.7 钉钉扫码登录

**交互流程**：
1. 用户在登录页点击 "钉钉扫码登录" 按钮
2. 跳转到 `/auth/dingtalk/login/` → 302 重定向到钉钉 OAuth 授权页
3. 用户在钉钉 App 中扫码确认
4. 回调 → 匹配或创建用户 → 建立 Session

**按钮样式**：全宽 outline 按钮，左侧钉钉图标，文字 "钉钉扫码登录"

### 4.8 认证提供者动态加载

- 页面加载时异步 fetch `GET /auth/providers/` 获取已启用的认证方式列表
- 根据返回的 providers 动态渲染 OAuth 按钮区
- 若仅本地密码启用，不显示"或使用以下方式登录"分割线
- 若所有第三方认证禁用，隐藏整个 OAuth 按钮区

---

## 5. 首页（文档工作台）

**URL**：`/`

### 5.1 未登录首页

**Hero 欢迎区域**：
- 居中布局，内容垂直居中于视口
- Logo（80×80px）+ "爱思文档"（font-4xl，手写体）+ 副标题 "思泉汹涌，智慧流淌"（font-lg text-tertiary）
- 搜索框（420px，居中）+ "搜索文档..."
- 两个 CTA 按钮：["开始使用"（Primary）] ["了解更多"（Ghost）]

### 5.2 已登录首页

```
┌──────────────────────────────────────────────┐
│ Header: [Logo 爱思文档 思泉汹涌...] [🔍 搜索] [🌙🔔👤] │
├────────────┬─────────────────────────────────┤
│ Sidebar    │ 筛选排序栏                       │
│ (文档树)    │ 收藏 | 最新 ↓ | 分类 ↓           │
│            │ ─────────────────────────────── │
│ 📁 文档A    │ ┌─────┐ ┌─────┐ ┌─────┐ ┌────┐ │
│  📄 子文档  │ │卡片1│ │卡片2│ │卡片3│ │卡片4│ │
│  📄 子文档2 │ └─────┘ └─────┘ └─────┘ └────┘ │
│ 📁 文档B    │ ┌─────┐ ┌─────┐ ┌─────┐ ┌────┐ │
│ [+ 新建]    │ │卡片5│ │卡片6│ │卡片7│ │卡片8│ │
│            │ └─────┘ └─────┘ └─────┘ └────┘ │
│            │                                  │
│            │ 最近浏览                           │
│            │ ┌──────────────────────────────┐ │
│            │ │ 文档名称  作者  更新时间       │ │
│            │ └──────────────────────────────┘ │
│            │                                  │
│            │ 继续编辑（草稿）                    │
│            │ ┌──────────────────────────────┐ │
│            │ │ 文档名称    最后修改时间  草稿  │ │
│            │ └──────────────────────────────┘ │
└────────────┴─────────────────────────────────┘
```

### 5.3 筛选排序栏

- 左侧：标签 "最近收藏"（font-base semibold）
- 右侧下拉（自定义 select，原生 select 透明覆盖在标签文字上）：
  - 排序：最新 / 最早 / 最多文档
  - 分类：全部 / 公开 / 访问码 / 私密（需登录）

### 5.4 收藏卡片网格（Recent Favorites）

- **布局**：横向可滚动网格（`grid-auto-flow: column`，2 行，每卡片 220px 宽）
- 超出可视区时显示左右滚动箭头按钮（36px 圆形，带阴影）
- **卡片样式**：
  - surface-0 背景，border-light，radius-lg，padding 12px 16px
  - hover 态：border-brand-300，shadow-md，上移 2px
  - 内容：图标(32×32px，brand-50 背景圆角方块) + 标题(font-sm semibold，溢出省略)
  - 类型 Badge（"文档"，10px 字号，surface-200 背景）

**响应式**（≤768px）：网格改为单列纵向排列，隐藏滚动按钮

### 5.5 最近浏览列表（Recently Viewed）

**数据加载**：AJAX 动态加载（`GET /api/user/browse-history/?page=N&page_size=50`），不再服务端渲染。加载完成后显示 section，空数据时隐藏整个 section。

**滚动加载**：IntersectionObserver 监听 loading 指示器，距视口 100px 时自动加载下一页。全部加载完毕后显示"— 没有更多了 —"。

**共享模块**：`RecentViews.init()`（`frontend/static/js/recent-views.js`），首页和个人中心复用同一逻辑，仅 `renderItem` 回调不同。

**列表项**（`home-doc-card`）：
- flex 布局：文件图标(18px) + 标题 + 作者(带头像图标) + 时间
- surface-0 背景，hover 态 surface-50
- 1px gap 模拟分隔线效果
- 点击整行跳转到文档

### 5.6 空状态

- 居中大图标（文档 SVG，48px）+ "暂无文档" + "当前没有可查看的文档"
- 已登录：显示"创建第一个文档"按钮（Primary）
- 未登录：显示"登录后创建文档"链接

### 5.7 行内创建工作流（Inline Create）

通过 URL 参数 `?create=1` 触发，或点击空状态按钮触发：

1. 首页内容区隐藏（`display:none`）
2. 同位置渲染行内编辑器（inline_editor.html）
3. 编辑器上方显示：标题输入框 + 父文档选择器
4. 提交按钮创建文档，成功后跳转到新建的文档页
5. 取消按钮：如有未保存修改，弹出确认对话框

### 5.8 "继续编辑"草稿区块

在"最近浏览"列表下方展示当前用户的待续草稿，帮助用户快速回到未完成的文档。

- **数据来源**：`GET /api/user/my-drafts/`（按 `modify_time` 倒序，最多 5 条）
- **区块样式**：与"最近浏览"相同的列表式布局，复用 `.home-doc-card` 卡片组件
- **卡片内容**：文档图标 + 文档名称 + 最后修改时间 + 黄色"草稿"角标
- **点击行为**：跳转到文档编辑页（`/docs/<doc_id>/?edit=1`）
- **空状态**：无草稿时整个区块隐藏（`style="display:none"`，JS 异步加载后控制显隐）

---

## 6. 文档浏览页

**URL**：`/docs/<doc_id>/`

### 6.1 页面布局

```
┌──────────────────────────────────────────────────────┐
│ Header: Logo > 父文档 > 当前文档                        │
├────────────┬─────────────────────────┬───────────────┤
│ Sidebar    │                         │ 大纲面板收起态 │
│ (文档树)    │    # 文档标题 (H1)        │  ┌──┐        │
│            │  👤 作者 · 🕐 更新时间      │  │目│        │
│ 当前文档高亮 ├─────────────────────────┤  │  │        │
│            │                         │  │录│        │
│            │ 文档正文内容 (max 860px)   │  └──┘        │
│            │                         │              │
│            │ ─────────────────────── │              │
│            │ 👍 点赞 (N)  💬 回复     │              │
│            │ ─────────────────────── │              │
│            │ 子文档列表               │              │
│            │ ─────────────────────── │              │
│            │ 评论区                   │              │
└────────────┴─────────────────────────┴───────────────┘
```

### 6.2 文档工具栏（Doc Toolbar）

标题栏采用两栏布局（标题区 + 操作按钮），`align-items: center` 垂直居中对齐。标题居中显示，作者/日期等元信息以 `.ispace-doc-header-meta-row` 水平居中排列在标题下方。

**元信息行**：👤 作者名称（可点击弹出作者卡片）+ 🕐 更新时间 + 🏷 标签列表（如有），各 meta 之间用 `·` 分隔

**Right 操作按钮**：
- 历史版本按钮（仅文档作者/管理员可见）
- 收藏按钮（星形图标，实心/空心切换）
- 编辑按钮（仅文档作者/创建者/管理员可见）
- 分享按钮
- 设置按钮（齿轮图标，仅文档作者/管理员可见）

**作者卡片（Author Card）**：点击作者名称触发（通过 `data-user-id` 属性匹配），弹出小卡片（width 280px），包含头像(48px) + 用户名 + 个性签名(bio) + 统计(文档数/收藏数) + 最后活跃时间。

### 6.3 文档正文区域

- **最大宽度**：860px（`--ispace-doc-content-max-width`），居中
- **标题**：H1 样式（font-4xl bold text-primary），margin-bottom: 24px
- **Markdown 内容**：marked.js 渲染，marked.css 样式
- **Vditor 所见即所得**：直接展示 `content` HTML
- **iceEditor 富文本**：直接展示 `content` HTML，经 DOMPurify 净化
- **表格**：Luckysheet 渲染

**内容样式（marked.css 提供）**：
- 代码块：暗色背景（`#1e1e1e`），等宽字体，语法高亮（Prism.js）
- 表格：border-collapse，斑马纹（偶数行 surface-50）
- 引用块：左边框 4px brand-200 + 浅灰背景
- Callout 提示块：彩色边框 + 背景 + CSS 伪元素图标
- 任务列表：checkbox 样式（accent-color: brand-500）
- 图片：最大宽度 100%，支持 Viewer.js 点击放大

**水印显示**：
- 文档启用水印时（`is_watermark=True`），在正文区域显示水印
- 水印内容：用户自定义文本或默认用户名
- 水印样式：重复平铺，透明度 0.06-0.1，不影响阅读
- 通过 CSS `pointer-events: none` 确保水印不干扰文字选择

### 6.4 子文档展示区

- 条件渲染：`doc.show_children == True`
- 列表样式：图标 + 文档标题 + 修改时间
- 标题 "子文档"（H3）

### 6.5 文档设置面板（Doc Settings）

点击工具栏齿轮图标触发，Modal 形式（`ispace-modal-md`），包含以下 Tab：

| Tab | 内容 |
| --- | ---- |
| 基本信息 | 文档标题编辑、状态切换（草稿/发布）、排序值设置 |
| 权限管理 | 用户/分组/组织节点三级权限表格：添加授权、撤销授权（详见 §12） |
| 标签管理 | 已关联标签列表 + 新建标签输入 + 删除标签 |
| 水印设置 | 启用水印开关 + 水印类型（文字/图片）+ 水印内容输入 |
| 访问控制 | 公开/私密切换 + 访问密码设置（is_public + access_password） |
| 分享设置 | 创建/管理分享链接（详见 §16） |
| 历史版本 | 版本列表（时间线），查看/对比/回滚（详见 §6.7） |
| 危险操作 | 删除文档按钮（需二次确认，有子文档时需图形验证码校验） |

### 6.6 点赞交互

- 点赞按钮：心形图标（SVG），未赞空心，已赞实心红色
- 点击：已登录即时切换（optimistic UI），未登录跳转登录页
- 点赞数实时更新
- 异步 fetch POST `/doc_like/`，失败时回滚状态 + showError

### 6.7 文档历史版本

**入口**：文档设置 Modal → 历史版本 Tab

**版本列表**：
- 时间线布局：左侧竖线 + 时间节点圆点
- 每条记录：创建时间(相对时间 "3 小时前") + 操作人 + "查看" / "对比" 按钮

**版本对比（Diff）**：
- URL：`/diff_doc/<doc_id>/<history_id>/`
- 左右双栏对比：左侧=旧版本，右侧=当前版本
- 差异高亮：绿色背景=新增，红色背景=删除

**回滚操作**：
- 仅限文档管理员
- 点击"回滚到此版本"→ 确认对话框 → 创建新历史记录后覆盖当前内容

### 6.8 右侧大纲导航面板

在文档浏览页右侧提供可收起的文档大纲导航面板（Outline Navigation Panel），展现文档标题层级结构，支持快速章节跳转与滚动位置跟踪。

**数据来源**（v1.0）：文档保存时服务端预生成大纲 JSON（`Doc.outline` 字段），通过模板变量传入前端 `window.__docOutline`。旧文档未重新保存时降级到客户端 DOM 扫描，确保兼容。

#### 6.8.1 收起态设计

- **外观**：固定于页面右侧边缘的窄竖直标签条（宽度 36px，高度 100px，圆角 8px）
- **位置**：`position: fixed; right: 6px; top: 50%; transform: translateY(-50%); z-index: 400`
- **背景**：`surface-0` 白色背景，`border: 1px solid border-light`，`box-shadow: 0 2px 8px rgba(0,0,0,0.08)`
- **文字**：竖向排列"目 录"两字，使用 `<br>` 换行实现竖排效果，字号 12px，字间距 2px
- **图标**：文字上方放置目录列表 SVG 图标（18×18px）
- **透明度**：默认 `opacity: 0.6`，hover 时 `opacity: 1.0` + `transform: translateY(-50%) scale(1.05)`

#### 6.8.2 展开态设计

**面板规格**：

| 属性 | 值 |
| ---- | --- |
| 宽度 | 260px |
| 高度 | `calc(100vh - 64px)`，与 Header 对齐 |
| 位置 | `position: fixed; right: 0; top: 64px; z-index: 450` |
| 背景 | `surface-0`，左侧 `border-left: 1px solid border-light` |
| 内容区滚动 | 隐藏滚动条（`scrollbar-width: none`） |

**面板头部**："目录"图标 + "目录" 标题 + 收起按钮（X 图标）

**大纲列表条目**：
- `<button>` 块级按钮，`width: 100%`，`text-align: left`
- H1-H6 层级缩进：16/28/44/60/76/92px
- 激活态：左侧 3px 蓝色指示条 + 品牌色文字 + 浅蓝背景
- Hover 态：背景 `surface-100`，文字颜色加深

**滚动条同步与激活指示**：
- IntersectionObserver 监听正文标题元素
- 激活条目自动滚动到面板可视区中间
- 顶部和底部 sticky 渐变遮罩提示内容可滚动

#### 6.8.3 动画规范

| 动画 | 时长 | 缓动函数 | 说明 |
| ---- | ---- | -------- | ---- |
| 面板展开 | 250ms | `cubic-bezier(0.4, 0, 0.2, 1)` | 从右侧滑入 |
| 面板收起 | 250ms | `cubic-bezier(0.4, 0, 0.2, 1)` | 滑出至右侧 |
| 条目交互 | 120ms | ease | 背景色和文字颜色过渡 |
| 标签条 hover | 150ms | ease | opacity、transform、box-shadow 过渡 |

---

## 7. 文档编辑器

**支持 3 种编辑器模式**：

| 模式 | 编辑器 | 说明 |
| ---- | ------ | ---- |
| 2 | Vditor（默认） | 现代 Markdown IR 所见即所得 |
| 3 | iceEditor | 富文本编辑器 |
| 4 | Luckysheet | 在线电子表格 |

> 模式 1（Editormd）已废弃，不再在 UI 中显示为可选选项。

### 7.1 创建文档页

**URL**：`/docs/<parent_doc>/?create_child=1` 或首页 `?create=1`

**页面布局**（`create_doc.html`）：

```
┌──────────────────────────────────────────┐
│ Header: Logo > 父文档名                    │
│   [Vditor ▼ 编辑器切换]                    │
├──────────────────────────────────────────┤
│ 标题输入框：[                    ] [草稿/已发布] │
│ [保存草稿] [发布] [从模板创建]              │
│                                          │
│ 编辑器区域（全宽）                          │
│ ┌──────────────────────────────────────┐ │
│ │ Toolbar: emoji headings bold italic  │ │
│ │ strike | quote code link | list      │ │
│ │ ordered-list check 表格 | 思维导图    │ │
│ │ 流程图 手绘图 图表 | 图片 附件 |       │ │
│ │ outline undo redo | fullscreen 预览   │ │
│ ├──────────────────────────────────────┤ │
│ │                                      │ │
│ │ 编辑区域（Markdown IR / 富文本 / 表格）   │ │
│ │                                      │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ 标签：[          ]  [添加]               │
│ 排序：[9999]                              │
│ [已保存草稿 HH:MM:SS]                      │
│ [展开子目录] [显示子文档]                   │
└──────────────────────────────────────────┘
```

**状态角标**：标题输入框右侧显示文档状态角标（`_updateDocStatusBadge(status)` 控制）：
- `status=0`（草稿）：黄色背景 + 黄色文字，文字"草稿"
- `status=1`（已发布）：绿色背景 + 绿色文字，文字"已发布"

**双按钮交互逻辑**：
- **新建模式**（`?create=1`）：同时显示"保存草稿"（outline 样式）和"发布"（primary 样式）
- **已发布文档编辑模式**：仅显示"保存草稿"按钮，角标显示"已发布"
- **草稿文档编辑模式**：仅显示"发布"按钮，角标显示"草稿"

**"从模板创建"按钮**：仅新建模式显示，点击弹出模板选择器。

**编辑器切换**：
- 导航栏下拉菜单：Vditor / 富文本 / 在线表格
- 当前选中的编辑器前方有蓝色圆点指示器
- 切换时保留已输入内容（支持 Markdown ↔ HTML 转换）

### 7.2 修改文档页

**URL**：`/docs/<doc_id>/?edit=1`

**布局**：与创建页一致，预填充现有内容

**差异**：
- 编辑器预加载文档现有内容
- 编辑器下方显示文档元信息：标签、排序、状态
- 显示"文档历史"按钮
- 提交按钮："保存"（更新现有文档）

### 7.3 Callout 块渲染

Vditor IR 模式下，对符合以下前缀的 blockquote 自动渲染为 Callout 提示块：

| 前缀 | callout 类型 | 边框色 | 图标来源 |
| ---- | ------------ | ------ | -------- |
| `i` / `info` | info (信息) | `#0969da` | CSS ::before |
| `w` / `warning` | warning (提醒) | `#f0ad4e` | CSS ::before |
| `e` / `error` | danger (关键) | `#d9534f` | CSS ::before |
| `s` / `success` | success (关注) | `#50af51` | CSS ::before |
| `t` / `tip` | tip (技巧) | `#6f42c1` | CSS ::before |

图标通过 CSS 伪元素 `blockquote.xxx > p:first-child::before` 渲染，不向 DOM 注入 HTML 元素，避免 Lute IR→MD 序列化破坏 Markdown 结构。

### 7.4 ECharts 图表插入

工具栏"图表"按钮点击弹出下拉菜单，支持 6 种图表类型：

| 图表类型 | 说明 |
| -------- | ---- |
| 柱状图 (bar) | 分类对比柱状图 |
| 折线图 (line) | 时间序列折线图 |
| 饼图 (pie) | 占比分析饼图 |
| 散点图 (scatter) | 相关性散点图 |
| 雷达图 (radar) | 多维指标雷达图 |
| 仪表盘 (gauge) | 进度仪表盘 |

插入格式：```` ```echarts { "title": ... } ``` ````

### 7.5 表格插入与编辑

**表格插入弹窗**：行数（2-20）+ 列数（1-15）→ 生成 Markdown 表格

**表格浮动操作工具栏**（IR 模式下点击表格单元格触发）：
```
[上方插入行] [下方插入行] | [左侧插入列] [右侧插入列] | [删除当前行] [删除当前列] | [删除表格]
```

### 7.6 编辑器自动缓存

- 每 10 秒自动保存编辑器内容到 `localStorage.isdoc_doc_cache`
- 页面意外关闭后重新进入时，检测缓存 → 弹出恢复对话框
- 文档成功提交后自动清除缓存

### 7.7 图片上传

- 支持拖拽上传和粘贴上传（Ctrl+V 粘贴剪贴板图片）
- 支持 URL 图片插入（自动下载并替换为本地路径）
- 上传进度条（Vditor 原生支持）
- 支持格式：jpg, jpeg, gif, png, bmp, webp, tiff（`config.ini` 可配置）

### 7.8 文档模板

模板功能提供"从模板创建"模态框，在新建文档时一键套用。管理入口在个人中心 → 文档模板 Tab。

**模板选择器模态框**（宽度 560px）：
- 卡片网格展示用户的所有模板
- 每卡片：模板名称 + 创建时间 + "使用此模板"按钮
- 空状态引导："暂无模板，请在个人中心 → 文档模板中创建"
- 点击"使用此模板"→ 加载模板内容到编辑器 → 关闭模态框

### 7.9 快捷键

| 快捷键 | 操作 |
| ------ | ---- |
| `Ctrl+S` / `Cmd+S` | 保存草稿 |
| `Ctrl+Shift+S` / `Cmd+Shift+S` | 发布文档 |
| `Ctrl+P` / `Cmd+P` | 打印 |
| `Esc` | 关闭模态框 / 取消编辑 |

---

## 8. 文档树侧边栏

### 8.1 侧边栏布局

- **宽度**：260px（可折叠至 64px）
- **位置**：sticky，top: 64px（Header 高度），height: calc(100vh - 64px)
- **滚动**：overflow-y: auto（垂直超出时），overflow-x: auto（水平超出时）
- **背景**：surface-0，右侧 border-light 分隔

### 8.2 折叠按钮

- 位置：侧边栏右侧边缘，20×44px 标签式按钮，右偏移 -8px 贴边
- 图标：`<` 箭头（折叠后旋转 180° 变为 `>`）
- 默认 opacity 0.35，hover 时 1.0
- 折叠态：宽度变为 64px，隐藏所有树节点和空状态

### 8.3 文档树节点

**节点结构**（`.ispace-tree-node`）：

```
┌─ .ispace-tree-row ─────────────────────┐
│ [▶] 📄 文档名称                         │
└────────────────────────────────────────┘
  └─ .ispace-tree-children (可折叠)
     ├─ .ispace-tree-row → [▶] 📄 子文档1
     └─ .ispace-tree-row → [▶] 📄 子文档2
```

- **折叠图标**：22×28px，有子文档显示文件夹图标+箭头，无子文档显示文档图标
- **文档名称**：flex 1，font-sm
  - 当前文档：`ispace-active` class → brand-50 背景 + brand-500 文字 + font-medium
  - Hover 态：surface-100 背景
- **缩进**：子节点 `padding-left: 20px`

### 8.4 右键上下文菜单

**在节点上右键**：
- 有创建权限：显示"新建文档"、"新建表格"
- 有管理权限：显示"重命名"、"删除文档"

**在空白处右键**：
- 显示"新建文档"、"新建表格"（在顶层创建）

### 8.5 拖拽排序

**技术**：SortableJS（v1.15.0）

**交互规则**：
- 拖拽手柄：整行（`.ispace-tree-row`），cursor: grab
- 拖拽延迟：200ms（防止误触）
- 支持跨层级拖拽（`group: 'doc-tree'`）
- 不支持拖入自己的子节点（防止循环引用）

**悬停自动展开**：
- 拖拽悬停在折叠的文件夹上 ≥ 600ms → 自动展开该节点
- 自动展开时目标节点显示虚线边框 + brand-50 背景
- 展开后自动收缩同级其他展开节点（手风琴逻辑）

**拖拽完成**：
- Ghost 元素：opacity 0.4，brand-50 背景
- 拖拽中元素：3D 投影效果（`box-shadow: 0 8px 24px rgba(0,0,0,0.12)`）
- Drop 后 AJAX POST `/move_doc/`
- 成功后 Toast "排序已保存"

### 8.6 当前文档高亮与展开

页面加载时自动：
1. 在文档树中定位当前文档节点
2. 添加 `ispace-active` class 高亮
3. 展开当前节点的子节点
4. 展开所有祖先节点（使当前文档路径可见）

### 8.7 手风琴式展开行为

为避免文档树层级过深时视觉混乱，采用手风琴（Accordion）交互模式：
- 同一层级中同时最多只有一个节点的子文档列表展开
- 展开某节点时自动收起同级其他已展开节点
- 同时适用于手动点击和 SPA 页面导航

---

## 9. 个人中心

**URL**：`/user/center/?tab=<tab_name>`

### 9.1 布局

```
┌──────────────────────────────────────────────┐
│ Header                                       │
├──────────────┬───────────────────────────────┤
│ 个人中心侧边栏  │ 内容区                        │
│              │                               │
│ [头像 48px]   │ Tab: 基本信息 | 账号安全 | 通知设置│
│ 用户名         │                               │
│ email        │ ┌───────────────────────────┐ │
│              │ │ 表单区域                    │ │
│ 文档数 / 收藏数│ │                           │ │
│              │ └───────────────────────────┘ │
│ ─────────── │                               │
│ 个人资料       │                               │
│  基本信息      │                               │
│  账号安全      │                               │
│  通知设置      │                               │
│ ─────────── │                               │
│ 内容管理       │                               │
│  文档管理      │                               │
│  模板管理      │                               │
│  附件管理      │                               │
│  图片管理      │                               │
│  收藏管理      │                               │
│  回收站        │                               │
│  分享管理      │                               │
│ ─────────── │                               │
│ 协作           │                               │
│  我的分组      │                               │
│  我的组织      │                               │
│ ─────────── │                               │
│ 记录           │                               │
│  浏览记录      │                               │
│  站内通知      │                               │
│  授权申请      │                               │
└──────────────┴───────────────────────────────┘
```

### 9.2 个人资料卡片（侧边栏顶部）

- 头像：48×48px 圆形，有自定义头像显示图片，否则显示用户名首字母（背景色基于用户名 Hash 从 10 色板中选取）
- 用户名（font-lg semibold）
- 邮箱（font-sm text-tertiary）
- 统计数据：文档数 | 收藏数
- 组织机构：显示用户所属的主要组织节点

### 9.3 各 Tab 详情

| Tab | 功能说明 |
| --- | -------- |
| 基本信息 | 头像上传裁剪（Cropper.js，200×200px）、昵称、邮箱、个性签名、性别、手机号 |
| 账号安全 | 修改密码（旧密码+新密码+确认）、最近 20 条登录记录（IP/设备/时间） |
| 通知设置 | 7 类通知邮件开关 + 每日汇总开关 + 发送时间选择（0-23h） |
| 我的文档 | 已发布文档分页列表，含草稿数量角标 |
| 文档模板 | 模板管理面板：新建/编辑/删除模板，内联模态框操作（详见 7.8） |
| 我的分组 | 分组管理面板：创建分组、查看列表、管理成员或退出分组（详见 10.3） |
| 我的组织 | 所属组织树展示，高亮主属部门 |
| 浏览记录 | 基于持久化存储的浏览历史，支持分页加载 |
| 我的收藏 | 收藏的文档列表 |
| 回收站 | 已删除文档列表，支持恢复或彻底删除 |
| 站内通知 | 完整通知列表，支持分页和筛选（详见 14） |
| 授权申请 | 已提交的文档权限申请记录 |

---

## 10. 分组管理

**URL**：`/group/`

### 10.1 分组列表页

- 卡片网格布局（每卡片 280px）
- 卡片内容：分组名称 + 描述 + 成员数 + 创建时间
- 操作：编辑（仅 Owner） / 删除（仅 Owner，需确认）
- 创建按钮：右上角 "新建分组" → Modal（名称 + 描述）

### 10.2 分组详情页

**URL**：`/group/<group_id>/`

- 页头：分组名称 + 描述 + 成员数
- 成员列表表格：用户名 + 加入时间 + "移除"按钮（仅 Owner 可见）
- 添加成员：搜索输入框（异步搜索用户，debounce 300ms）+ 搜索结果下拉 → 点击添加
- 转让所有者：仅 Owner 可操作，下拉选择成员 + 确认

### 10.3 个人中心分组面板

分组管理功能同时在个人中心"我的分组"Tab 中提供快捷入口：

| 操作 | 个人中心 | 完整分组页 `/group/list/` |
| ---- | -------- | ----------------------- |
| 创建分组 | 模态框快捷创建 | 完整创建流程 |
| 查看列表 | 卡片网格展示 | 卡片网格展示 |
| 管理成员 | 跳转到 `/group/list/` | 搜索添加 / 移除成员 |
| 退出分组 | 直接退出（确认对话框） | — |
| 编辑分组信息 | — | Owner 可编辑名称和描述 |
| 删除分组 | — | Owner 可删除 |
| 转让所有权 | — | Owner 可转让 |

---

## 11. 组织架构管理

**URL**：`/org/`

### 11.1 组织树页面

- 树形结构展示：物化路径方式渲染
- 节点操作（右键或行末按钮）：
  - 添加子节点 → Modal（名称 + 选择部门管理员）
  - 编辑节点名称
  - 删除节点（需确认，仅空节点可删除，支持子节点迁移或级联删除）

### 11.2 节点详情

- 点击节点 → 展开详情面板
- 成员列表：同分组成员管理
- 部门管理员：显示当前管理员 + 更换按钮
- 外部来源标识（企业微信/LDAP 同步标记）

---

## 12. 文档权限管理

### 12.1 权限设置入口

**路径**：文档设置 Modal → 权限管理 Tab

### 12.2 权限管理弹窗

**布局**：左右双栏 + 底部操作栏
- **左侧面板**（260px）：对象选择器
  - 顶部 Tab 切换：用户 | 分组 | 组织
  - 搜索输入框，实时过滤
  - 对象列表：checkbox + 名称 + 用户名/描述
  - 已授权对象用占位符替代 checkbox
  - 顶部工具栏：全选 checkbox + "已选 N 项"计数
- **右侧面板**：权限设置
  - 权限级别：radio 单选（仅查看 / 可编辑 / 管理员），选中态高亮
  - 已授权列表：对象名 + 权限级别 Badge + 撤销按钮 + "待保存"标记
- **底部操作栏**：
  - 左侧："同步到所有子文档" checkbox
  - 右侧："保存更改 (N)" 按钮，N=0 时 disabled

### 12.3 权限申请

**入口**：无权限访问文档时显示 `no_permission.html`

- 页面显示："您没有访问此文档的权限"
- "申请权限"按钮 → 填写申请理由（textarea）→ 提交
- 申请发送给文档管理员
- 24 小时内不重复发送申请（后端校验）

---

## 13. 评论系统

### 13.1 评论区域布局

- 位置：文档正文下方，border-top 分隔
- 标题："评论 (N)"，N 为实时计数
- 未登录时：显示"请登录后发表评论"引导文案
- **输入框默认隐藏**：页面加载时评论输入框不可见
- **展开输入框**：点击"回复"按钮 → 输入框展开 + 聚焦 + 平滑滚动到评论区 + 初始化 @mention 选择器
- **收起输入框**：点击"取消"按钮 → 输入框收起并清空内容
- 字符计数：0/2000，实时更新

### 13.2 评论条目

```
┌──────────────────────────────────┐
│ [A] 张三 · 3小时前               │
│                                 │
│ 评论内容文字...                   │
│                                 │
│ [回复] [👍 赞] [举报]            │
│   ├── [A] 李四 · 2小时前         │
│   │   回复内容...                 │
│   │   [回复] [👍]                │
│   └── [回复框]                   │
└──────────────────────────────────┘
```

- 回复缩进最多 3 层，第 4 层起平铺
- 已删除评论显示"该评论已删除"占位
- 评论中链接自动识别为可点击超链接

### 13.3 @提及交互

- 在评论框或文档编辑器中输入 `@` 触发用户搜索
- 下拉列表显示匹配用户（用户名 + 头像），最多显示 5 条
- 选择后插入 `@username` 标记
- 后端解析并发送 mention 通知
- 文档正文 @提及在编辑保存时对比新旧内容，仅通知新增的 @用户

### 13.4 划词评论（Inline Comment）

- 用户在文档正文中选中文字 → 弹出浮动工具栏："评论"按钮
- 划词评论与选中文字位置锚定（`anchor_start` / `anchor_end`）
- 选中文字区域高亮显示（黄色背景下划线）
- 点击高亮区域显示该划词的评论列表
- 评论数量显示为高亮文字右上方小角标

---

## 14. 通知系统

### 14.1 通知铃铛（Header）

- 铃铛图标（SVG, 18px），带红色未读数角标
- 角标显示：0 时不显示，1-99 显示数字，100+ 显示 "99+"
- 未读数通过 30s 轮询 `GET /api/notifications/unread_count/` 更新

### 14.2 通知下拉面板

- 宽度：360px，最大高度 480px（overflow-y: auto）
- 每条通知：类型图标(16px，按类型着色) + 标题 + 正文(最多 2 行) + 相对时间
- 未读通知：左侧蓝色圆点 + 浅蓝背景
- 点击跳转：有文档链接的通知直接跳转文档
- "全部已读"按钮：仅在有未读通知时显示
- 下拉列表仅显示未读通知，与铃铛角标数量一致

### 14.3 通知列表

**个人中心"站内通知" Tab**：`/user_center/?tab=notifications`

- 完整通知列表，分页 20 条/页，支持无限滚动加载
- 筛选 Tab：全部 / 系统 / 评论 / @提及 / 点赞 / 权限
- 仅未读开关（Toggle）
- 支持 `open=<id>` URL 参数高亮指定通知
- 每条通知可点击跳转，自动标记已读

### 14.4 通知类型说明

| 类型 | `notification_type` | 触发场景 |
|------|---------------------|----------|
| 系统 | `system` | 系统级公告、配置变更、角色变更 |
| 评论 | `comment` | 文档新增评论 |
| 回复 | `reply` | 评论被回复 |
| @提及 | `mention` | 评论或文档正文中被 @ |
| 文档变更 | `doc_change` | 文档被编辑/删除/移动 |
| 点赞 | `doc_like` | 文档被点赞（同日同文档聚合） |
| 权限申请 | `perm_apply` | 申请文档访问权限 |
| 权限变更 | `perm_change` | 被添加/移出分组或组织节点、权限被修改 |

---

## 15. 全文搜索

### 15.1 搜索入口

- **Header 搜索框**：首页和文档浏览页显示，最大宽度 420px
- 输入关键词 + Enter → 跳转搜索结果页
- 子树搜索：`/docs/<doc_id>/search/?q=<keyword>`（限定在当前文档树内搜索）

### 15.2 搜索结果页

**URL**：`/search/?kw=<keyword>&type=doc`

- 每页 10 条
- 关键词高亮：`<em class="highlight">` 标签，黄色背景
- 时间筛选下拉：最近 1 天 / 7 天 / 30 天 / 365 天 / 自定义日期范围
- 分页器：标准页码组件

**搜索后端**：Whoosh + jieba 中文分词，支持实时索引更新。可选 Elasticsearch 企业搜索引擎。

---

## 16. 文档分享

### 16.1 分享管理

**入口**：文档设置 Modal → 分享设置 Tab

- 已有分享记录：Token + 类型 Badge（公开/私密）+ 状态 + 操作
- 创建分享：选择类型（公开/私密）→ 私密需输入分享码（≤10 位）

### 16.2 分享访问页

**URL**：`/share/<token>/`

- **公开分享**：直接显示文档内容（只读模式，无编辑功能，无侧边栏）
- **私密分享**：先显示分享码验证页 → 验证成功后进入文档只读浏览页
- 验证码存储在 Session 中，有效期内无需重复输入

---

## 17. 文档导入导出

### 17.1 导入文档

**URL**：`/import_doc/<doc_id>/`

**支持格式**：
- `.zip`：iSpaceDoc 导出格式（含 isdoc.yaml 元数据 + Markdown 文件）
- `.docx`：Word 文档（通过 Mammoth.js 转换）
- `.md` / `.txt`：Markdown 文件

**导入流程**：选择文件 → 上传进度 → 解析预览 → 确认导入 → 结果反馈

### 17.2 导出文档

**支持格式**：EPUB / PDF / DOCX

- 服务端异步生成文件
- PDF 通过 pdfkit 渲染，包含封面页 + 目录 + 正文 + 页眉页脚
- 生成完成后自动下载

---

## 18. 素材管理

### 18.1 图片管理

**URL**：`/manage_image/`

- 图片网格展示（缩略图 + 名称 + 分组 + 上传时间）
- 分组筛选下拉
- 上传：点击上传区域或拖拽 → 选择分组 → 上传
- 操作：重命名、移动分组、删除

**图片选择器**（编辑器内嵌）：
- Modal 形式，显示用户图片库
- 筛选按分组
- 点击图片即插入编辑器

### 18.2 附件管理

**URL**：`/manage_attachment/`

- 表格列表：文件名 + 大小 + 上传时间 + 下载/删除按钮
- 上传：文件选择 → 自动上传（显示进度）
- 附件预览：支持 PDF, 图片, Office 文档, 视频（mp4, flv）

---

## 19. API 开放平台

**URL**：`/api/manage_token/`

### 19.1 Token 管理页

- 页面标题："API 开放平台"
- 说明文字：介绍 API Token 的用途和使用方式
- Token 列表表格：Token 前缀（masked） + 创建时间 + 状态 + 操作
- 创建 Token：生成新 Token → 一次性显示完整 Token（警告提示）

### 19.2 API 文档

- 内嵌 API 使用说明（Markdown 渲染）
- 支持的 API 端点列表
- 请求示例代码（Python/cURL）

---

## 20. 安装初始化引导

**URL**：`/setup/`

### 20.1 引导流程

**5 步骤向导（Step Wizard）**：

```
●─────○─────○─────○─────○
1      2      3      4      5
站点信息 管理员 数据库 邮件   完成
```

| 步骤 | 配置内容 |
| ---- | -------- |
| 1 - 站点信息 | 网站名称（1-64字）、网站描述（≤256字）、默认语言 |
| 2 - 创建管理员 | 用户名、邮箱、密码（两次确认） |
| 3 - 数据库配置 | 引擎选择（SQLite/MySQL/PostgreSQL）、连接参数、"测试连接"按钮 |
| 4 - 邮件配置 | SMTP Host/Port/User/Password、SSL/TLS、"发送测试邮件"按钮 |
| 5 - 确认安装 | 配置摘要、"确认安装"按钮 → 写入配置 + 创建表 + 创建超管 → 完成 |

**完成页**：绿色 ✓ 图标 + "安装完成！" + "前往登录"按钮

### 20.2 已安装检测

- Middleware 检测 `.ispace_installed` 标记文件
- 未安装时所有请求重定向到 `/setup/`
- 白名单路径：`/setup`、`/static/`、`/media/`、`/favicon.ico`、`/login/`、`/register/`

---

## 21. 管理后台

**URL**：`/admin/`

仅超级管理员可访问。使用 SPA 架构：侧边栏 + 内容框架 + AJAX 页面加载。

### 21.1 仪表盘（Overview）

**系统健康仪表盘**：
- 3 个 conic-gradient 圆环仪表（CPU / 内存 / 磁盘），110px，百分比居中，颜色编码
- 7 项数据指标网格：用户总数 / 7天活跃 / 文档总数 / 今日新增 / 评论总数 / 图片总数 / 附件总数

**运行动态**：
- 双栏布局：最近 10 条审计日志 + 最近 5 条文档动态
- Debug 模式标签：侧边栏管理员名称旁黄色 Badge

**系统负载与并发**：
- Load Average（1/5/15 分钟）折线指示器
- 线程数 / 峰值并发 / 活跃连接数
- 各服务状态指示灯（数据库/缓存/邮件/文件存储/企业微信/通知渠道）

### 21.2 管理侧边栏菜单结构

```
📊 仪表盘
───
👥 用户管理
📄 文档管理
📝 模板管理
🖼 素材管理（可折叠）
  ├─ 图片管理
  └─ 附件管理
🔑 注册码管理
───
👥 分组管理
🏢 组织架构
🗑 文档回收站
📋 审计日志
───
🔑 登录记录
💬 评论管理
🔔 通知管理
🏥 系统健康
🔐 认证配置───
⚙ 站点设置
```

### 21.3 各管理模块功能

| 模块 | 功能说明 |
| ---- | -------- |
| 用户管理 | 用户列表、搜索、禁用/启用、编辑档案 |
| 文档管理 | 全局文档查看、筛选、管理 |
| 文档回收站 | 已删除文档列表、搜索筛选、单个/批量恢复、物理删除 |
| 审计日志 | 操作时间/操作人/操作类型/目标类型/详情/IP，支持筛选，30 条/页 |
| 登录记录 | 登录时间/用户名/IP/User-Agent/结果，支持筛选 |
| 评论管理 | 全局评论查看、筛选（文档/评论者/状态）、删除/恢复 |
| 通知管理 | 全局通知查看，按接收者/类型/已读状态筛选 |
| 系统健康 | 数据库/媒体文件/磁盘/缓存状态检查，debug 警告横幅 |
| 认证配置 | OIDC/WeCom/LDAP/DingTalk 可视化配置、启用/禁用开关、连接测试 |
| 站点设置 | 站点名称/Logo/注册设置/邮件配置/安全设置/功能开关 |

### 21.4 系统健康详情

**仪表盘卡片**（3 列网格）：
- 数据库状态：连接状态、版本、表数量、大小
- 媒体文件统计：总文件数、总大小、按月分组统计
- 磁盘使用率：磁盘总空间/已用/可用，进度条
- 缓存状态：缓存后端类型、命中率、内存使用
- 系统信息：Python 版本、Django 版本、操作系统、服务器时间

**状态指示灯**：绿色（正常）/ 黄色（警告）/ 红色（异常）

---

## 22. 新增功能

### 22.1 可视化绘图

#### 22.1.1 思维导图

- 编辑器工具栏新增"思维导图"按钮
- 点击后在编辑器中插入 `mindmap` fenced code block
- 思维导图以 JSON 格式存储节点数据
- 渲染引擎：`mind-elixir`（MIT 协议），纯 JS 无框架依赖
- 支持节点增删改、拖拽重排、快捷键操作
- 支持导出 PNG/SVG

#### 22.1.2 Draw.io 流程图

- 编辑器工具栏新增"流程图"按钮
- 点击后弹出 Draw.io 编辑模态框（`iframe` 嵌入 `embed.diagrams.net`）
- `postMessage` 双向通信：编辑器 ↔ Draw.io
- mxGraph 格式存储在文档 `content_json` 字段中
- 支持导出 PNG/SVG

**模态框规格**：`.ispace-modal-xl`（960px），全屏高度 90vh

#### 22.1.3 Excalidraw 手绘图

- 编辑器工具栏新增"手绘图"按钮
- 集成 Excalidraw（MIT 协议），封装为 Web Component
- 白板手绘风格，支持协作光标（预留）
- 数据以 JSON 存储在文档 `content_json` 字段中

### 22.2 水印功能

**文档级水印**（从 Doc 模型字段控制）：

- 启用水印：`Doc.is_watermark`（Boolean）
- 水印类型：`Doc.watermark_type`（1=文字水印，2=图片水印）
- 水印内容：`Doc.watermark_value`（用户自定义文本，为空时默认使用用户名）

**管理入口**：文档设置 Modal → 水印设置 Tab

**设置表单**：
```
┌─────────────────────────────────┐
│ 水印设置                         │
│                                 │
│ [===========] 启用水印           │
│                                 │
│ 水印类型                         │
│ ○ 文字水印  ○ 图片水印            │
│                                 │
│ 水印内容                         │
│ ┌─────────────────────────────┐ │
│ │ 请输入水印文字...              │ │
│ └─────────────────────────────┘ │
│                                 │
│ [保存设置]                       │
└─────────────────────────────────┘
```

**渲染效果**：
- 文字水印在文档正文区域重复平铺
- 透明度：0.06-0.1，倾斜角度：-15°
- 字体大小：14-18px
- CSS `pointer-events: none` 确保不干扰文本选择
- 打印时水印也可见

### 22.3 访问密码保护

**文档级访问控制**：

- `Doc.is_public`：是否允许公开访问
- `Doc.access_password`：公开访问密码（非空时启用密码验证）

**交互流程**：
1. 文档设置为 `is_public=True` + 设置 `access_password`
2. 未登录用户访问文档时，先显示密码验证页
3. 输入正确密码后，Session 记录验证状态，有效期内存取免验证
4. 密码验证页布局与私密分享验证页一致 居中卡片 + 输入框 + 验证按钮

### 22.4 WebHook 管理

**数据模型**：
- `WebHookConfig`：URL、密钥、触发事件类型（文档创建/更新/删除/评论/点赞）、启用状态
- `WebHookDelivery`：投递记录（时间、请求/响应、状态码、成功/失败）

**管理入口**：管理后台 → WebHook 管理（或独立管理页面）

**管理界面**：
- 配置列表表格：URL + 事件类型 Badge + 状态 + 操作
- 创建/编辑 WebHook：URL 输入 + 密钥生成 + 事件类型多选 checkbox + 启用开关
- 投递记录：最近投递列表 + 状态（成功/失败）+ 重试按钮

### 22.5 认证配置管理

**URL**：`/admin/system/auth/`

**功能**：管理后台提供统一的认证配置管理界面

```
┌──────────────────────────────────────────────┐
│ 认证配置管理                                   │
├──────────────────────────────────────────────┤
│                                              │
│  OIDC 认证                  [=========] 启用   │
│  ┌──────────────────────────────────────┐    │
│  │ Provider Name: [Keycloak         ▼]  │    │
│  │ Discovery URL: [https://...       ]  │    │
│  │ Client ID:     [ispace-doc        ]  │    │
│  │ Client Secret: [••••••••••••••••  ]  │    │
│  │ Scope:         [openid profile email] │    │
│  │ [测试连接] [保存配置]                  │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  企业微信认证               [=========] 启用   │
│  ┌──────────────────────────────────────┐    │
│  │ Corp ID:       [ww1234567890abcdef ] │    │
│  │ Corp Secret:   [•••••••••••••••••• ] │    │
│  │ Agent ID:      [1000002           ]  │    │
│  │ [测试连接] [保存配置] [同步通讯录]       │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  LDAP 认证                  [=========] 启用   │
│  ┌──────────────────────────────────────┐    │
│  │ Server URI:    [ldap://...         ] │    │
│  │ Bind DN:       [cn=admin,dc=...   ] │    │
│  │ ...                                  │    │
│  │ [测试连接] [保存配置] [同步通讯录]       │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  钉钉认证                   [=========] 启用   │
│  ┌──────────────────────────────────────┐    │
│  │ ...                                  │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

- 每个认证方式可折叠面板
- 启用/禁用 Toggle 开关（保留配置数据，仅控制是否在登录页展示）
- "测试连接"按钮：发送测试请求验证配置正确性
- "同步通讯录"按钮（企业微信/LDAP）：手动触发目录同步
- 同步结果显示成功/失败数量和详细日志

### 22.6 系统健康监控增强

**健康评分系统**：
- 综合健康评分（0-100 分），基于各项指标加权计算
- 扣分明细展示：每项扣分原因和分值
- 评分等级：优秀(≥90 绿) / 良好(≥70 蓝) / 警告(≥50 黄) / 危险(<50 红)

**评分维度**：
| 维度 | 权重 | 说明 |
| ---- | ---- | ---- |
| 数据库连接 | 20% | 连接状态、响应时间 |
| 缓存服务 | 15% | Redis/内存缓存状态、命中率 |
| 磁盘空间 | 15% | 剩余空间百分比 |
| 邮件服务 | 10% | SMTP 连接状态 |
| 搜索服务 | 10% | Whoosh/ES 索引状态 |
| 文件存储 | 10% | 媒体文件可访问性 |
| 任务队列 | 10% | Celery worker 状态 |
| 通知渠道 | 10% | 企业微信/钉钉连接状态 |

### 22.7 关于我们页面

**URL**：`/about/`

**页面布局**：

```
┌──────────────────────────────────────────────┐
│ Header                                       │
├──────────────────────────────────────────────┤
│                                              │
│          🏢 关于 爱思文档 i·Space Doc            │
│          企业级私有云文档 · 知识管理平台         │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ 项目简介                               │    │
│  │ 爱思文档（i·Space Doc）是基于 Python       │    │
│  │ Django 开发的企业级在线文档系统...       │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ 技术栈                                 │    │
│  │ Python / Django / Vditor / LayUI ...  │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ 开源协议                               │    │
│  │ GPL-3.0 License                      │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ 版本信息                               │    │
│  │ 当前版本：v0.9.0-dev                    │    │
│  └──────────────────────────────────────┘    │
│                                              │
├──────────────────────────────────────────────┤
│ Footer                                       │
└──────────────────────────────────────────────┘
```

- 响应式设计，移动端卡片堆叠

---

## 23. 附录：CSS 命名规范与 Class 速查

### 23.1 命名规范

- 前缀：`ispace-`
- 分隔符：单连字符 `-`（BEM 风格简化）
- Block：`ispace-btn`, `ispace-card`, `ispace-modal`
- Element：`ispace-card-header`, `ispace-modal-title`
- Modifier：`ispace-btn-sm`, `ispace-btn-primary`, `ispace-badge-success`
- 状态：`ispace-active`, `ispace-selected`, `ispace-error`, `ispace-disabled`
- 工具类：`ispace-mt-4`, `ispace-mb-2`, `ispace-text-sm`, `ispace-text-danger`, `ispace-d-none-mobile`

### 23.2 主要 Class 速查

| Category | Classes |
| -------- | ------- |
| Layout | `ispace-app-layout`, `has-sidebar`, `ispace-header`, `ispace-sidebar`, `ispace-main-content`, `ispace-footer` |
| Button | `ispace-btn`, `-primary`, `-secondary`, `-ghost`, `-danger`, `-sm`, `-lg`, `-icon`, `-outline` |
| Form | `ispace-form-group`, `-label`, `-label-required`, `-input`, `-textarea`, `-select`, `-hint`, `-error-text` |
| Table | `ispace-table` |
| Card | `ispace-card`, `-header`, `-title`, `-body`, `-footer` |
| Badge | `ispace-badge`, `-primary`, `-success`, `-warning`, `-error`, `-info` |
| Modal | `ispace-modal-backdrop`, `ispace-modal`, `-sm`, `-md`, `-lg`, `-xl`, `-header`, `-title`, `-close` |
| Toggle | `ispace-toggle` |
| Tree | `ispace-tree-node`, `-row`, `-toggle`, `-link`, `-children`, `ispace-active` |
| Context Menu | `ispace-context-menu`, `-item`, `-item--danger` |
| Sortable | `ispace-sortable-ghost`, `ispace-sortable-drag`, `ispace-drop-target` |
| Spacing | `ispace-m{t|b|l|r}-{0|1|2|3|4|5|6|8|10|12}`, `ispace-p{t|b|l|r}-{...}` |
| Text | `ispace-text-{xs|sm|base|lg|xl|2xl}`, `ispace-text-{primary|secondary|tertiary|quaternary}`, `ispace-text-danger` |
| Responsive | `ispace-d-none-mobile` |
| Auth | `ispace-auth-page`, `ispace-auth-card`, `ispace-auth-logo`, `ispace-oauth-btn`, `ispace-input-password` |
| Health | `ispace-health-gauge`, `ispace-health-score`, `ispace-health-deduction` |
| Watermark | `ispace-watermark-container`, `ispace-watermark-text` |

---

> 本文档基于 i·Space Doc v0.9.0-dev 前端代码实际实现编写，与代码库保持同步更新。
> 最后更新：2026-05-29
>
> ### 版本管理规则
>
> 本项目采用 `主版本号.次版本号.修订号[.补发号]` 格式（如 `0.9.0`）。第一位=重大需求/架构更新，第二位=功能新增/重构，第三位=问题修复/体验迭代，第四位=非常规紧急补发。详见 [需求规格说明书 §1.6](爱思文档需求说明书.md#16-版本管理规则)。
> 版本：v0.9.0-dev
