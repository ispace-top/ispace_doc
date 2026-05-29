# coding:utf-8

from django.utils.translation import gettext_lazy as _
from backend.apps.admin.models import SysSetting
from backend.apps.doc.models import Attachment
from backend.apps.doc.storage.security import detect_content_type, sanitize_filename
from backend.apps.admin.utils import is_zip_bomb
from loguru import logger
import os
import tempfile
import datetime

# 文件大小 字节转换
def fileSizeFormat(size, is_disk=False, precision=2):
    '''
    size format for human.
        byte      ---- (B)
        kilobyte  ---- (KB)
        megabyte  ---- (MB)
        gigabyte  ---- (GB)
        terabyte  ---- (TB)
        petabyte  ---- (PB)
        exabyte   ---- (EB)
        zettabyte ---- (ZB)
        yottabyte ---- (YB)
    '''
    formats = ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    unit = 1000.0 if is_disk else 1024.0
    if not (isinstance(size, float) or isinstance(size, int)):
        raise TypeError('a float number or an integer number is required!')
    if size < 0:
        raise ValueError('number must be non-negative')
    for i in formats:
        size /= unit
        if size < unit:
            r = '{}{}'.format(round(size, precision),i)
            return r

def handle_attachment_upload(attachment, user, request):
    if not attachment:
        return {'status': False, 'data': _('无效文件')}

    # 清理文件名，防止路径穿越
    attachment_name = sanitize_filename(attachment.name)
    attachment_size = fileSizeFormat(attachment.size)

    # 限制附件大小
    try:
        allow_attachment_size = SysSetting.objects.get(types='doc', name='attachment_size')
        allow_attach_size = int(allow_attachment_size.value) * 1048576
    except Exception:
        allow_attach_size = 52428800  # 默认50MB
    if attachment.size > allow_attach_size:
        return {'status': False, 'data': _('文件大小超出限制')}

    # 限制附件格式
    try:
        attachment_suffix_list = SysSetting.objects.get(types='doc', name='attachment_suffix')
        attachment_suffix_list = attachment_suffix_list.value.split(',')
        if attachment_suffix_list == ['']:
            attachment_suffix_list = ['zip']
    except Exception:
        attachment_suffix_list = ['zip']

    file_suffix = attachment_name.split('.')[-1].lower()
    if file_suffix not in attachment_suffix_list:
        return {'status': False, 'data': _('不支持的格式')}

    # 读取文件前几个字节用于 MIME 检测
    file_header = attachment.read(512)
    attachment.seek(0)
    detected_mime = detect_content_type(file_header)
    if detected_mime != "application/octet-stream":
        mime_subtype = detected_mime.split("/")[-1]
        subtype_map = {"jpeg": "jpg"}
        mapped = subtype_map.get(mime_subtype, mime_subtype)
        if mapped not in attachment_suffix_list:
            logger.warning(f"附件 MIME 类型不匹配: 文件名={attachment_name}, 检测={detected_mime}")
            return {'status': False, 'data': _('文件格式与内容不匹配')}

    # 检测ZIP炸弹
    if file_suffix == 'zip':
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            for chunk in attachment.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        if is_zip_bomb(temp_file_path):
            os.remove(temp_file_path)
            return {'status': False, 'data': _('检测到可能的ZIP炸弹')}

        os.remove(temp_file_path)
        attachment.seek(0)

    # 更新文件名（经过清理）
    attachment.name = attachment_name
    try:
        a = Attachment.objects.create(
            file_name=attachment_name,
            file_size=attachment_size,
            file_path=attachment,
            user=user
        )
        return {'status': True, 'data': {'name': attachment_name, 'url': a.file_path.name}}
    except Exception as e:
        logger.error(f"上传附件失败: {repr(e)}")
        return {'status': False, 'data': _('上传附件失败')}