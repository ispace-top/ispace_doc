"""
管理命令：生成与 MrDoc 结构相似的测试文档，用于性能测试。
用法: python manage.py seed_test_docs --count 300
"""
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User


LOREM_PARAGRAPHS = [
    """## 概述

在现代软件开发中，架构设计是整个系统的基石。一个好的架构设计需要考虑以下关键因素：

- **可扩展性**：系统应能随着业务增长而水平扩展
- **可维护性**：代码结构清晰，模块间耦合度低
- **性能**：在高并发场景下保持稳定的响应时间
- **安全性**：防范常见的 Web 安全威胁

### 微服务架构的优势

微服务架构通过将单体应用拆分为独立的小服务，每个服务专注于单一业务领域，独立部署和扩展。这种方式带来的好处包括：

1. 技术栈灵活：不同服务可以选择最适合的技术
2. 故障隔离：单个服务故障不影响整体系统
3. 团队自治：小团队可以独立负责完整服务生命周期""",

    """## 实现细节

### 数据库设计

数据库设计需要遵循第三范式（3NF），确保数据的一致性和完整性：

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(150) NOT NULL UNIQUE,
    email VARCHAR(254) NOT NULL,
    date_joined DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
```

### API 设计原则

RESTful API 设计遵循以下原则：

- 使用 HTTP 动词表示操作（GET/POST/PUT/DELETE）
- 资源 URL 使用名词复数形式
- 使用 HTTP 状态码表示结果
- 支持分页、过滤和排序

```python
# Django REST Framework 示例
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.filter(status=1)
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)
```
""",

    """## 常见问题与解决方案

### 1. 高并发下的缓存策略

> i 缓存是解决高并发访问性能问题的最有效手段之一。合理使用缓存可以将数据库查询次数减少 90% 以上。

#### Redis 缓存层设计

使用 Redis 作为缓存层时，需要注意：

- 设置合理的过期时间（TTL），避免内存溢出
- 使用缓存穿透、缓存击穿、缓存雪崩的防护策略
- 对于热点数据，可以采用本地缓存 + 分布式缓存的双层架构

```python
from django.core.cache import cache

def get_document_with_cache(doc_id):
    cache_key = f'doc:{doc_id}'
    cached = cache.get(cache_key)
    if cached:
        return cached
    doc = Document.objects.get(id=doc_id)
    cache.set(cache_key, doc, timeout=300)
    return doc
```

> w 注意：缓存不一致可能导致用户看到过期的数据，建议在数据更新时主动清除相关缓存。

### 2. SQLite 性能优化

> t SQLite 在开启 WAL 模式后，读性能可以提升 3-5 倍，且支持读写并发。

在 Django 中通过连接信号设置 WAL：

```python
from django.db.backends.signals import connection_created

def setup_sqlite_pragmas(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA synchronous=NORMAL;')

connection_created.connect(setup_sqlite_pragmas)
```

> e 不要在事务中间修改 journal_mode，这会导致数据库锁。

> s 建议在生产环境中定期运行 `PRAGMA optimize` 来优化查询计划。""",

    """## 单元测试最佳实践

### 测试金字塔

单元测试是软件质量的基石。遵循测试金字塔原则：

- **单元测试**（底座）：覆盖核心业务逻辑，快速且可靠
- **集成测试**（中层）：验证组件间的交互
- **端到端测试**（顶层）：验证完整的用户场景

### AAA 模式

每个测试用例遵循 AAA（Arrange-Act-Assert）模式：

```python
import pytest
from django.test import TestCase

class DocumentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_document_creation(self):
        # Arrange
        doc = Document(
            name='Test Document',
            pre_content='Hello World',
            create_user=self.user,
            status=1
        )

        # Act
        doc.save()

        # Assert
        self.assertEqual(doc.name, 'Test Document')
        self.assertEqual(doc.status, 1)
        self.assertIsNotNone(doc.create_time)
```
""",

    """## 部署与运维

### Docker 容器化部署

Docker 提供了一致性的运行环境，消除了"在我机器上能跑"的问题。

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["uwsgi", "--ini", "uwsgi.ini"]
```

### 性能监控指标

关键性能指标（KPI）：

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| API 响应时间 (P95) | < 200ms | 待测量 |
| 文档页面加载时间 | < 1s | 待测量 |
| 数据库查询次数/请求 | < 10 | 待测量 |
| 缓存命中率 | > 80% | 待测量 |

### Nginx 反向代理配置

```nginx
server {
    listen 443 ssl;
    server_name wiki.example.com;

    location /static/ {
        alias /app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
""",
]


def generate_content(doc_index, deep=False):
    """生成测试文档内容，模拟真实的 Markdown 文档"""
    parts = []
    # 标题和简介
    parts.append(random.choice(LOREM_PARAGRAPHS))

    if deep:
        parts.append(random.choice(LOREM_PARAGRAPHS))

    parts.append("---\n")
    parts.append("*本文档由性能测试工具自动生成*")
    return "\n\n".join(parts)


