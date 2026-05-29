"""WebHook Django 数据模型。

表名使用 isp_ 前缀作为 iSpaceDoc 命名空间标识。
"""
from django.db import models
from django.contrib.auth.models import User


class WebHookConfig(models.Model):
    """WebHook 订阅配置。"""

    name = models.CharField(max_length=100, verbose_name="名称")
    url = models.URLField(max_length=500, verbose_name="目标 URL")
    events = models.JSONField(default=list, verbose_name="订阅事件列表")
    secret = models.CharField(max_length=128, blank=True, default="", verbose_name="签名密钥")
    is_enabled = models.BooleanField(default=True, verbose_name="启用")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="创建者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "isp_webhook_configs"
        verbose_name = "WebHook 配置"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class WebHookDelivery(models.Model):
    """WebHook 投递日志。"""

    config = models.ForeignKey(
        WebHookConfig, on_delete=models.CASCADE, related_name="deliveries", verbose_name="配置"
    )
    event = models.CharField(max_length=50, verbose_name="事件类型")
    target_url = models.URLField(max_length=500, verbose_name="目标 URL")
    request_body = models.TextField(blank=True, default="", verbose_name="请求体")
    response_status = models.IntegerField(default=0, verbose_name="响应状态码")
    response_body = models.TextField(blank=True, default="", verbose_name="响应体")
    success = models.BooleanField(default=False, verbose_name="是否成功")
    duration_ms = models.IntegerField(default=0, verbose_name="耗时(ms)")
    attempt = models.IntegerField(default=1, verbose_name="重试次数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="投递时间")

    class Meta:
        db_table = "isp_webhook_deliveries"
        verbose_name = "WebHook 投递日志"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
