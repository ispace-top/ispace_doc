<h1 align="center">
  <img src="frontend/static/isdoc/favicon.ico" width="38" height="38" alt="iSpaceDoc" style="vertical-align: middle;" />
  爱思文档 i·Space Doc
</h1>

<p align="center">
  <strong>企业级私有云文档 · 知识管理 · 团队协作平台</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/i%C2%B7Space_Doc-v0.9.0_dev-d4843a?style=flat-square" alt="i·Space Doc v0.9.0-dev" />
  <img src="https://img.shields.io/badge/Python-3.9_%7C_3.10_%7C_3.11_%7C_3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Django-4.2-092E20?style=flat-square&logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/Docker-Supported-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/License-GPL--3.0-green?style=flat-square" alt="License" />
</p>

<p align="center">
  <a href="#-简介">📖 简介</a> ·
  <a href="#-快速开始">🚀 快速开始</a> ·
  <a href="docs/deployment.md">🐳 部署指南</a> ·
  <a href="#-认证体系">🔐 认证体系</a> ·
  <a href="#-功能特性">✨ 功能特性</a> ·
  <a href="#-技术栈">🛠 技术栈</a> ·
  <a href="#-项目文档">📚 文档</a>
</p>

---

## 📖 简介

**爱思文档**（i·Space Doc）是一款基于 Python Django 4.2 开发的企业级在线文档与知识管理平台，专为中小型团队私有化部署而设计。核心理念借鉴 Linux "一切皆文件"的哲学——**"一切皆文档"**，用统一的文档模型承载知识组织、权限管理和团队协作。

> **爱要春风化雨，思必汇流成渊。** 你可以把它看作「私有部署的语雀」或「团队协作的 GitBook」。

### 🎯 适用场景

| 场景                          | 说明                                                     |
| ----------------------------- | -------------------------------------------------------- |
| 📝**个人云笔记**        | Markdown IR 实时预览、全文搜索、标签管理、收藏、浏览历史 |
| 🏢**团队知识库**        | 多级文档树、细粒度权限、组织架构管理、划词评论、@提及    |
| 📖**产品手册 / 文档站** | 公开分享、SPA 无刷新导航、SEO 优化、站点地图             |
| 🏫**内部电子教程**      | 思维导图、流程图、数学公式、ECharts 图表、在线表格       |
| 🔒**企业合规文档**      | 水印保护、审计日志、软删除恢复、访问密码、操作日志       |

---

## ✨ 功能特性

### 📝 文档编辑

- **双编辑器** — Vditor（Markdown IR 所见即所得，默认）+ iceEditor（富文本）
- **在线表格** — Luckysheet 内嵌电子表格（`editor_mode=4`）
- **丰富内容** — 图片、附件、数学公式、音视频、思维导图、流程图、ECharts 图表
- **Callout 提示块** — `> info/warning/error/success/tip` 前缀自动渲染为彩色提示块
- **表格编辑** — IR 模式下点击表格弹出浮动工具栏，支持行列增删操作
- **文档模板** — 创建文档时从模板库一键套用，内联模板管理
- **历史版本** — 自动保存历史快照，支持 diff 对比与回滚
- **批量导入** — 支持 `.md` / `.txt` / `.docx` 文件导入

### 📖 文档阅读

- **三栏布局** — 左侧文档树 + 中间正文 + 右侧大纲导航
- **暖色调双主题** — 亮色/暗色模式，CSS Custom Properties 驱动，支持 auto 跟随系统
- **SPA 无刷新导航** — URL 格式 `/docs/<docId>/`，浏览器前进后退支持
- **三级文档树** — 手风琴展开模式，拖拽排序（SortableJS），3D 投影视觉效果
- **大纲导航面板** — 收起态标签条 + 展开态 260px 面板，IntersectionObserver 滚动跟踪
- **全文搜索** — Whoosh + jieba 中文分词，支持时间筛选和子树搜索
- **收藏** / **评论回复** / **文档分享** / **点赞**

