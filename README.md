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
  <a href="#-docker-部署">🐳 Docker 部署</a> ·
  <a href="#-数据持久化与目录映射">💾 数据持久化</a> ·
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

## 🐳 Docker 部署

iSpaceDoc 提供两种 Docker 部署模式，按需选择：

| 模式                 | 配置文件                    | 适用场景                       | 依赖                               |
| -------------------- | --------------------------- | ------------------------------ | ---------------------------------- |
| 🪶**轻量模式** | `docker-compose.lite.yml` | 个人使用 / 开发测试 / 快速体验 | 仅 Docker，无需外部服务            |
| 🏭**完整模式** | `docker-compose.yml`      | 团队协作 / 生产环境            | PostgreSQL + Redis + Elasticsearch |

---

### 🪶 轻量模式（SQLite · 单容器）

无需安装任何外部依赖，一个容器即开即用，数据持久化到 Docker Volume。

```
┌───────────────────────────┐
│     Docker Container       │
│                           │
│  Django App (uWSGI)        │
│  Port 10086               │
│                           │
│  SQLite + Whoosh           │
│                           │
│  持久化卷:                 │
│  data · media · index      │
└───────────────────────────┘
```

```bash
# 克隆仓库
git clone <仓库地址>
cd iSpaceDoc

# 启动（单容器，SQLite + Whoosh，无需外部依赖）
docker compose -f config/docker/docker-compose.lite.yml up -d

# 创建管理员账户
docker exec -it ispacedoc-app-1 python manage.py createsuperuser

# 查看日志
docker compose -f config/docker/docker-compose.lite.yml logs -f app
```

访问 **http://localhost:10086**。

> 轻量模式使用 SQLite 数据库 + Whoosh 搜索引擎，自动与配置文件 `config-lite.ini` 关联。首次启动自动执行数据库迁移。

---

### 🏭 完整模式（PostgreSQL + Redis + ES · 多容器）

适用于团队协作和生产环境，需要 PostgreSQL、Redis、Elasticsearch 等外部服务。

**架构概览**：

```
┌──────────────────────────────────────────────────────────────┐
│                     Docker Compose                            │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐           │
│  │PostgreSQL│  │ Redis 7  │  │ Elasticsearch 8.x│           │
│  │   16     │  │          │  │                  │           │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘           │
│       │              │                │                      │
│  ┌────┴──────────────┴────────────────┴─────────┐           │
│  │            Django App (uWSGI :10086)           │           │
│  └──────────────────────┬────────────────────────┘           │
│                         │                                    │
│  ┌──────────────────────┼────────────────────────┐           │
│  │  FastAPI (:8000) · Celery Worker · Celery Beat│           │
│  └──────────────────────┴────────────────────────┘           │
│                                                              │
│  持久化卷: pgdata · redisdata · esdata · media · log         │
└──────────────────────────────────────────────────────────────┘
```

```bash
# 启动全部服务
docker compose -f config/docker/docker-compose.yml up -d

# 查看运行状态
docker compose -f config/docker/docker-compose.yml ps

# 查看日志
docker compose -f config/docker/docker-compose.yml logs -f app
```

> 默认监听 **http://localhost:10086**。首次启动自动执行数据库迁移和索引初始化。

### 两种模式对比

| 维度          |    🪶 轻量模式    |     🏭 完整模式     |
| ------------- | :----------------: | :-----------------: |
| 数据库        |       SQLite       |    PostgreSQL 16    |
| 搜索引擎      | Whoosh（文件索引） |  Elasticsearch 8.x  |
| 缓存          |      本地内存      |       Redis 7       |
| 任务队列      |   无（同步处理）   |   Celery + Redis   |
| 容器数        |         1         |          6          |
| 内存占用      |       ~200MB       |        ~2GB+        |
| 适用场景      |  个人/测试/小团队  | 中大型团队/生产环境 |
| PostgreSQL    |      `5432`      |       数据库       |
| Redis         |      `6379`      |   缓存 / 消息队列   |
| Elasticsearch |      `9200`      |  搜索引擎（可选）  |

---

## 💾 数据持久化与目录映射

Docker 容器本身是**无状态**的——容器删除后内部所有数据将丢失。为实现**重新安装、版本升级、容器重建后数据不丢失**，必须将所有关键数据通过 Volume 映射到宿主机持久化存储。

### Volume 映射表

**轻量模式**（`docker-compose.lite.yml`）：

| Volume 名称      | 容器内路径                      | 存储内容                            |      备份优先级      |
| ---------------- | ------------------------------- | ----------------------------------- | :------------------: |
| `ispace_data`  | `/app/iSpaceDoc/data`          | SQLite 数据库文件（`db.sqlite3`） | ⭐⭐⭐**最高** |
| `ispace_media` | `/app/iSpaceDoc/media`        | 用户上传的图片、附件、头像          | ⭐⭐⭐**最高** |
| `ispace_index` | `/app/iSpaceDoc/whoosh_index` | Whoosh 搜索索引（可重建）           |       ⭐⭐ 高       |

