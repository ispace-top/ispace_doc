"""分片上传数据模型。"""
import uuid

from django.db import models


class ChunkedUpload(models.Model):
    """大文件分片上传会话。

    临时存储上传进度和分片数据，完成时通过 StorageBackend 组装保存。
    """

    upload_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    filename = models.CharField(max_length=255, verbose_name="原始文件名")
    file_size = models.BigIntegerField(verbose_name="文件总大小")
    chunk_size = models.IntegerField(verbose_name="分片大小")
    total_chunks = models.IntegerField(verbose_name="总分片数")
    uploaded_chunks = models.JSONField(default=list, verbose_name="已上传分片索引")
    content_type = models.CharField(max_length=128, blank=True, default="", verbose_name="MIME 类型")
    status = models.CharField(
        max_length=20, default="uploading",
        choices=(("uploading", "上传中"), ("completed", "已完成"), ("expired", "已过期")),
        verbose_name="状态",
    )
    storage_key = models.CharField(max_length=500, blank=True, default="", verbose_name="最终存储 Key")
    attachment_id = models.IntegerField(null=True, blank=True, verbose_name="附件记录 ID")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "isp_chunked_uploads"
        verbose_name = "分片上传会话"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.filename} ({self.upload_id})"

    @property
    def progress(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return len(self.uploaded_chunks) / self.total_chunks * 100

    @property
    def is_ready(self) -> bool:
        return len(self.uploaded_chunks) >= self.total_chunks
