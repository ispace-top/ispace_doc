# coding:utf-8
# iSpaceDoc API views

from django.contrib.auth.models import User
from django.shortcuts import render
from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView
from backend.apps.api.models import AppUserToken
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.authentication import SessionAuthentication
from backend.apps.doc.outline_utils import parse_outline
from backend.apps.doc.models import Doc, DocHistory, DocTemp, Image, ImageGroup, Attachment
from backend.apps.api.serializers_app import DocSerializer, DocTempSerializer, ImageSerializer, ImageGroupSerializer, AttachmentSerializer
from backend.apps.api.auth_app import AppAuth, AppMustAuth
from backend.apps.doc.services import PermissionService
from backend.apps.doc.util_upload_img import img_upload, base_img_upload
from loguru import logger
import datetime
import os

'''
响应：
    code：状态码
    data：数据

状态码：
    0：成功
    1：资源未找到
    2：无权访问
    3：需要访问码
    4：系统异常
    5：参数不正确
    6：需要登录

'''


# 生成Token的函数
def get_token_code(username):
    """
    根据用户名和时间戳来生成永不相同的token随机字符串
    :param username: 字符串格式的用户名
    :return: 字符串格式的Token
    """

    import time
    import hashlib

    timestamp = str(time.time())
    m = hashlib.md5(username.encode("utf-8"))
    # md5 要传入字节类型的数据
    m.update(timestamp.encode("utf-8"))
    return m.hexdigest()  # 将生成的随机字符串返回


# 登陆视图
class LoginView(APIView):
    '''
    登陆检测试图。
    1，接收用户发过来的用户名和密码数据
    2，校验用户密码是否正确
        - 成功就返回登陆成功,然后发Token
        - 失败就返回错误提示
    '''

    def post(self,request):
        res = {"code":0}
        # 从post 里面取数据
        # print(request.data)
        username = request.data.get("username")
        password = request.data.get("password")
        # 查询用户是否存在、密码是否匹配
        user_obj = authenticate(username=username, password=password)
        if user_obj:
            if user_obj.is_active:
                # 生成Token
                token = get_token_code(username)
                # 保存或更新token
                AppUserToken.objects.update_or_create(defaults={"token": token}, user=user_obj)
                # 将token返回给用户
                res["token"] = token
                res['username'] = username
            else:
                res['code'] = 2
                res["error"] = _('账号被禁用')

        else:
            # 登陆失败
            res["code"] = 1
            res["error"] = _("用户名或密码错误")
        return Response(res)


