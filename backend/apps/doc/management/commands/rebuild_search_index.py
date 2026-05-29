"""重建搜索索引。

用法:
    python manage.py rebuild_search_index          # 全量重建
    python manage.py rebuild_search_index --ids 1,2,3  # 增量更新指定文档
    python manage.py rebuild_search_index --clear      # 仅清空索引
"""
from django.core.management.base import BaseCommand
from backend.apps.doc.models import Doc
from backend.apps.doc.search.backends import get_search, SearchDocument


class Command(BaseCommand):
    help = "重建搜索引擎索引"

    def add_arguments(self, parser):
        parser.add_argument("--ids", type=str, help="指定文档 ID，逗号分隔")
        parser.add_argument("--clear", action="store_true", help="清空索引（不重建）")

    def handle(self, *args, **options):
        search = get_search()
        self.stdout.write(f"搜索后端: {search.name}")

        if options["clear"]:
            self.stdout.write("正在清空索引...")
            search.clear_index()
            self.stdout.write(self.style.SUCCESS("索引已清空"))
            return

        if options["ids"]:
            doc_ids = [int(x.strip()) for x in options["ids"].split(",") if x.strip()]
            docs = Doc.objects.filter(id__in=doc_ids, status__in=[0, 1])
        else:
            docs = Doc.objects.filter(status__in=[0, 1])

        total = docs.count()
        if total == 0:
            self.stdout.write("没有需要索引的文档")
            return

        self.stdout.write(f"正在重建索引 ({total} 篇文档)...")

        if options["ids"]:
            search_docs = [_doc_to_search_doc(doc) for doc in docs]
            for sd in search_docs:
                search.index_doc(sd)
        else:
            search.clear_index()
            batch = []
            batch_size = 500
            for i, doc in enumerate(docs.iterator(chunk_size=batch_size)):
                batch.append(_doc_to_search_doc(doc))
                if len(batch) >= batch_size:
                    search.index_docs(batch)
                    self.stdout.write(f"  已索引 {min(i + 1, total)}/{total}")
                    batch = []
            if batch:
                search.index_docs(batch)

        stats = search.stats()
        self.stdout.write(self.style.SUCCESS(
            f"索引重建完成。后端: {stats['backend']}, 文档数: {stats.get('doc_count', total)}"
        ))


def _doc_to_search_doc(doc: Doc) -> SearchDocument:
    return SearchDocument(
        id=str(doc.id),
        title=doc.name or "",
        content=doc.pre_content or "",
        author=doc.create_user.username if doc.create_user else "",
        author_id=doc.create_user_id or 0,
        created_at=doc.create_time.strftime("%Y-%m-%d %H:%M:%S") if doc.create_time else "",
        updated_at=doc.modify_time.strftime("%Y-%m-%d %H:%M:%S") if doc.modify_time else "",
        status="published" if doc.status == 1 else "draft",
    )