**完整模式**（`docker-compose.yml`）：

| Volume 名称   | 容器内路径                        | 存储内容                                 |      备份优先级      |
| ------------- | --------------------------------- | ---------------------------------------- | :------------------: |
| `pgdata`    | `/var/lib/postgresql/data`      | PostgreSQL 数据库全部数据                | ⭐⭐⭐**最高** |
| `media`     | `/app/iSpaceDoc/media`          | 用户上传的图片、附件、头像、文档导入文件 | ⭐⭐⭐**最高** |
| `esdata`    | `/usr/share/elasticsearch/data` | Elasticsearch 索引数据（可重建）         |       ⭐⭐ 高       |
| `redisdata` | `/data`                         | Redis AOF 持久化数据（缓存 + 会话）      |        ⭐ 中        |
| `log`       | `/app/iSpaceDoc/log`            | 应用日志（按日滚动，保留 30 天）         |        ⭐ 低        |

### 方式一：Docker Named Volumes（默认，推荐）

默认的 `docker-compose.yml` 使用 Docker Named Volumes，Docker 自动管理存储位置，简单安全。

```bash
# 查看各 volume 在宿主机上的实际存储位置
docker volume inspect iSpaceDoc_pgdata
docker volume inspect iSpaceDoc_media
docker volume inspect iSpaceDoc_esdata
```

> **Windows / macOS 注意**：Docker Desktop 的 volume 数据存储在虚拟机内部，不能直接在宿主机文件系统中访问。可通过以下方式查看和操作：
>
> ```bash
> # 进入临时容器查看 volume 内容
> docker run --rm -it -v iSpaceDoc_media:/data alpine ls -la /data
> ```

### 方式二：Bind Mounts（将数据映射到宿主机指定目录）

如果你需要将数据存储在**宿主机指定目录**（便于直接备份、迁移或使用外部存储），可以修改 `docker-compose.yml` 将 Named Volumes 改为 Bind Mounts。

**步骤 1：创建宿主机数据目录**

```bash
# Linux / macOS
sudo mkdir -p /data/ispacedoc/{pgdata,media,esdata,redisdata,log}

# 设置目录权限（PostgreSQL 需要 uid 999）
sudo chown -R 999:999 /data/ispacedoc/pgdata
sudo chown -R 1000:1000 /data/ispacedoc/media /data/ispacedoc/log
```

**步骤 2：修改 `config/docker/docker-compose.yml`**

将文件底部的 `volumes:` 声明删除（或注释），然后将各服务的 `volumes` 从 Named Volume 改为 Bind Mount：

```yaml
# 修改前（Named Volume — 容器删除后数据仍在 Docker 内部，但不易直接访问）
services:
  db:
    volumes:
      - pgdata:/var/lib/postgresql/data    # ← Named Volume
  app:
    volumes:
      - media:/app/iSpaceDoc/media         # ← Named Volume
      - log:/app/iSpaceDoc/log

volumes:                                   # ← 删除这段
  pgdata:
  redisdata:
  esdata:
  media:
  log:
```

```yaml
# 修改后（Bind Mount — 数据直接存储在宿主机指定目录）
services:
  db:
    volumes:
      - /data/ispacedoc/pgdata:/var/lib/postgresql/data    # ← Bind Mount
  redis:
    volumes:
      - /data/ispacedoc/redisdata:/data                     # ← Bind Mount
  elasticsearch:
    volumes:
      - /data/ispacedoc/esdata:/usr/share/elasticsearch/data
  app:
    volumes:
      - /data/ispacedoc/media:/app/iSpaceDoc/media          # ← Bind Mount
      - /data/ispacedoc/log:/app/iSpaceDoc/log              # ← Bind Mount
  fastapi:
    volumes:
      - /data/ispacedoc/media:/app/iSpaceDoc/media
  celery-worker:
    volumes:
      - /data/ispacedoc/media:/app/iSpaceDoc/media
```

**步骤 3：重新部署**

```bash
# 停止旧容器
docker compose -f config/docker/docker-compose.yml down

# 启动新配置
docker compose -f config/docker/docker-compose.yml up -d

# 验证数据目录
ls -la /data/ispacedoc/pgdata/
ls -la /data/ispacedoc/media/
```

### 方式三：使用环境变量配置数据目录

创建 `.env` 文件，通过变量统一管理宿主机数据路径：

```bash
# .env 文件内容
DATA_ROOT=/data/ispacedoc
```

然后在 `docker-compose.yml` 中引用：

```yaml
services:
  db:
    volumes:
      - ${DATA_ROOT:-./data}/pgdata:/var/lib/postgresql/data
  app:
    volumes:
      - ${DATA_ROOT:-./data}/media:/app/iSpaceDoc/media
      - ${DATA_ROOT:-./data}/log:/app/iSpaceDoc/log
```

> `:-./data` 表示如果未设置 `DATA_ROOT` 环境变量，则默认使用 `./data`（项目目录下的 data 文件夹）。