# 文档视图
class DocView(APIView):
    authentication_classes = (AppAuth,SessionAuthentication)

    # 获取文档
    def get(self,request):
        doc_id = request.query_params.get('did','') # 文档ID
        doc_format = request.query_params.get('type','json') # 返回格式

        # 存在文档ID，返回指定文档
        if doc_id:
            try:
                doc = Doc.objects.get(id=int(doc_id), is_deleted=False)
            except ObjectDoesNotExist:
                return Response({'code': 1, 'data': _('文档不存在')})

            # 检查权限：公开文档或有 view 权限
            if not doc.is_public:
                if request.user.is_authenticated:
                    perm = PermissionService.get_effective_permission(request.user, doc)
                    if perm is None:
                        return Response({'code': 2, 'data': _('无权访问')})
                else:
                    return Response({'code': 6, 'data': _('请登录后操作')})

            if doc_format == 'json':
                serializer = DocSerializer(doc)
                resp = {'code':0,'data':serializer.data}
                return Response(resp)
            elif doc_format == 'html':
                logger.info(_("返回HTML"))
                return render(request,'app_api/single_doc_detail.html',locals())
        # 不存在文档ID，返回用户自己的文档列表
        else:
            if request.auth:
                doc_list = Doc.objects.filter(
                    create_user=request.user,
                    is_deleted=False
                ).order_by('-modify_time')
                page = PageNumberPagination()  # 实例化一个分页器
                page_docs = page.paginate_queryset(doc_list, request, view=self)  # 进行分页查询
                serializer = DocSerializer(page_docs, many=True)  # 对分页后的结果进行序列化处理
                resp = {
                    'code': 0,
                    'data': serializer.data,
                    'count': doc_list.count()
                }
                return Response(resp)
            else:
                return Response({'code': 6, 'data': _('请登录后操作')})

    # 新建文档
    def post(self, request):
        try:
            parent_doc = request.data.get('parent_doc','')
            doc_name = request.data.get('doc_name','')
            doc_content = request.data.get('content','')
            pre_content = request.data.get('pre_content','')
            sort = request.data.get('sort','')
            status = request.data.get('status',1)

            if doc_name != '':
                outline = parse_outline(pre_content, 2)  # API app 默认 Vditor/Markdown
                doc = Doc.objects.create(
                    name=doc_name,
                    content=doc_content,
                    pre_content=pre_content,
                    parent_doc=int(parent_doc) if parent_doc != '' else 0,
                    top_doc=0,
                    sort=sort if sort != '' else 99,
                    create_user=request.user,
                    status=status,
                    outline=outline
                )
                return Response({'code':0,'data':{'doc':doc.id}})
            else:
                return Response({'code':5,'data':_('请确认文档标题正确')})
        except Exception as e:
            logger.exception(_("api新建文档异常"))
            return Response({'code':4,'data':_('请求出错')})

    # 修改文档
    def put(self, request):
        try:
            doc_id = request.data.get('doc_id','') # 文档ID
            parent_doc = request.data.get('parent_doc', '') # 上级文档ID
            doc_name = request.data.get('doc_name', '') # 文档名称
            doc_content = request.data.get('content', '') # 文档内容
            pre_content = request.data.get('pre_content', '') # 文档Markdown格式内容
            sort = request.data.get('sort', '') # 文档排序
            status = request.data.get('status',1) # 文档状态

            if doc_id != '' and doc_name != '':
                doc = Doc.objects.get(id=doc_id, is_deleted=False)
                # 验证用户有权限修改文档 - 仅文档创建者
                if request.user == doc.create_user:
                    # 将现有文档内容写入到文档历史中
                    DocHistory.objects.create(
                        doc=doc,
                        pre_content=doc.pre_content,
                        create_user=request.user
                    )
                    # 更新文档内容
                    em = doc.editor_mode if doc.editor_mode else 2
                    source = pre_content if em == 2 else doc_content
                    outline = parse_outline(source, em)
                    Doc.objects.filter(id=int(doc_id)).update(
                        name=doc_name,
                        content=doc_content,
                        pre_content=pre_content,
                        parent_doc=int(parent_doc) if parent_doc != '' else 0,
                        sort=sort if sort != '' else 99,
                        modify_time=datetime.datetime.now(),
                        status=status,
                        outline=outline
                    )
                    return Response({'code': 0,'data':_('修改成功')})
                else:
                    return Response({'code':2,'data':_('未授权请求')})
            else:
                return Response({'code': 5,'data':_('参数错误')})
        except Exception as e:
            logger.exception(_("api修改文档出错"))
            return Response({'code':4,'data':_('请求出错')})

    # 删除文档
    def delete(self, request):
        try:
            # 获取文档ID
            doc_id = request.data.get('doc_id', None)
            if doc_id:
                # 查询文档
                try:
                    doc = Doc.objects.get(id=doc_id, is_deleted=False)
                except ObjectDoesNotExist:
                    return Response({'code': 1, 'data': _('文档不存在')})

                if request.user == doc.create_user:
                    # 软删除当前文档
                    doc.is_deleted = True
                    doc.deleted_at = timezone.now()
                    doc.deleted_by = request.user
                    doc.save()
                    # 修改其下级所有文档为已删除
                    chr_doc = Doc.objects.filter(parent_doc=doc_id, is_deleted=False)
                    chr_doc_ids = chr_doc.values_list('id', flat=True)
                    chr_doc.update(is_deleted=True, deleted_at=timezone.now(), deleted_by=request.user)
                    Doc.objects.filter(
                        parent_doc__in=chr_doc_ids,
                        is_deleted=False
                    ).update(is_deleted=True, deleted_at=timezone.now(), deleted_by=request.user)

                    return Response({'code': 0, 'data': _('删除完成')})
                else:
                    return Response({'code': 2, 'data': _('非法请求')})
            else:
                return Response({'code': 5, 'data': _('参数错误')})
        except Exception as e:
            logger.exception(_("api删除文档出错"))
            return Response({'code': 4, 'data': _('请求出错')})


