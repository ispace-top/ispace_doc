# coding:utf-8
# 文档导入相关视图函数

from django.http.response import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from loguru import logger
from backend.apps.doc.import_utils import ImportDocxDoc
import os
import time


# 导入docx文档
@login_required()
@csrf_exempt
@require_POST
def import_doc_docx(request):
    file_type = request.POST.get('type', None)
    editor_mode = request.POST.get('editor_mode',2)
    # 上传Word文档
    if file_type == 'docx':
        import_file = request.FILES.get('import_doc_docx', None)
        if import_file:
            file_name = import_file.name
            # 限制文件大小在50mb以内
            if import_file.size > 52428800:
                return JsonResponse({'status': False, 'data': _('文件大小超出限制')})
            # 限制文件格式为.docx
            if file_name.endswith('.docx'):
                if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'import_temp')) is False:
                    os.mkdir(os.path.join(settings.MEDIA_ROOT, 'import_temp'))

                temp_file_name = str(time.time()) + '.docx'
                temp_file_path = os.path.join(settings.MEDIA_ROOT, 'import_temp/' + temp_file_name)
                with open(temp_file_path, 'wb+') as docx_file:
                    for chunk in import_file:
                        docx_file.write(chunk)
                if os.path.exists(temp_file_path):
                    import_file = ImportDocxDoc(
                        docx_file_path=temp_file_path,
                        editor_mode=editor_mode,
                        create_user=request.user
                    ).run()
                    return JsonResponse(import_file)
                else:
                    return JsonResponse({'status': False, 'data': _('上传失败')})
            else:
                return JsonResponse({'status': False, 'data': _('仅支持.docx格式')})
        else:
            return JsonResponse({'status': False, 'data': _('无有效文件')})
    else:
        return JsonResponse({'status': False, 'data': _('参数错误')})