### 🔐 企业认证体系

| 方式                   | 类型      | 说明                                                         |
| ---------------------- | --------- | ------------------------------------------------------------ |
| 🔑 本地密码            | 表单      | Django 默认用户名 + 密码，支持验证码和登录锁定               |
| 🔗**OIDC**       | OAuth 2.0 | Keycloak / Auth0 / Azure AD / Okta 等标准 OIDC IdP           |
| 💬**企业微信**   | OAuth 2.0 | QR 扫码登录 + 自建应用免登 + 通讯录同步                      |
| 📂**LDAP**       | 表单      | 搜索模式 + 直接绑定模式 + 目录同步（OU 组织单位）            |
| 📱**钉钉**       | OAuth 2.0 | 扫码登录 + 免登                                              |
| 🔌**可插拔架构** | —        | `enabled` 字段独立开关，配置保留不丢失，管理后台可视化配置 |

### 👥 权限与组织

- **三级细粒度授权** — 用户 / 分组 / 组织节点，三线合并取最大权限（`view` / `edit` / `admin`）
- **树状组织架构** — 物化路径算法，支持部门管理员任命和外部来源（企业微信/LDAP）同步标记
- **用户分组管理** — 创建分组、成员增减、管理员转让、退出分组
- **文档水印** — 文字/图片水印，自定义内容，不影响阅读
- **访问密码保护** — 公开文档可设置密码验证访问
- **全站强制登录** / **禁止注册** / **邀请码注册** — 灵活可控

### 🔔 通知与协作

- **划词评论** — 文本选中 + 锚点标记（MD5 重定位），高亮下划线展示
- **@提及通知** — 评论和文档正文均支持，编辑保存时仅通知新增用户
- **8 种通知类型** — 系统 / 评论 / 回复 / @提及 / 文档变更 / 点赞 / 权限申请 / 权限变更
- **站内通知** — 铃铛图标 + 未读角标 + 下拉面板 + 通知列表页
- **邮件通知** — SMTP 配置，8 种邮件模板，每日摘要汇总
- **可插拔通知通道** — 预留企业微信/钉钉/OA/Webhook 通知扩展

### 🛡 管理后台

- **仪表盘** — CPU/内存/磁盘圆环仪表 + 7 项数据指标 + 运行动态 + 系统负载（Load Average / 线程数 / 并发）
- **系统健康评分** — 0-100 分综合评分（8 维度加权），扣分明细展示，绿/蓝/黄/红四级状态
- **认证配置管理** — OIDC/WeCom/LDAP/DingTalk 可视化编辑、启用/禁用开关、连接测试
- **通讯录同步** — 管理后台手动触发 + 管理命令 cron 定时调度
- **审计日志** — 操作时间/人/类型/目标/详情/IP，支持筛选和分页
- **用户管理** / **文档管理** / **回收站** / **登录记录** / **评论管理** / **站点设置**

### 🌍 更多

- 🌐 **多语言** — 简体中文 / 繁體中文 / English
- 🔌 **REST API** — Token 认证，统一响应格式，支持第三方集成
- 📡 **WebHook** — 文档事件（创建/更新/删除/评论/点赞）HTTP 回调通知
- 🔍 **SEO** — 站点地图（Sitemap）自动生成
- 📱 **响应式设计** — 桌面/平板/手机三档适配

---

## 🚀 快速开始

### 环境要求

- **Python** 3.9 ~ 3.12
- **数据库** SQLite（默认）/ MySQL 8.0+ / PostgreSQL 14+
- **可选** Redis（缓存 / Celery 任务队列）

### 开发环境搭建

```bash
# 1. 克隆仓库
git clone <仓库地址>
cd iSpaceDoc

# 2. 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Linux / macOS
# .venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库
python manage.py makemigrations
python manage.py migrate

# 5. 创建管理员
python manage.py createsuperuser

# 6. 启动开发服务器
python manage.py runserver
```

访问 **http://127.0.0.1:8000**。