# 文档模板视图
class DocTempView(APIView):
    authentication_classes = (AppMustAuth,SessionAuthentication)

    # 获取文档模板
    def get(self, request):
        temp_id = request.query_params.get('id','')
        if temp_id != '':
            doctemp = DocTemp.objects.get(id=int(temp_id))
            if request.user == doctemp.create_user:
                serializer = DocTempSerializer(doctemp)
                resp = {'code': 0, 'data': serializer.data}
            else:
                resp = {'code':2,'data':_('无权操作')}
        else:
            doctemps = DocTemp.objects.filter(create_user=request.user)
            page = PageNumberPagination()
            page_doctemps = page.paginate_queryset(doctemps,request,view=self)
            serializer = DocTempSerializer(page_doctemps,many=True)
            resp = {'code':0,'data':serializer.data,'count':doctemps.count()}
        return Response(resp)

    def post(self, request):
        try:
            if request.auth:
                name = request.data.get('name','')
                content = request.data.get('content','')
                if name != '':
                    doctemp = DocTemp.objects.create(
                        name = name,
                        content = content,
                        create_user=request.user
                    )
                    doctemp.save()
                    return Response({'code':0,'data':_('创建成功')})
                else:
                    return Response({'code':5,'data':_('模板标题不能为空')})
            else:
                return Response({'code':6,'data':_('请登录')})
        except Exception as e:
            logger.exception(_("api创建文档模板出错"))
            return Response({'code':4,'data':_('请求出错')})

    def put(self, request):
        try:
            doctemp_id = request.data.get('doctemp_id','')
            name = request.data.get('name','')
            content = request.data.get('content','')
            if doctemp_id != '' and name !='':
                doctemp = DocTemp.objects.get(id=doctemp_id)
                # 验证请求用户为文档模板的创建者
                if request.user == doctemp.create_user:
                    doctemp.name = name
                    doctemp.content = content
                    doctemp.save()
                    return Response({'code':0,'data':_('修改成功')})
                else:
                    return Response({'code':2,'data':_('非法操作')})
            else:
                return Response({'code':5,'data':_('参数错误')})
        except Exception as e:
            logger.exception(_("api修改文档模板出错"))
            return Response({'code':4,'data':_('请求出错')})

    def delete(self, request):
        try:
            doctemp_id = request.data.get('doctemp_id', '')
            if doctemp_id != '':
                doctemp = DocTemp.objects.get(id=doctemp_id)
                if request.user == doctemp.create_user:
                    doctemp.delete()
                    return Response({'code': 0, 'data': _('删除完成')})
                else:
                    return Response({'code': 2, 'data': _('非法请求')})
            else:
                return Response({'code': 5, 'data': _('参数错误')})
        except Exception as e:
            logger.exception(_("api删除文档模板出错"))
            return Response({'code': 4, 'data': _('请求出错')})


# 图片视图
class ImageView(APIView):
    authentication_classes = (AppMustAuth,SessionAuthentication)

    # 获取
    def get(self, request):
        g_id = int(request.query_params.get('group', 0))  # 图片分组id
        if int(g_id) == 0:
            image_list = Image.objects.filter(user=request.user)  # 查询所有图片
        elif int(g_id) == -1:
            image_list = Image.objects.filter(user=request.user, group_id=None)  # 查询指定分组的图片
        else:
            image_list = Image.objects.filter(user=request.user, group_id=g_id)  # 查询指定分组的图片
        page = PageNumberPagination()
        page_images = page.paginate_queryset(image_list,request,view=self)
        serializer = ImageSerializer(page_images,many=True)
        resp = {'code':0,'data':serializer.data,'count':image_list.count()}
        return Response(resp)

    # 上传
    def post(self, request):
        img = request.data.get("api_img_upload", None)  # 编辑器上传
        # manage_upload = request.data.get('manage_upload', None)  # 图片管理上传
        dir_name = request.data.get('dirname', '')
        base_img = request.data.get('base', None)
        if img:  # 上传普通图片文件
            result = img_upload(img, dir_name, request.user)
            resp = {'code':0,'data':result['url']}
        # elif manage_upload:
        #     result = img_upload(manage_upload, dir_name, request.user)
        #     resp = {'code': 0, 'data': result['url']}
        elif base_img:  # 上传base64编码图片
            result = base_img_upload(base_img, dir_name, request.user)
            resp = {'code': 0, 'data': result['url']}
        else:
            resp = {"code": 5, "message": _("出错信息")}
        return Response(resp)

    # 删除
    def delete(self, request):
        from backend.apps.doc.storage import get_storage

        img_id = request.data.get('id', '')
        img = Image.objects.get(id=img_id)
        if img.user != request.user:
            return Response({'code': 2, 'data': _('未授权请求')})
        # 通过存储后端删除文件
        storage = get_storage()
        storage_key = img.file_path
        if storage_key:
            try:
                storage.delete(storage_key)
            except Exception:
                pass
        img.delete()
        return Response({'code': 0, 'data': 'ok'})


