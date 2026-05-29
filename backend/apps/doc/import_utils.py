# coding:utf-8
# iSpaceDoc document import utilities
# 文档导入工具函数

from django.utils.translation import gettext_lazy as _
from backend.apps.doc.models import Doc,Image
from backend.apps.doc.util_upload_img import upload_generation_dir
from backend.apps.doc.utils import libreoffice_wmf_conversion,image_trim
from django.db import transaction
from django.conf import settings
from loguru import logger
from markdownify import markdownify
import mammoth
import shutil
import os
import time
import re

# 导入Word文档(.docx)
class ImportDocxDoc():
    def __init__(self,docx_file_path,editor_mode,create_user):
        self.docx_file_path = docx_file_path # docx文件绝对路径
        self.tmp_img_dir = self.docx_file_path.split('.')
        self.create_user = create_user
        self.editor_mode = int(editor_mode)

    # 转存docx文件中的图片
    def convert_img(self,image):
        image = libreoffice_wmf_conversion(image, post_process=image_trim)
        if image.alt_text:
            alt = image.alt_text.replace('\n', '').replace('\r', '')
        else:
            alt = ''
        with image.open() as image_bytes:
            file_suffix = image.content_type.split("/")[1]
            file_time_name = str(time.time())
            dir_name = upload_generation_dir()  # 获取当月文件夹名称
            # 图片在媒体文件夹内的路径，形如 /202012/12542542.jpg
            copy2_filename = dir_name + '/' + file_time_name + '.' + file_suffix
            # 文件的绝对路径 形如/home/iSpaceDoc/media/202012/12542542.jpg
            new_media_file_path = settings.MEDIA_ROOT + copy2_filename
            # 图片文件的相对url路径
            file_url = '/media' + copy2_filename

            # 图片数据写入数据库
            Image.objects.create(
                user=self.create_user,
                file_path=file_url,
                file_name=file_time_name + '.' + file_suffix,
                remark=_('本地上传'),
            )
            with open(new_media_file_path, 'wb') as f:
                f.write(image_bytes.read())
        return {"src": file_url,"alt_text":alt,"alt":alt}

    # 转换docx文件内容为HTML和Markdown
    def convert_docx(self):
        # 读取Word文件
        with open(self.docx_file_path, "rb") as docx_file:
            # 转化Word文档为HTML
            result = mammoth.convert_to_html(docx_file, convert_image=mammoth.images.img_element(self.convert_img))
            # 获取HTML内容
            html = result.value
            if self.editor_mode == 2:
                # 转化HTML为Markdown
                md = markdownify(html, heading_style="ATX")
                return md
            else:
                return html

    def run(self):
        try:
            result = self.convert_docx()
            os.remove(self.docx_file_path)
            return {'status':True,'data':result}
        except:
            os.remove(self.docx_file_path)
            return {'status':False,'data':_('读取异常')}

if __name__ == '__main__':
    imp = ImportZipProject()
    imp.read_zip(r"D:\Python XlsxWriter模块中文文档_2020-06-16.zip")