### 配置文件

配置文件位于 `config/conf/config.ini`，支持通过环境变量切换：

```bash
# Linux / macOS
export ISDOC_CONFIG=production.ini

# Windows PowerShell
$env:ISDOC_CONFIG = "production.ini"
```

### 常用管理命令

```bash
python manage.py migrate                  # 数据库迁移
python manage.py createsuperuser          # 创建管理员
python manage.py rebuild_index            # 重建搜索索引（Whoosh）
python manage.py sync_wecom_contacts      # 企业微信通讯录同步
python manage.py sync_ldap --dry-run      # LDAP 同步预览
python manage.py send_daily_digest        # 发送每日摘要邮件
python manage.py test backend.apps.doc    # 运行测试
```

---

## 🐳 部署运行

详见 **[部署指南 →](docs/deployment.md)**，涵盖三种部署模式的完整说明：

| 模式 | 适用场景 |
|------|---------|
| 本地开发 `python manage.py runserver` | 开发调试 |
| Docker 单容器 `docker run` | 个人使用 |
| Docker 全栈 `docker-compose up` | 生产环境 |

包括：环境配置、DEBUG 开关、数据持久化、备份恢复、无损更新。

---

## 🔐 认证体系

iSpaceDoc 支持多种企业认证方式，通过 `config.ini` 统一配置，登录页自动展示已启用的认证入口。

```
登录页 (/login)
    ├── 本地密码表单
    └── OAuth 按钮区（动态加载 /auth/providers/）
        ├── redirect 类型 (OIDC / WeCom / DingTalk) → OAuth 2.0 授权码流程
        └── form 类型 (LDAP) → 弹出用户名密码表单
```

### 配置示例

```ini
# OIDC (Keycloak 示例)
[auth.oidc]
enabled = true
provider_name = Keycloak
discovery_url = https://keycloak.example.com/realms/myrealm/.well-known/openid-configuration
client_id = ispace-doc
client_secret = your_secret
scope = openid profile email

# 企业微信
[auth.wecom]
enabled = true
corp_id = ww1234567890abcdef
corp_secret = your_corp_secret
agent_id = 1000002

# LDAP
[auth.ldap]
enabled = true
server_uri = ldap://ldap.example.com:389
bind_dn = cn=admin,dc=example,dc=com
bind_password = admin_password
user_base_dn = ou=users,dc=example,dc=com
user_filter = (uid=%(user)s)
username_attr = uid
email_attr = mail

# 钉钉
[auth.dingtalk]
enabled = false
app_key = your_app_key
app_secret = your_app_secret
```

### 目录同步

```bash
# 企业微信同步
python manage.py sync_wecom_contacts --dry-run      # 预览
python manage.py sync_wecom_contacts                 # 正式同步

# LDAP 同步（支持 OU 组织单位）
python manage.py sync_ldap --dry-run                 # 预览
python manage.py sync_ldap                           # 正式同步
```

管理后台 `/admin/system/auth/` 提供可视化配置界面，支持同步触发和状态查询。

---

## 🛠 技术栈

| 类别               | 技术                                                          | 说明                |
| ------------------ | ------------------------------------------------------------- | ------------------- |
| **后端框架** | Django 4.2 + Django REST Framework                            | Python Web 框架     |
| **异步服务** | FastAPI + Uvicorn                                             | 健康检查 / 系统 API |
| **任务队列** | Celery + Redis                                                | 异步任务 / 定时调度 |
| **数据库**   | SQLite / MySQL 8.0+ / PostgreSQL 14+                          | 可配置切换          |
| **搜索引擎** | Whoosh + jieba / Elasticsearch / Meilisearch                  | 中文分词搜索        |
| **缓存**     | Redis / LocMemCache / 数据库缓存                              | 可配置切换          |
| **前端**     | Vanilla JS + SPA 路由 + LayUI + SortableJS                    | 无框架              |
| **编辑器**   | Vditor (Markdown IR) + Luckysheet (电子表格) | —                  |
| **样式系统** | CSS Custom Properties · 暖色调深色/亮色双主题                | —                  |
| **认证**     | OIDC · OAuth 2.0 · LDAP · 企业微信 · 钉钉 · 本地密码     | 多后端可插拔        |
| **存储**     | 本地文件系统 / 阿里云 OSS / 腾讯云 COS / AWS S3 兼容          | —                  |
| **部署**     | Docker Compose · uWSGI · Alpine Linux                       | 一键部署            |
| **日志**     | Python logging + Loguru（按日滚动，保留 30 天）               | —                  |

