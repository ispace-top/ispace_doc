#!/bin/sh
set -e

echo "Starting iSpaceDoc container..."

# 确保持久化目录存在（必须在 migrate 之前，SQLite 需要）
mkdir -p /app/iSpaceDoc/data /app/iSpaceDoc/media /app/iSpaceDoc/log /app/iSpaceDoc/whoosh_index

# 检查是否已经初始化过
if [ ! -f "/app/iSpaceDoc/.initialized" ]; then
    echo "First time running — running database migrations..."
    python /app/iSpaceDoc/manage.py migrate --noinput
    if [ $? -ne 0 ]; then
        echo "ERROR: Database migration failed"
        exit 1
    fi
    touch /app/iSpaceDoc/.initialized
    echo "Initialization completed."
else
    echo "Already initialized, skipping migrations."
fi

# 初始化持久化配置文件（首次部署时从镜像默认配置复制）
for _cfg in config-lite.ini config-docker.ini; do
    _cfg_path="/app/iSpaceDoc/config/conf/${_cfg}"
    if [ -d "$_cfg_path" ]; then
        # Docker bind mount 的空目录，删除后从镜像模板复制
        echo "Replacing directory ${_cfg_path} with default config file..."
        rm -rf "$_cfg_path"
    fi
    if [ ! -f "$_cfg_path" ] && [ -f "/app/iSpaceDoc/config/conf-templates/${_cfg}" ]; then
        cp "/app/iSpaceDoc/config/conf-templates/${_cfg}" "$_cfg_path"
        echo "Created ${_cfg} from default template."
    fi
done

# 执行传入的命令，如果 uwsgi ini 文件缺失则回退到命令行参数
if [ "$1" = "uwsgi" ] && [ "$2" = "--ini" ]; then
    UWSGI_INI="$3"
    if [ ! -f "$UWSGI_INI" ]; then
        echo "WARNING: $UWSGI_INI not found, falling back to inline config."
        echo "Contents of /app/iSpaceDoc/config/conf/:"
        ls -la /app/iSpaceDoc/config/conf/ 2>&1 || echo "(directory not found)"
        exec uwsgi \
            --master \
            --processes 5 \
            --chdir /app/iSpaceDoc \
            --wsgi-file /app/iSpaceDoc/backend/core/wsgi.py \
            --http-socket "0.0.0.0:${LISTEN_PORT:-8000}" \
            --logto /app/iSpaceDoc/log/uwsgi.log \
            --log-maxsize 3000000 \
            --chmod-socket 664 \
            --vacuum \
            --enable-threads \
            --max-requests 1000 \
            --buffer-size 65536 \
            --die-on-term
    fi
fi

exec "$@"
