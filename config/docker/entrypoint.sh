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

# 确保 media 和 log 目录存在
mkdir -p /app/iSpaceDoc/media /app/iSpaceDoc/log

# 执行传入的命令（uwsgi / uvicorn / 其他）
exec "$@"
