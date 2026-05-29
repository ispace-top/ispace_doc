#!/usr/bin/env python
import os
import sys

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.core.settings")
    django.setup()
    
    # 尝试导入关键模块检查是否正常
    try:
        from django.contrib.auth.models import User
        print("Django imported successfully")
        
        # 尝试访问数据库
        user_count = User.objects.count()
        print(f"Database connection successful, user count: {user_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)