---

## 📚 项目文档

| 文档                               | 说明                                        |
| ---------------------------------- | ------------------------------------------- |
| [部署指南](docs/deployment.md)        | 三种部署模式、DEBUG 配置、数据持久化、备份恢复 |
| [认证体系总览](docs/auth/overview.md) | 认证架构、后端结构、用户绑定机制            |
| [OIDC 认证接入](docs/auth/oidc.md)    | Keycloak / Auth0 / Azure AD / Okta 配置示例 |
| [企业微信接入](docs/auth/wecom.md)    | QR 登录、免登、通讯录同步完整文档           |
| [LDAP 认证与同步](docs/auth/ldap.md)  | 搜索模式/直接绑定模式、OU 同步配置          |

---

## 🤝 致谢

爱思文档基于以下优秀的开源项目构建：

| 项目                                                                                                | 用途                |
| --------------------------------------------------------------------------------------------------- | ------------------- |
| [Django](https://www.djangoproject.com/) + [DRF](https://www.django-rest-framework.org/)                  | Web 框架            |
| [Vditor](https://github.com/Vanessa219/vditor)                                                         | Markdown IR 编辑器  |
| [iceEditor](https://github.com/iceEditor/iceEditor)                                                    | 富文本编辑器        |
| [Luckysheet](https://github.com/dream-num/Luckysheet)                                                  | 在线电子表格        |
| [LayUI](https://layui.dev/)                                                                            | UI 组件库           |
| [Whoosh](https://whoosh.readthedocs.io/) + [jieba](https://github.com/fxsjy/jieba)                        | 全文搜索 + 中文分词 |
| [Elasticsearch](https://www.elastic.co/)                                                               | 企业搜索引擎        |
| [SortableJS](https://sortablejs.github.io/Sortable/)                                                   | 拖拽排序            |
| [ECharts](https://echarts.apache.org/)                                                                 | 数据图表            |
| [mind-elixir](https://github.com/ssshooter/mind-elixir)                                                | 思维导图            |
| [Draw.io](https://github.com/jgraph/drawio)                                                            | 流程图              |
| [Excalidraw](https://github.com/excalidraw/excalidraw)                                                 | 手绘白板            |
| [python-ldap](https://www.python-ldap.org/)                                                            | LDAP 认证           |
| [PostgreSQL](https://www.postgresql.org/) · [Redis](https://redis.io/) · [Docker](https://www.docker.com/) | 基础设施            |

---

## 🙏 特别鸣谢

爱思文档在设计和开发过程中，参考并学习了以下优秀开源项目：

| 项目                                                             | 说明                                                                                                                        |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| [**MrDoc**](https://github.com/zmister2016/MrDoc)  觅思文档 | i·Space Doc 早期开发阶段参考了 MrDoc 的文档管理架构、权限模型设计和前后端交互模式，在此对 MrDoc 项目及其作者表示诚挚感谢。 |

> 开源精神薪火相传，在巨人肩膀上才能看得更远。

---

## 📄 协议

[GPL-3.0 License](LICENSE)

开源版使用者必须保留「爱思文档」及「i·Space Doc」相关版权标识，禁止对其进行修改或删除。

---

<p align="center">
  <sub>Made with ❤️ by i·Space Doc Team · <strong>v0.9.0-dev</strong> · 爱要春风化雨，思必汇流成渊</sub>
</p>
