# coding:utf-8
from django.http import HttpResponse,JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required # 登录需求装饰器
from django.utils.translation import gettext_lazy as _
import datetime,time,json,base64,os,uuid,io
from backend.apps.doc.models import Image,ImageGroup,Attachment
from backend.apps.doc.utils import validate_url
from backend.apps.doc.storage import get_storage
from backend.apps.doc.storage.security import generate_storage_key, detect_content_type, validate_content_type
from backend.apps.doc.util_upload_file import fileSizeFormat as format_size
from backend.apps.admin.models import SysSetting
from loguru import logger
import requests
import random


@login_required()
@csrf_exempt
def upload_ice_img(request):
    ##################
    # 如果需要使用ice自带的多文件上传，请修改ice的js文件中的附件上传部分代码如下：
    # 
    # for(var i=0;i<this.files.length;i++){
    # 	formData.append('file_' + i, this.files[i]);
    # }
    # formData.append('upload_num', i);
    # formData.append('upload_type', "files");
    ##################
    try:
        up_type = request.POST.get('upload_type','')
        up_num = request.POST.get('upload_num','')   
        iceEditor_img = str(request.POST.get('iceEditor-img',''))
    except:
       pass    
    if up_type == "files":
        # 多文件上传功能，需要修改js文件
        res_dic = {'length':int(up_num)}
        for  i in range(0,int(up_num)):
            file_obj = request.FILES.get('file_' + str(i))
            result = ice_save_file(file_obj,request.user)
            res_dic[i] = result
    elif iceEditor_img.lower().startswith('http'):
        res_dic = ice_url_img_upload(iceEditor_img,request.user)       
    else:
        # 粘贴上传和单文件上传
        file_obj = request.FILES.get('file[]')
        result = ice_save_file(file_obj,request.user)           
        res_dic = {0:result,"length":1,'other_msg':iceEditor_img}         #一个文件，直接把文件数量固定了
    return JsonResponse(res_dic)


def ice_save_file(file_obj,user):
    # 默认保留支持ice单文件上传功能，可以iceEditor中开启
    file_suffix = str(file_obj).split(".")[-1].lower()
    # 允许上传文件类型，ice粘贴上传为blob
    if file_suffix == 'blob':
        file_suffix = 'png'
    allow_suffix = settings.ALLOWED_IMG
    is_images = ["jpg", "jpeg", "gif", "png", "bmp", "webp"]
    if file_suffix not in allow_suffix:
        return {"error": _("文件格式不允许")}

    # 读取文件内容用于 MIME 检测
    file_content = file_obj.read()
    is_allowed, detected_mime = validate_content_type(file_content, allow_suffix)
    if not is_allowed:
        return {"error": _("文件格式与内容不匹配")}

    # 通过存储后端上传
    key = generate_storage_key("images", file_suffix)
    storage = get_storage()
    content_type = detected_mime or f"image/{file_suffix}"
    result = storage.upload(io.BytesIO(file_content), key, content_type=content_type)

    file_url = result.url
    file_name = os.path.basename(key)

    if file_suffix in is_images:
        Image.objects.create(
            user=user,
            file_path=file_url,
            file_name=file_name,
            remark=_("iceEditor上传")
        )
    else:
        Attachment.objects.create(
            user=user,
            file_path=file_url,
            file_name=file_name,
            file_size=format_size(result.size)
        )
    return {"error":0, "name": str(file_obj),'url':file_url}


# ice_url图片上传
def ice_url_img_upload(url,user):
    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    r = requests.get(url, headers=header, stream=True)
    if r.status_code != 200:
        return {"error":0, "name": {}, "file":{}}

    remote_type = r.headers.get("Content-Type", "").split("/")[-1]
    if remote_type not in settings.ALLOWED_IMG:
        logger.error("上传了不允许的URL图片：{}".format(url))
        return {"error": 0, "name": {}, "file": {}}

    file_content = r.content
    is_allowed, detected_mime = validate_content_type(file_content, settings.ALLOWED_IMG)
    if not is_allowed:
        logger.error("URL图片内容与声明类型不匹配：{}".format(url))
        return {"error": 0, "name": {}, "file": {}}

    suffix = remote_type if remote_type in settings.ALLOWED_IMG else "png"
    key = generate_storage_key("images", suffix)
    storage = get_storage()
    result = storage.upload(io.BytesIO(file_content), key, content_type=detected_mime)

    Image.objects.create(
        user=user,
        file_path=result.url,
        file_name=os.path.basename(key),
        remark=_('iceurl粘贴上传'),
    )
    return {"error":0, "name": os.path.basename(key), 'url': result.url}


@login_required()
@csrf_exempt
def upload_img(request):
    ##################
    # {"success": 0, "message": "出错信息"}
    # {"success": 1, "url": "图片地址"}
    ##################
    img = request.FILES.get("editormd-image-file", None) or request.FILES.get("vditor-image-file", None) # 编辑器上传
    manage_upload = request.FILES.get('manage_upload',None) # 图片管理上传
    try:
        url_img = json.loads(request.body.decode())['url']
        url_img = validate_url(url_img)
        if url_img is False:
            return JsonResponse({"success": 0, "message": _("无效的URL！")})
    except:
        url_img = None
    dir_name = request.POST.get('dirname','')
    base_img = request.POST.get('base',None)
    group_id = request.POST.get('group_id',0)

    if int(group_id) not in [0,-1]:
        try:
            group_id = ImageGroup.objects.get(id=group_id)
        except:
            group_id = None
    else:
        group_id = None

    # 上传普通图片文件
    if img:
        result = img_upload(img, dir_name,request.user)
    # 图片管理上传
    elif manage_upload:
        result = img_upload(manage_upload, dir_name, request.user, group_id=group_id)
    # 上传base64编码图片
    elif base_img:
        result = base_img_upload(base_img,dir_name,request.user)
    # 上传图片URL地址
    elif url_img:
        if url_img.startswith("data:image"):# 以URL形式上传的BASE64编码图片
            result = base_img_upload(url_img, dir_name, request.user)
        else:
            result = url_img_upload(url_img,dir_name,request.user)
    else:
        result = {"success": 0, "message": _("上传出错")}
    return JsonResponse(result)