class Command(BaseCommand):
    help = '生成用于性能测试的文档树'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=300,
                            help='文档总数（默认 300）')
        parser.add_argument('--depth', type=int, default=4,
                            help='文档树深度（默认 4）')
        parser.add_argument('--children', type=int, default=10,
                            help='每层最多子文档数（默认 10）')
        parser.add_argument('--clear', action='store_true',
                            help='先清空现有文档')

    def handle(self, *args, **options):
        total = options['count']
        max_depth = options['depth']
        max_children = options['children']

        self.stdout.write(f'开始生成测试文档 (目标: {total} 篇, 深度: {max_depth})')

        user, _ = User.objects.get_or_create(username='Admin')
        if user.is_superuser is False:
            user.is_superuser = True
            user.is_staff = True
            user.save()

        if options['clear']:
            from backend.apps.doc.models import Doc
            Doc.objects.all().delete()
            self.stdout.write('已清空现有文档')

        # 从数据库获取已有文档数
        from backend.apps.doc.models import Doc
        existing = Doc.objects.filter(status=1, is_deleted=False).count()
        if existing >= total:
            self.stdout.write(f'已有 {existing} 篇文档，无需生成')
            return

        need = total - existing
        self.stdout.write(f'需要生成 {need} 篇文档')

        created = 0
        now = timezone.now()
        # 扩散范围（已生成文档 ID 列表，用于随机选 parent）
        created_ids = [0]  # 0 = root

        while created < need:
            depth_chunk = min(max_children, need - created)
            parent_id = random.choice(created_ids[-20:] or [0])
            parent_depth = 0
            if parent_id != 0:
                # 通过 parent_doc 链推算深度
                try:
                    p = Doc.objects.get(id=parent_id)
                    pid = p.parent_doc
                    while pid and pid != 0:
                        parent_depth += 1
                        pid = Doc.objects.filter(id=pid).values_list('parent_doc', flat=True).first() or 0
                except Doc.DoesNotExist:
                    parent_depth = 0

            if parent_depth >= max_depth:
                # 到了最大深度，不在此节点下添加子节点
                parent_id = random.choice(created_ids[:max(1, len(created_ids) // 2)] or [0])

            for i in range(depth_chunk):
                doc_name = generate_doc_name(created + i + 1, parent_depth + 1)
                doc = Doc.objects.create(
                    name=doc_name,
                    pre_content=generate_content(created + i, deep=(random.random() > 0.5)),
                    content='',
                    parent_doc=parent_id,
                    top_doc=0,
                    sort=random.randint(1, 9999),
                    create_user=user,
                    create_time=now - timedelta(days=random.randint(0, 365)),
                    status=1,
                    editor_mode=2,
                    open_children=False,
                    is_public=True,
                    is_deleted=False,
                )
                created_ids.append(doc.id)
                created += 1
                if created % 50 == 0:
                    self.stdout.write(f'  已创建 {created}/{need} 篇文档...')

        self.stdout.write(self.style.SUCCESS(f'完成！共 {Doc.objects.filter(status=1, is_deleted=False).count()} 篇文档'))


TOPICS_CN = [
    ("Java", ["基础语法", "集合框架", "多线程编程", "JVM调优", "Spring Boot实战",
              "MyBatis深入", "设计模式", "网络编程", "IO模型", "并发编程"]),
    ("Android", ["Framework开发", "性能优化", "UI渲染机制", "跨进程通信",
                 "Jetpack组件", "Kotlin协程", "单元测试", "APK包体积优化"]),
    ("Python", ["Django深入", "数据处理", "机器学习入门", "自动化脚本",
                "FastAPI实践", "异步编程", "测试框架"]),
    ("前端开发", ["React组件设计", "TypeScript类型系统", "CSS布局技巧",
                 "性能优化", "工程化实践", "状态管理"]),
    ("运维部署", ["Docker实践", "Kubernetes入门", "CI/CD流水线",
                 "Nginx配置", "监控告警", "日志分析"]),
    ("数据库", ["MySQL优化", "Redis缓存", "MongoDB应用", "SQL调优",
               "索引设计", "分库分表"]),
    ("面试准备", ["数据结构", "算法题解", "系统设计", "项目经验总结",
                 "行为面试", "技术深度追问"]),
    ("项目管理", ["需求分析", "技术方案设计", "迭代规划", "风险管理",
                 "团队协作", "代码审查"]),
]


def generate_doc_name(index, depth):
    """生成类似 MrDoc 风格的文档名"""
    topic, subtopics = random.choice(TOPICS_CN)
    subtopic = random.choice(subtopics)
    prefix = "|  " * (depth - 1) if depth > 1 else ""
    return f"{prefix}📚 {topic} - {subtopic} ({index})"
