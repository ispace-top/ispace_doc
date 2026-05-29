# iSpaceDoc 部署指南

## 三种部署模式

| 模式 | 命令 | 数据库 | 适用场景 |
|------|------|--------|---------|
| **本地开发** | `python manage.py runserver` | SQLite | 开发调试、代码修改 |
| **Docker 单容器** | `docker run` | SQLite + Whoosh | 个人使用、快速体验 |
| **Docker 全栈** | `docker-compose up` | PostgreSQL + Redis + ES | 团队协作、生产环境 |

---

## 一、本地开发模式

```bash
cd iSpaceDoc
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

访问 `http://127.0.0.1:8000`。

**DEBUG 开关**：编辑 `config/conf/config.ini`

```ini
[site]
debug = True   # 开发环境开启，自动提供静态文件，显示详细错误
```

本地开发时 `debug = True` 即可，Django runserver 自动处理静态文件，无需额外配置。

---

## 二、Docker 单容器模式（轻量）

使用内置 SQLite + Whoosh，无需 PostgreSQL/Redis/ES。

### 2.1 快速启动

```bash
docker run -d \
  --name ispacedoc \
  -p 8000:8000 \
  -e ISDOC_CONFIG=config-lite.ini \
  -e SECRET_KEY=your-secret-key \
  -v ~/ispacedoc/data:/app/iSpaceDoc/data \
  -v ~/ispacedoc/media:/app/iSpaceDoc/media \
  -v ~/ispacedoc/log:/app/iSpaceDoc/log \
  -v ~/ispacedoc/whoosh_index:/app/iSpaceDoc/whoosh_index \
  wapedkj/ispace-doc:latest
```

### 2.2 数据持久化

| 宿主机路径 | 容器内路径 | 内容 |
|-----------|-----------|------|
| `~/ispacedoc/data` | `/app/iSpaceDoc/data` | SQLite 数据库 |
| `~/ispacedoc/media` | `/app/iSpaceDoc/media` | 上传文件 |
| `~/ispacedoc/log` | `/app/iSpaceDoc/log` | 应用日志 |
| `~/ispacedoc/whoosh_index` | `/app/iSpaceDoc/whoosh_index` | 搜索索引 |

### 2.3 DEBUG 配置

轻量模式默认使用 `config-lite.ini`，`debug = False`。静态文件由 Whitenoise 中间件在构建时预收集并提供服务。

如需调试，可在启动后进入容器修改：

```bash
docker exec -it ispacedoc vi /app/iSpaceDoc/config/conf/config-lite.ini
# 将 debug = False 改为 debug = True
docker restart ispacedoc
```

---

## 三、Docker 全栈模式（完整）

使用 PostgreSQL + Redis + Elasticsearch + Celery，适合团队协作和生产环境。

### 3.1 使用在线镜像部署（推荐）

```bash
cd config/docker

# 创建 .env 配置
cat > .env << 'EOF'
DB_NAME=ispace
DB_USER=ispace
DB_PASSWORD=请修改为安全密码
SECRET_KEY=请修改为随机字符串
# 以下为可选配置
IMAGE_TAG=latest
APP_PORT=8000
API_PORT=8001
EOF

# 拉取镜像并启动
docker pull wapedkj/ispace-doc:latest
docker-compose -f docker-compose.deploy.yml up -d
```

### 3.2 从源码构建部署

```bash
cd config/docker

cat > .env << 'EOF'
DB_NAME=ispace
DB_USER=ispace
DB_PASSWORD=请修改为安全密码
SECRET_KEY=请修改为随机字符串
EOF

docker-compose -f docker-compose.yml up -d --build
```

### 3.3 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| App (uWSGI) | `8000` | Django 主应用 |
| FastAPI (Uvicorn) | `8001` | 异步 API |
| PostgreSQL 16 | `5432` | 数据库 |
| Redis 7 | `6379` | 缓存 / 消息队列 |
| Elasticsearch 8 | `9200` | 全文搜索 |
| Celery Worker | — | 异步任务 |
| Celery Beat | — | 定时任务 |

### 3.4 DEBUG 配置

完整模式使用 `config-docker.ini`，`debug = True`。生产环境应设为 `False`：

```bash
docker exec -it docker_app_1 vi /app/iSpaceDoc/config/conf/config-docker.ini
# 将 debug = True 改为 debug = False
docker-compose restart app
```

> `debug = True` 时 Django 详细错误页面会暴露敏感信息，**公网部署必须关闭**。

---

## 四、数据持久化与目录映射

Docker 容器删除后内部数据全部丢失，必须通过 Volume 持久化。

### 单容器模式

| 挂载 | 容器内路径 | 备份优先级 |
|------|-----------|:---:|
| `data` | `/app/iSpaceDoc/data` | ⭐⭐⭐ |
| `media` | `/app/iSpaceDoc/media` | ⭐⭐⭐ |
| `whoosh_index` | `/app/iSpaceDoc/whoosh_index` | ⭐⭐ |
| `log` | `/app/iSpaceDoc/log` | ⭐ |

### 全栈模式

| Volume | 容器内路径 | 备份优先级 |
|--------|-----------|:---:|
| `pgdata` | `/var/lib/postgresql/data` | ⭐⭐⭐ |
| `media` | `/app/iSpaceDoc/media` | ⭐⭐⭐ |
| `esdata` | `/usr/share/elasticsearch/data` | ⭐⭐ |
| `redisdata` | `/data` | ⭐ |
| `log` | `/app/iSpaceDoc/log` | ⭐ |

### Bind Mount 方式

将数据存储在宿主机指定目录：

```yaml
# docker-compose.yml
services:
  db:
    volumes:
      - /data/ispacedoc/pgdata:/var/lib/postgresql/data
  app:
    volumes:
      - /data/ispacedoc/media:/app/iSpaceDoc/media
```

---

## 五、备份与恢复

### 备份

```bash
# 数据库
docker exec docker_db_1 pg_dump -U ispace ispace > db_backup.sql

# 媒体文件（Bind Mount 方式）
cp -r /data/ispacedoc/media /backup/media

# Named Volume 方式
docker run --rm -v docker_media:/data -v /backup:/backup alpine tar czf /backup/media.tar.gz -C /data .
```

### 恢复

```bash
# 停止服务
docker-compose -f docker-compose.deploy.yml down

# 恢复数据库
docker-compose -f docker-compose.deploy.yml up -d db
docker exec -i docker_db_1 psql -U ispace ispace < db_backup.sql

# 恢复文件后重启
docker-compose -f docker-compose.deploy.yml up -d
```

---

## 六、无损更新流程

```bash
cd config/docker

# 拉取新镜像
docker pull wapedkj/ispace-doc:latest

# 滚动重启（不触碰 db/redis/es）
docker-compose -f docker-compose.deploy.yml up -d --no-deps --force-recreate app fastapi celery-worker celery-beat

# 如有数据库迁移
docker exec docker_app_1 python manage.py migrate
```

---

## 七、模式对比

| 维度 | 本地开发 | 单容器 | 全栈 |
|------|:---:|:---:|:---:|
| 数据库 | SQLite | SQLite | PostgreSQL 16 |
| 搜索引擎 | Whoosh | Whoosh | Elasticsearch 8 |
| 缓存 | 本地内存 | 本地内存 | Redis 7 |
| 任务队列 | 无 | 无 | Celery + Redis |
| 静态文件 | Django runserver | Whitenoise | Whitenoise |
| DEBUG 默认值 | True | False | True |
| 容器数 | 0 | 1 | 7 |
| 内存占用 | ~200MB | ~200MB | ~2GB+ |