# 目录创建（兼容旧代码，新逻辑使用 generate_storage_key）
def upload_generation_dir(dir_name=''):
    today = datetime.datetime.today()
    dir_name = dir_name + '/%d%02d/' %(today.year,today.month)
    if not os.path.exists(settings.MEDIA_ROOT + dir_name):
        os.makedirs(settings.MEDIA_ROOT + dir_name)
    return dir_name


# 普通图片上传
def img_upload(files, dir_name, user, group_id=None):
    allow_suffix = settings.ALLOWED_IMG
    file_suffix = files.name.split(".")[-1].lower()

    if file_suffix not in allow_suffix:
        return {"success": 0, "message": _("图片格式不正确")}

    # 判断图片的大小
    try:
        allow_image_size = SysSetting.objects.get(types='doc', name='img_size')
        allow_img_size = int(allow_image_size.value) * 1048576
    except Exception:
        allow_img_size = 10485760
    if files.size > allow_img_size:
        return {"success": 0, "message": _("图片大小超出{}MB".format(allow_img_size / 1048576))}

    # 读取并验证真实 MIME 类型
    file_content = files.read()
    is_allowed, detected_mime = validate_content_type(file_content, allow_suffix)
    if not is_allowed:
        return {"success": 0, "message": _("图片格式与内容不匹配")}

    # 通过存储后端上传
    prefix = f"images/{dir_name}" if dir_name else "images"
    key = generate_storage_key(prefix, file_suffix)
    storage = get_storage()
    result = storage.upload(io.BytesIO(file_content), key, content_type=detected_mime)

    Image.objects.create(
        user=user,
        file_path=result.url,
        file_name=os.path.basename(key),
        remark=_('本地上传'),
        group=group_id,
    )
    return {"success": 1, "url": result.url, 'message': _('上传图片成功')}

# 解析image/png获取扩展名
def getImageExtensionName(temps):
    if len(temps) == 2:
        #image/png
        temps = temps[0].split('image/')
        if len(temps) == 2:
            ## 如果文件传了扩展名，就取扩展名的文件类型，判断图片格式是否允许上传
            if temps[-1] in settings.ALLOWED_IMG:
                return "." + temps[-1]
    return ".png" 

# base64编码图片上传
def base_img_upload(files,dir_name, user):
    temps = files.split(';base64,')
    files_str = temps[-1]
    extensionName = getImageExtensionName(temps)

    files_base = base64.b64decode(files_str)
    suffix = extensionName.lstrip(".")
    if suffix not in settings.ALLOWED_IMG:
        suffix = "png"

    is_allowed, detected_mime = validate_content_type(files_base, settings.ALLOWED_IMG)
    if not is_allowed:
        return {"success": 0, "message": _("图片格式与内容不匹配")}

    prefix = f"images/{dir_name}" if dir_name else "images"
    key = generate_storage_key(prefix, suffix)
    storage = get_storage()
    result = storage.upload(io.BytesIO(files_base), key, content_type=detected_mime)

    Image.objects.create(
        user=user,
        file_path=result.url,
        file_name=os.path.basename(key),
        remark=_('粘贴上传'),
    )
    return {"success": 1, "url": result.url, 'message': _('上传图片成功')}


# url图片上传
def url_img_upload(url,dir_name,user):
    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        r = requests.get(url, headers=header, stream=True)
        if r.status_code != 200:
            return {'msg': '', 'code': 1, 'data': {}}

        remote_type = r.headers.get("Content-Type", "").split("/")[-1]
        if remote_type not in settings.ALLOWED_IMG:
            logger.error("上传了不允许的URL图片：{}".format(url))
            return {'msg': '', 'code': 1, 'data': {}}

        file_content = r.content
        is_allowed, detected_mime = validate_content_type(file_content, settings.ALLOWED_IMG)
        if not is_allowed:
            logger.error("URL图片内容与声明类型不匹配：{}".format(url))
            return {'msg': '', 'code': 1, 'data': {}}

        suffix = remote_type if remote_type in settings.ALLOWED_IMG else "png"
        prefix = f"images/{dir_name}" if dir_name else "images"
        key = generate_storage_key(prefix, suffix)
        storage = get_storage()
        result = storage.upload(io.BytesIO(file_content), key, content_type=detected_mime)

        Image.objects.create(
            user=user,
            file_path=result.url,
            file_name=os.path.basename(key),
            remark=_('粘贴上传'),
        )
        return {'msg': '', 'code': 0, 'data': {'originalURL': url, 'url': result.url}}
    except Exception as e:
        logger.error("上传URL图片异常：{}".format(repr(e)))
        return {'msg': '', 'code': 1, 'data': {}}