---

## 📦 备份与恢复

### 备份方案

```bash
# === 方案 A：宿主机 tar 备份（推荐，适用于 Bind Mount） ===
BACKUP_DIR="/backup/ispacedoc/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 1. 备份数据库（pg_dump 导出 SQL）
docker exec ispacedoc-db-1 pg_dump -U ispace ispace > "$BACKUP_DIR/db_backup.sql"

# 2. 备份媒体文件
cp -r /data/ispacedoc/media "$BACKUP_DIR/media"

# 3. 打包
tar czf "$BACKUP_DIR.tar.gz" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR")"
echo "备份完成: $BACKUP_DIR.tar.gz"
```

```bash
# === 方案 B：Named Volume 备份（使用临时容器） ===
BACKUP_DIR="/backup/ispacedoc/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 数据库
docker exec ispacedoc-db-1 pg_dump -U ispace ispace > "$BACKUP_DIR/db_backup.sql"

# 媒体文件
docker run --rm -v iSpaceDoc_media:/data -v "$BACKUP_DIR":/backup alpine \
  tar czf /backup/media.tar.gz -C /data .

# 搜索索引
docker run --rm -v iSpaceDoc_esdata:/data -v "$BACKUP_DIR":/backup alpine \
  tar czf /backup/esdata.tar.gz -C /data .
```

```bash
# === 定时备份脚本（crontab，每天凌晨 2:00） ===
# 0 2 * * * /opt/scripts/backup-ispacedoc.sh
```

### 恢复流程

```bash
# 1. 停止服务
docker compose -f config/docker/docker-compose.yml down

# 2. 恢复数据库
docker compose -f config/docker/docker-compose.yml up -d db
docker exec -i ispacedoc-db-1 psql -U ispace ispace < /backup/db_backup.sql

# 3. 恢复媒体文件
# Bind Mount 方式：
cp -r /backup/media/* /data/ispacedoc/media/

# Named Volume 方式：
docker run --rm -v iSpaceDoc_media:/data -v /backup:/backup alpine \
  tar xzf /backup/media.tar.gz -C /data

# 4. 重新启动全部服务
docker compose -f config/docker/docker-compose.yml up -d

# 5. 重建搜索索引（如恢复的是 esdata 则跳过）
docker exec ispacedoc-app-1 python manage.py rebuild_index --noinput
```

---

## 🔄 无损更新流程

无损更新的核心原则：**仅替换容器镜像和应用代码，不触碰数据卷**。

```bash
# 第一步：拉取新代码
cd iSpaceDoc
git pull origin main

# 第二步：重新构建镜像（应用代码更新）
docker compose -f config/docker/docker-compose.yml build app

# 第三步：滚动重启（仅重启应用服务，不触碰 db/redis/es）
docker compose -f config/docker/docker-compose.yml up -d \
  --no-deps --force-recreate \
  app fastapi celery-worker celery-beat

# 第四步（如有数据库迁移）：执行迁移
docker exec ispacedoc-app-1 python manage.py migrate
```

### 更新场景速查表

| 更新内容         | 操作                                                            |   数据安全   |
| ---------------- | --------------------------------------------------------------- | :-----------: |
| 应用代码更新     | `git pull` → `docker compose build app` → `up -d`       |    ✅ 无损    |
| 新增 Python 依赖 | 修改 requirements.txt →`docker compose build --no-cache app` |    ✅ 无损    |
| Django 模型变更  | `docker exec app python manage.py migrate`                    |    ✅ 无损    |
| 配置文件修改     | 修改 config.ini → 重启容器                                     |    ✅ 无损    |
| 数据库版本升级   | 先备份 → 修改镜像版本 →`up -d`                              |  ⚠️ 需备份  |
| 搜索引擎重建     | `docker exec app python manage.py rebuild_index`              | ✅ 索引可重建 |
| 完全卸载重装     | `docker compose down -v` → 全新部署                          |  ❌ 全部丢失  |

```bash
# ⚠️ 危险操作：彻底清理（删除所有数据！）
docker compose -f config/docker/docker-compose.yml down -v
# -v 参数会一并删除所有 named volumes，数据不可恢复！
```

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
| **编辑器**   | Vditor (Markdown IR) + iceEditor (富文本) + Luckysheet (表格) | —                  |
| **样式系统** | CSS Custom Properties · 暖色调深色/亮色双主题                | —                  |
| **认证**     | OIDC · OAuth 2.0 · LDAP · 企业微信 · 钉钉 · 本地密码     | 多后端可插拔        |
| **存储**     | 本地文件系统 / 阿里云 OSS / 腾讯云 COS / AWS S3 兼容          | —                  |
| **部署**     | Docker Compose · uWSGI · Alpine Linux                       | 一键部署            |
| **日志**     | Python logging + Loguru（按日滚动，保留 30 天）               | —                  |

---

## 📚 项目文档

| 文档                               | 说明                                        |
| ---------------------------------- | ------------------------------------------- |
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