# 图片分组视图
class ImageGroupView(APIView):
    authentication_classes = (AppMustAuth,SessionAuthentication)

    def get(self, request):
        try:
            group_list = []
            all_cnt = Image.objects.filter(user=request.user).count()
            non_group_cnt = Image.objects.filter(group_id=None,user=request.user).count()
            group_list.append({'group_name': _('全部图片'), 'group_cnt': all_cnt, 'group_id': 0})
            group_list.append({'group_name': _('未分组'), 'group_cnt': non_group_cnt, 'group_id': -1})
            groups = ImageGroup.objects.filter(user=request.user)  # 查询所有分组
            for group in groups:
                group_cnt = Image.objects.filter(group_id=group).count()
                item = {
                    'group_id': group.id,
                    'group_name': group.group_name,
                    'group_cnt': group_cnt
                }
                group_list.append(item)
            return Response({'code': 0, 'data': group_list})
        except:
            return Response({'code': 4, 'data': _('出现错误')})

    def post(self, request):
        group_name = request.data.get('group_name', '')
        if group_name not in ['', _('默认分组'), _('未分组')]:
            ImageGroup.objects.create(
                user=request.user,
                group_name=group_name
            )
            return Response({'code': 0, 'data': 'ok'})
        else:
            return Response({'code': 5, 'data': _('名称无效')})

    def put(self, request):
        group_name = request.data.get("group_name", '')
        if group_name not in ['', _('默认分组'), _('未分组')]:
            group_id = request.POST.get('group_id', '')
            ImageGroup.objects.filter(id=group_id,user=request.user).update(group_name=group_name)
            return Response({'code': 0, 'data': 'ok'})
        else:
            return Response({'code': 5, 'data': _('名称无效')})

    def delete(self, request):
        try:
            group_id = request.data.get('group_id', '')
            group = ImageGroup.objects.get(id=group_id, user=request.user)  # 查询分组
            images = Image.objects.filter(group_id=group_id).update(group_id=None)  # 移动图片到未分组
            group.delete()  # 删除分组
            return Response({'code': 0, 'data': 'ok'})
        except:
            return Response({'code': 4, 'data': _('删除错误')})


# 附件视图
class AttachmentView(APIView):
    authentication_classes = (AppMustAuth,SessionAuthentication)

    # 文件大小 字节转换
    def sizeFormat(size, is_disk=False, precision=2):
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
                r = '{}{}'.format(round(size, precision), i)
                return r

    def get(self, request):
        attachment_list = []
        attachments = Attachment.objects.filter(user=request.user)
        for a in attachments:
            item = {
                'filename': a.file_name,
                'filesize': a.file_size,
                'filepath': a.file_path.name,
                'filetime': a.create_time
            }
            attachment_list.append(item)
        return Response({'code': 0, 'data': attachment_list})

    def post(self, request):
        from backend.apps.doc.storage.security import sanitize_filename, detect_content_type

        attachment = request.data.get('attachment_upload', None)
        if not attachment:
            return Response({'code': 5, 'data': _('无效文件')})

        attachment_name = sanitize_filename(attachment.name)
        attachment_size = self.sizeFormat(attachment.size)
        # 限制附件大小在50mb以内
        if attachment.size > 52428800:
            return Response({'code': False, 'data': _('文件大小超出限制')})
        # 限制附件为ZIP格式
        if not attachment_name.lower().endswith('.zip'):
            return Response({'code': 5, 'data': _('不支持的格式')})

        # MIME 检测
        file_header = attachment.read(512)
        attachment.seek(0)
        detected = detect_content_type(file_header)
        if detected != "application/zip" and detected != "application/octet-stream":
            return Response({'code': 5, 'data': _('文件格式与内容不匹配')})

        attachment.name = attachment_name
        a = Attachment.objects.create(
            file_name=attachment_name,
            file_size=attachment_size,
            file_path=attachment,
            user=request.user
        )
        return Response({'code': 0, 'data': {'name': attachment_name, 'url': a.file_path.name}})

    def delete(self, request):
        attach_id = request.data.get('attach_id', '')
        attachment = Attachment.objects.filter(id=attach_id, user=request.user)  # 查询附件
        for a in attachment:  # 遍历附件
            a.file_path.delete()  # 删除文件
        attachment.delete()  # 删除数据库记录
        return Response({'code': 0, 'data': 'ok'})