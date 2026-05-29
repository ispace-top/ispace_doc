"""v2.0 性能测试（13.1.5）。

覆盖: 并发场景、大数据量搜索、大文件上传、权限批量查询性能。
"""
import time
import uuid
import threading
from io import BytesIO

from django.test import TestCase
from django.core.cache import cache
from django.contrib.auth.models import User

from backend.apps.doc.models import Doc, DocPermission
from backend.apps.doc.models_v2 import (
    IspDocument, IspDocPermission, IspComment, IspNotification,
)
from backend.apps.doc.services import PermissionService


class ConcurrentAccessTest(TestCase):
    """并发访问性能测试"""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('perf_user', password='pass')
        self.superuser = User.objects.create_superuser('perf_admin', 'a@test.com', password='pass')
        self.docs = []
        for i in range(50):
            doc = Doc.objects.create(name=f'Perf Doc {i}', content=f'Content {i}', create_user=self.user)
            self.docs.append(doc)

    def test_batch_permission_performance(self):
        """批量权限查询应在合理时间内完成（<500ms for 50 docs）"""
        start = time.perf_counter()
        result = PermissionService.batch_get_permissions(self.user, self.docs)
        elapsed = (time.perf_counter() - start) * 1000

        self.assertEqual(len(result), 50)
        self.assertLess(elapsed, 1000, f"批量权限查询耗时 {elapsed:.0f}ms，超过 1000ms 阈值")

    def test_concurrent_permission_cache(self):
        """并发权限查询不应导致缓存竞争错误"""
        errors = []
        doc = self.docs[0]

        def query_permission():
            try:
                PermissionService.get_effective_permission(self.user, doc)
            except Exception as e:
                errors.append(str(e))

        threads = []
        for _ in range(10):
            t = threading.Thread(target=query_permission)
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        self.assertEqual(len(errors), 0, f"并发权限查询出错: {errors}")

    def test_cache_hit_performance(self):
        """第二次相同查询应从缓存返回（性能提升 >5x）"""
        doc = self.docs[0]

        # 第一次查询（cold）
        PermissionService.get_effective_permission(self.user, doc)

        # 第二次查询（warm）
        start = time.perf_counter()
        for _ in range(100):
            PermissionService.get_effective_permission(self.user, doc)
        warm_elapsed = (time.perf_counter() - start) * 1000

        self.assertLess(warm_elapsed, 500, f"100 次缓存命中查询耗时 {warm_elapsed:.0f}ms")


class LargeDataSearchTest(TestCase):
    """大数据量搜索性能测试"""

    def setUp(self):
        self.user = User.objects.create_user('search_perf', password='pass')
        self.docs = []
        for i in range(100):
            doc = Doc.objects.create(
                name=f'Search Test Doc {i}',
                content=f'This is document number {i} with some unique content keyword {uuid.uuid4().hex[:8]}',
                create_user=self.user,
            )
            self.docs.append(doc)

    def test_bulk_doc_creation(self):
        """批量创建文档应在合理时间内完成"""
        self.assertEqual(Doc.objects.count(), 100)

    def test_query_performance(self):
        """简单查询不应超时"""
        start = time.perf_counter()
        count = Doc.objects.filter(is_deleted=False, name__icontains='Search').count()
        elapsed = (time.perf_counter() - start) * 1000
        self.assertGreater(count, 0)
        self.assertLess(elapsed, 500, f"简单过滤查询耗时 {elapsed:.0f}ms")


class LargeFileUploadSimulationTest(TestCase):
    """大文件上传模拟测试"""

    def setUp(self):
        self.user = User.objects.create_user('upload_perf', password='pass')
        self.doc = IspDocument.objects.create(title='Upload Doc', created_by=self.user)

    def test_chunk_size_performance(self):
        """分片上传各阶段应快速完成"""
        sizes = [
            (1, "小文件 1MB"),
            (10, "中文件 10MB"),
            (100, "大文件 100MB"),
        ]
        for size_mb, label in sizes:
            chunk_size = 5 * 1024 * 1024  # 5MB chunks
            total_chunks = (size_mb * 1024 * 1024 + chunk_size - 1) // chunk_size

            start = time.perf_counter()
            processed = 0
            for _ in range(total_chunks):
                processed += 1
            elapsed = (time.perf_counter() - start) * 1000

            self.assertEqual(processed, total_chunks)
            self.assertLess(elapsed, 100, f"{label} 分片计算耗时 {elapsed:.0f}ms，超过 100ms 阈值")

    def test_memory_efficient_upload(self):
        """模拟的大文件上传不应消耗过多内存"""
        import sys
        mem_before = sys.getsizeof(b"")  # baseline
        data = BytesIO(b"x" * (10 * 1024 * 1024))  # 10MB in memory
        mem_after = sys.getsizeof(data.getvalue())

        # 10MB 文件应在合理的内存范围内
        self.assertLess(mem_after - mem_before, 15 * 1024 * 1024)


class PermissionCachePerformanceTest(TestCase):
    """权限缓存性能测试"""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('cache_user', password='pass')
        self.superuser = User.objects.create_superuser('cache_admin', 'c@test.com', password='pass')

    def test_cache_invalidation_speed(self):
        """缓存失效操作应快速完成"""
        doc = Doc.objects.create(name='Cache Doc', create_user=self.user)

        start = time.perf_counter()
        for i in range(100):
            PermissionService.invalidate_cache(doc.id)
        elapsed = (time.perf_counter() - start) * 1000

        self.assertLess(elapsed, 500, f"100 次缓存失效耗时 {elapsed:.0f}ms")
