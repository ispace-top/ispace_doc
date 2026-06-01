# 🖥️ 系统安装配置

>i **适用对象**：系统管理员、运维人员。

## 1. 环境要求

| 项目 | 最低 | 推荐 |
|------|------|------|
| OS | Ubuntu 20.04+ | Ubuntu 22.04 |
| CPU | 1核 | 2核+ |
| 内存 | 1GB | 4GB+ |
| Docker | 20.10+ | 最新版 |

## 2. 三种部署方式

### 本地开发

```bash
git clone https://github.com/ispace-top/ispace_doc.git
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

>i DEBUG 自动检测 runserver 并启用。

### Docker 单容器 (Lite)

```bash
docker compose -f config/docker/docker-compose.lite.yml up -d
```

- SQLite + Whoosh，无需外部依赖

### Docker 多容器 (生产)

```bash
cp config/docker/.env.example config/docker/.env
docker compose -f config/docker/docker-compose.yml up -d
```

- PostgreSQL + Redis + Elasticsearch + Celery

## 3. 配置文件

| 文件 | 场景 |
|------|------|
| config.ini | 本地开发 |
| config-docker.ini | Docker 多容器 |
| config-lite.ini | Docker 单容器 |

环境变量 `ISDOC_CONFIG` 选择配置文件。

## 4. 安全建议

- 生产设置 `SECRET_KEY` 环境变量
- 生产设置 `DEBUG=false`
- 数据库密码用环境变量注入
- 配置 HTTPS
- 定期备份 data/ media/ 目录
