#!/bin/sh

echo "Starting MrDoc Docker container..."

# 检查是否已经初始化过
if [ ! -f "/app/MrDoc/.initialized" ]; then
    echo "First time running, initializing..."
    
    # 生成数据库迁移文件
    echo "Making migrations..."
    python /app/MrDoc/manage.py makemigrations
    if [ $? -ne 0 ]; then
        echo "Failed to make migrations"
        exit 1
    fi
    
    # 根据数据库迁移文件执行数据库变更
    echo "Applying migrations..."
    python /app/MrDoc/manage.py migrate
    if [ $? -ne 0 ]; then
        echo "Failed to apply migrations"
        exit 1
    fi
    
    # 重建全文搜索索引
    echo "Rebuilding search index..."
    echo "y" | python /app/MrDoc/manage.py rebuild_index
    if [ $? -ne 0 ]; then
        echo "Failed to rebuild search index"
        exit 1
    fi
    
    # 创建标记文件，表示已完成初始化
    touch /app/MrDoc/.initialized
    echo "Initialization completed."
else
    echo "Already initialized, skipping initialization steps."
fi

# 确保log目录存在并具有正确的权限
mkdir -p /app/MrDoc/log
chmod 777 /app/MrDoc/log

# 测试Django是否能正常工作
echo "Testing Django setup..."
python /app/MrDoc/config/tests/test_django.py
if [ $? -ne 0 ]; then
    echo "Django test failed, exiting..."
    exit 1
fi
echo "Django test passed."

# 检查uwsgi是否安装
echo "Checking for uwsgi installation..."
if ! command -v uwsgi &> /dev/null
then
    echo "uwsgi could not be found, trying to install..."
    pip install uwsgi
fi

echo "Starting uWSGI server..."
# 启动uwsgi
uwsgi --ini /app/MrDoc/config/conf/uwsgi.ini