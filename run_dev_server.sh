#!/bin/sh

echo "Starting Django development server for debugging..."

# 检查是否已经初始化过
if [ ! -f "/app/MrDoc/.initialized" ]; then
    echo "First time running, initializing..."
    
    # 生成数据库迁移文件
    echo "Making migrations..."
    python /app/MrDoc/manage.py makemigrations
    
    # 根据数据库迁移文件执行数据库变更
    echo "Applying migrations..."
    python /app/MrDoc/manage.py migrate
    
    # 重建全文搜索索引
    echo "Rebuilding search index..."
    echo "y" | python /app/MrDoc/manage.py rebuild_index
    
    # 创建标记文件，表示已完成初始化
    touch /app/MrDoc/.initialized
    echo "Initialization completed."
else
    echo "Already initialized, skipping initialization steps."
fi

echo "Starting Django development server..."
python /app/MrDoc/manage.py runserver 0.0.0.0:10086