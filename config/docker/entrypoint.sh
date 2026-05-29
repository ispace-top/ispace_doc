#!/bin/sh
set -e

echo "Starting iSpaceDoc container..."

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

# 确保持久化目录存在
mkdir -p /app/iSpaceDoc/data /app/iSpaceDoc/media /app/iSpaceDoc/log /app/iSpaceDoc/whoosh_index

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
