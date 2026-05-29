from django.shortcuts import render
from django.http.response import JsonResponse,HttpResponse
from django.views.decorators.csrf import csrf_exempt # CSRF装饰器
from django.views.decorators.http import require_http_methods,require_safe,require_GET
from django.contrib.auth.decorators import login_required # 登录需求装饰器
from django.core.exceptions import PermissionDenied,ObjectDoesNotExist
from django.conf import settings
from django.contrib.auth import authenticate,login,logout # 认证相关方法
from django.contrib.auth.models import User # Django默认用户模型
from django.core.paginator import Paginator,PageNotAnInteger,EmptyPage,InvalidPage # 后端分页
from django.shortcuts import render,redirect
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from backend.apps.doc.util_upload_img import upload_generation_dir,base_img_upload,url_img_upload,img_upload
from backend.apps.doc.util_upload_file import handle_attachment_upload
from backend.apps.doc.utils import find_doc_next,find_doc_previous
from backend.apps.doc.outline_utils import parse_outline
from backend.apps.api.models import UserToken
from backend.apps.doc.models import Doc, DocHistory, Image
from backend.apps.api.serializers_app import ImageSerializer
from backend.apps.api.utils import remove_doc_tag
from loguru import logger
import time,hashlib
import traceback,json
import datetime

# iSpaceDoc 基于用户的Token访问API模块

# 用户通过该url获取服务器时间戳，便于接口访问
# url范例：http://127.0.0.1:8000/api/get_timestamp/
def get_timestamp(request):
    now_time = str(int(time.time()))
    return JsonResponse({'status':True,'data':now_time})

def oauth0(request):
    # url范例：http://127.0.0.1:8000/api/oauth0/?username=huyang&timestamp=1608797025&randstr=123adsfadf&hashstr=c171ce95ef3789d922cb6663c678c255&redirecturl=http%3A%2F%2F127.0.0.1%3A8000%2Fproject-1%2Fdoc-10%2F
    if request.method == 'GET':
        try:
            username = request.GET.get("username","")
            timestamp = request.GET.get("timestamp","")
            randstr = request.GET.get("randstr","")
            hashstr = request.GET.get("hashstr","")
            redirecturl = request.GET.get("redirecturl","/") 
            if redirecturl == "" :
                # 必须用判断的方式，否则url里提交redirecturl= 还是为空
                redirecturl =  "/"                
            if "" not in [username,timestamp,randstr,hashstr] :
                # 都不为空，才验证哦
                # 1 、验证timestamp的时效性
                nowtime = int (time.time())
                # 时间戳失效时间，默认为3600，可以改短，如30，严格点5秒，如果使用5秒，请求前，需要通过get_timestamp获取服务器时间戳，否则因为和服务器时间差导致无法验证通过
                if (nowtime - int(timestamp)) > 3600 :                    
                    raise ValueError(_('链接已失效，请从合法路径访问，或联系管理员！'))
                # 2、获取userid的Token
                user = User.objects.get(username=username)                                
                if user is None:
                    raise ValueError(_('请求用户出错！'))
                ID = user.id
                State = user.is_active
                if State == 1 and ID is not None:
                    usertoken = UserToken.objects.get(user_id=ID)
                    token = usertoken.token
                else:
                    raise ValueError(_('非法用户！'))
            
                # 3、 验证hash的正确性
                final_str  =  str(randstr) + str(timestamp) + str(username) + token
                md5 = hashlib.md5(final_str.encode("utf-8")).hexdigest()        # 不支持中文
                if md5 == hashstr:
                    # 用户验证成功                   
                    login(request,user)
                    from urllib.parse import unquote
                    newurl = unquote(redirecturl)
                    return redirect(newurl)
                else:                    
                    raise ValueError(_('验证失败,可能是用户名或Token不正确!详情请联系管理员！'))
            else:
                raise ValueError(_('关键字验证失败，请联系管理员！部分关键字为空'))
        except ValueError as e:
            errormsg = e
            return render(request, 'app_api/api404.html', locals())
        except :
            errormsg = _("API接口运行出错！")
            return render(request, 'app_api/api404.html', locals())
    else:
        return JsonResponse({'status':False,'data':'Nothing Here'}) 


# Token管理页面
@require_http_methods(['POST','GET'])
@login_required()
def manage_token(request):
    if request.method == 'GET':
        try:
            token = UserToken.objects.get(user=request.user).token # 查询用户Token
        except ObjectDoesNotExist:
            token = _('你还没有生成过Token！')
        except:
            if settings.DEBUG:
                logger.exception(_("Token管理页面异常"))
        return render(request,'app_api/manage_token.html',locals())
    elif request.method == 'POST':
        try:
            user = request.user
            now_time =str(time.time())
            string = 'user_{}_time_{}'.format(user,now_time).encode('utf-8')
            token_str = hashlib.sha224(string).hexdigest()
            user_token = UserToken.objects.filter(user=user)
            if user_token.exists():
                UserToken.objects.get(user=user).delete()
            UserToken.objects.create(
                user=user,
                token=token_str
            )
            return JsonResponse({'status':True,'data':token_str})
        except:
            logger.exception(_("用户Token生成异常"))
            return JsonResponse({'status':False,'data':_('生成出错，请重试！')})


# 检查用户Token
def check_token(request):
    token = request.GET.get('token', '')
    try:
        token = UserToken.objects.get(token=token)
        user = token.user
        data = {
            'is_writer':True,
            'username': user.first_name if user.first_name else user.username,  # 用户昵称
            'user_type': 'admin' if user.is_superuser else 'user',  # 用户类型
        }
        return JsonResponse({'status':True,'data':data})
    except:
        return JsonResponse({'status':False})

# 获取文档列表（原文集文档列表，现改为获取用户自己的文档）
def get_docs(request):
    token = request.GET.get('token', '')
    sort = request.GET.get('sort',0)
    limit = request.GET.get('limit', 10)
    if sort == '1':
        sort = '-'
    else:
        sort = ''
    try:
        token = UserToken.objects.get(token=token)
        parent_doc = request.GET.get('pid', '')  # pid 参数改为 parent_doc
        pid = int(parent_doc) if parent_doc else 0
        docs = Doc.objects.filter(create_user=token.user, parent_doc=pid, status=1).order_by('{}create_time'.format(sort))

        # 分页处理
        paginator = Paginator(docs, limit)
        page = request.GET.get('page', 1)
        try:
            docs_page = paginator.page(page)
        except PageNotAnInteger:
            docs_page = paginator.page(1)
        except EmptyPage:
            return JsonResponse({'status': True, 'data': []})

        doc_list = []
        for doc in docs_page:
            item = {
                'id': doc.id,
                'name': doc.name,
                'parent_doc': doc.parent_doc,
                'top_doc': doc.top_doc,
                'status': doc.status,
                'create_time': doc.create_time,
                'modify_time': doc.modify_time,
                'create_user': doc.create_user.username,
                'editor_mode': doc.editor_mode,
            }
            doc_list.append(item)
        return JsonResponse({'status': True, 'data': doc_list})
    except ObjectDoesNotExist:
        return JsonResponse({'status': False, 'data': _('token无效')})
    except:
        logger.exception(_("token获取文档列表异常"))
        return JsonResponse({'status': False, 'data': _('系统异常')})


# 获取文档层级列表
def get_level_docs(request):
    token = request.GET.get('token', '')
    try:
        token = UserToken.objects.get(token=token)
        pid = request.GET.get('pid', 0)
        pid = int(pid) if pid else 0

        base_qs = Doc.objects.filter(create_user=token.user, status=1)
        parent_id_list = set(base_qs.exclude(parent_doc=0).values_list('parent_doc', flat=True))
        doc_list = []
        doc_cnt = 0

        top_docs = base_qs.filter(parent_doc=pid).values('id', 'name', 'editor_mode', 'parent_doc').order_by('sort')
        for doc in top_docs:
            top_item = {
                'id': doc['id'],
                'name': doc['name'],
                'editor_mode': doc['editor_mode'],
                'parent_doc': doc['parent_doc'],
                'top_doc': 0,
                'sub': []
            }
            doc_cnt += 1
            if doc['id'] in parent_id_list:
                sec_docs = base_qs.filter(parent_doc=doc['id']).values('id', 'name', 'editor_mode', 'parent_doc').order_by('sort')
                for doc2 in sec_docs:
                    sec_item = {
                        'id': doc2['id'],
                        'name': doc2['name'],
                        'editor_mode': doc2['editor_mode'],
                        'parent_doc': doc2['parent_doc'],
                        'top_doc': 0,
                        'sub': []
                    }
                    doc_cnt += 1
                    if doc2['id'] in parent_id_list:
                        thr_docs = base_qs.filter(parent_doc=doc2['id']).values('id', 'name', 'editor_mode', 'parent_doc').order_by('sort')
                        for doc3 in thr_docs:
                            item = {
                                'id': doc3['id'],
                                'name': doc3['name'],
                                'editor_mode': doc3['editor_mode'],
                                'parent_doc': doc3['parent_doc'],
                                'top_doc': 0,
                                'sub': []
                            }
                            doc_cnt += 1
                            sec_item['sub'].append(item)
                        top_item['sub'].append(sec_item)
                    else:
                        top_item['sub'].append(sec_item)
                doc_list.append(top_item)
            else:
                doc_list.append(top_item)

        return JsonResponse({'status': True, 'data': doc_list, 'total': doc_cnt})
    except ObjectDoesNotExist:
        return JsonResponse({'status': False, 'data': _('token无效')})
    except:
        logger.exception(_("token获取文档层级异常"))
        return JsonResponse({'status': False, 'data': _('系统异常')})

# 获取个人所有文档列表
def get_self_docs(request):
    token = request.GET.get('token', '')
    sort = request.GET.get('sort',0)
    kw = request.GET.get('kw','')
    limit = request.GET.get('limit', 10)
    if sort == '1':
        sort = '-'
    else:
        sort = ''
    try:
        token = UserToken.objects.get(token=token)
        # 按文档修改时间进行排序
        if kw == '':
            docs = Doc.objects.filter(create_user=token.user,status=1).order_by('{}modify_time'.format(sort))
        else:
            # kw_list = jieba.cut(kw, cut_all=True)
            # reduce(operator.or_,(Q(name__icontains=x) for x in kw_list))
            docs = Doc.objects.filter(create_user=token.user,status=1,name__icontains=kw).order_by('{}modify_time'.format(sort))

        # 分页处理
        paginator = Paginator(docs, limit)
        page = request.GET.get('page', 1)
        try:
            docs_page = paginator.page(page)
        except PageNotAnInteger:
            docs_page = paginator.page(1)
        except EmptyPage:
            # docs_page = paginator.page(paginator.num_pages)
            return JsonResponse({'status': True, 'data': []})

        doc_list = []
        for doc in docs_page:
            item = {
                'id': doc.id,
                'name': doc.name,
                'summary': remove_doc_tag(doc),
                'parent_doc': doc.parent_doc,
                'top_doc': doc.top_doc,
                'editor_mode': doc.editor_mode,
                'status': doc.status,
                'create_time': doc.create_time,
                'modify_time': doc.modify_time,
                'create_user': doc.create_user.username
            }
            doc_list.append(item)
        return JsonResponse({'status': True, 'data': doc_list})
    except ObjectDoesNotExist:
        return JsonResponse({'status': False, 'data': _('token无效')})
    except:
        logger.exception("token获取文档列表异常")
        return JsonResponse({'status': False, 'data': _('系统异常')})



# 获取单篇文档
def get_doc(request):
    token = request.GET.get('token', '')
    try:
        token = UserToken.objects.get(token=token)
        did = request.GET.get('did', '')
        doc = Doc.objects.get(create_user=token.user, id=did)

        item = {
            'id': doc.id,
            'name': doc.name,
            "content": doc.content,
            'md_content': doc.pre_content,
            'parent_doc': doc.parent_doc,
            'top_doc': doc.top_doc,
            'status': doc.status,
            "editor_mode": doc.editor_mode,
            'create_time': doc.create_time,
            'modify_time': doc.modify_time,
            'create_user': doc.create_user.username
        }
        return JsonResponse({'status': True, 'data': item})
    except ObjectDoesNotExist:
        return JsonResponse({'status': False, 'data': _('token无效')})
    except:
        logger.exception("token获取文集异常")
        return JsonResponse({'status': False, 'data': _('系统异常')})


# 获取文档上下篇文档
def get_doc_previous_next(request):
    token = request.GET.get('token', '')
    try:
        token = UserToken.objects.get(token=token)
        did = request.GET.get('did', '')
        doc = Doc.objects.get(id=did)
        try:
            previous_doc = find_doc_previous(did)
            previous_doc_id = previous_doc.id
        except Exception as e:
            logger.error("获取上一篇文档异常")
            previous_doc_id = None
        try:
            next_doc = find_doc_next(did)
            next_doc_id = next_doc.id
        except Exception as e:
            logger.error("获取下一篇文档异常")
            next_doc_id = None
        return JsonResponse({'status': True, 'data': {'next':next_doc_id,'previous':previous_doc_id}})
    except Exception as e:
        logger.exception("获取文档上下篇文档异常")
        return JsonResponse({'status':False,'data':'系统异常'})



# 新建文档
@require_http_methods(['GET','POST'])
@csrf_exempt
def create_doc(request):
    token = request.GET.get('token', '')
    content_type = request.headers.get('Content-Type', '').lower()
    if 'json' in content_type:
        try:
            json_data = json.loads(request.body.decode('utf-8'))
            project_id = json_data.get('pid', '')
            doc_title = json_data.get('title', '')
            doc_content = json_data.get('doc', '')
            parent_doc = json_data.get('parent_doc', 0)
            editor_mode = json_data.get('editor_mode', 2)
        except json.JSONDecodeError:
            return JsonResponse({'data': 'Invalid JSON data', 'status': False})
    else:
        project_id = request.POST.get('pid', '')
        doc_title = request.POST.get('title', '')
        doc_content = request.POST.get('doc', '')
        editor_mode = request.POST.get('editor_mode', 2)
        parent_doc = request.POST.get('parent_doc', 0)
    try:
        # 验证Token
        token = UserToken.objects.get(token=token)
        em = int(editor_mode)
        source = doc_content
        outline = parse_outline(source, em)
        kwargs = {
            'name': doc_title,
            'top_doc': 0,
            'editor_mode': em,
            'parent_doc': int(parent_doc) if parent_doc else 0,
            'create_user': token.user,
            'outline': outline,
        }
        if em == 2:
            kwargs['pre_content'] = doc_content
        elif em == 3:
            kwargs['content'] = doc_content
        else:
            kwargs['pre_content'] = doc_content
        doc = Doc.objects.create(**kwargs)
        return JsonResponse({'status': True, 'data': doc.id})
    except ObjectDoesNotExist:
        return JsonResponse({'status': False, 'data': _('token无效')})
    except:
        logger.exception(_("token创建文档异常"))
        return JsonResponse({'status':False,'data':_('系统异常')})

# 更新修改文档
@require_http_methods(['GET','POST'])
@csrf_exempt
def modify_doc(request):
    token = request.GET.get('token', '')
    content_type = request.headers.get('Content-Type', '').lower()
    if 'json' in content_type:
        try:
            json_data = json.loads(request.body.decode('utf-8'))
            project_id = json_data.get('pid', '')
            doc_id = json_data.get('did', '')
            doc_title = json_data.get('title', '')
            doc_content = json_data.get('doc', '')
            parent_doc = json_data.get('parent_doc', '')
        except json.JSONDecodeError:
            return JsonResponse({'data': 'Invalid JSON data', 'status': False})
    else:
        project_id = request.POST.get('pid', '')
        doc_id = request.POST.get('did', '')
        doc_title = request.POST.get('title', '')
        doc_content = request.POST.get('doc', '')
        parent_doc = request.POST.get('parent_doc', '')
    try:
        # 验证Token
        token = UserToken.objects.get(token=token)
        doc = Doc.objects.get(id=doc_id, create_user=token.user)
        parent_id = doc.parent_doc if parent_doc == '' else int(parent_doc) if parent_doc else doc.parent_doc
        DocHistory.objects.create(
            doc=doc,
            pre_content=doc.pre_content,
            create_user=token.user
        )
        outline = parse_outline(doc_content, doc.editor_mode)
        if doc.editor_mode == 4:
            Doc.objects.filter(id=int(doc_id)).update(
                name=doc_title,
                pre_content=doc_content,
                parent_doc=parent_id,
                modify_time=datetime.datetime.now(),
            )
        else:
            Doc.objects.filter(id=int(doc_id)).update(
                name=doc_title,
                pre_content=doc_content,
                parent_doc=parent_id,
                modify_time=datetime.datetime.now(),
                outline=outline
            )
        return JsonResponse({'status': True, 'data': 'ok'})
    except ObjectDoesNotExist:
        return JsonResponse({'status': False, 'data': 'token无效'})
    except:
        logger.exception("token修改文档异常")
        return JsonResponse({'status':False,'data':'系统异常'})
    
# 上传图片
@csrf_exempt
@require_http_methods(['GET','POST'])
def upload_img(request):
    ##################
    # {"success": 0, "message": "出错信息"}
    # {"success": 1, "url": "图片地址"}
    ##################
    token = request.GET.get('token', '')
    content_type = request.headers.get('Content-Type', '').lower()
    if 'json' in content_type:
        try:
            json_data = json.loads(request.body.decode('utf-8'))
            base64_img = json_data.get('base64', None)
            commom_img = json_data.get('image', None)
        except json.JSONDecodeError:
            return JsonResponse({'data': 'Invalid JSON data', 'status': False})
    else:
        base64_img = request.POST.get('data', None)
        commom_img = request.FILES.get('image', None)  # 普通图片上传
    try:
        # 验证Token
        token = UserToken.objects.get(token=token)
        # 上传图片
        if base64_img:
            result = base_img_upload(base64_img, '', token.user)
        elif commom_img:
            result = img_upload(commom_img, '', token.user)
        else:
            return JsonResponse({'status': False, 'data': _('无有效图片')})
        return JsonResponse(result)
        # return HttpResponse(json.dumps(result), content_type="application/json")
    except ObjectDoesNotExist:
        return JsonResponse({'success': 0, 'data': _('token无效')})
    except:
        logger.exception(_("token上传图片异常"))
        return JsonResponse({'success':0,'data':_('上传出错')})

# 上传URL图片
@csrf_exempt
@require_http_methods(['GET','POST'])
def upload_img_url(request):
    token = request.GET.get('token', '')
    url_img = request.POST.get('url','')
    try:
        # 验证Token
        token = UserToken.objects.get(token=token)
        if token.user:
            # 上传图片
            if url_img.startswith("data:image"):  # 以URL形式上传的BASE64编码图片
                result = base_img_upload(url_img, '', token.user)
            else:
                result = url_img_upload(url_img, '', token.user)
            return JsonResponse(result)
        else:
            return JsonResponse({'status': False, 'data': _('用户无权限操作')})
    except ObjectDoesNotExist:
        return JsonResponse({'success': 0, 'data': _('token无效')})
    except:
        logger.error(_("token上传url图片异常"))
        return JsonResponse({'success':0,'data':_('上传出错')})

# 上传附件
@csrf_exempt
@require_http_methods(['POST'])
def upload_attachment(request):
    attachment = request.FILES.get('attachment_upload', None)
    token = request.GET.get('token', '')
    try:
        token = UserToken.objects.get(token=token)
        if not (token.user.is_writer and token.user.writer_value[3] == '1'):
            return JsonResponse({'status': False, 'data': _('用户无权限操作')})
        result = handle_attachment_upload(attachment, token.user, request)
        return JsonResponse({'status': result['status'], 'data': result['data']})
    except ObjectDoesNotExist:
        return JsonResponse({'status': False, 'data': _('token无效')})
    except Exception:
        logger.exception(_("上传出错"))
        return JsonResponse({'status': False, 'data': _('上传出错')})

# 删除文档（软删除）
@csrf_exempt
@require_http_methods(['GET','POST'])
def delete_doc(request):
    token = request.GET.get('token', '')
    content_type = request.headers.get('Content-Type', '').lower()
    if 'json' in content_type:
        try:
            json_data = json.loads(request.body.decode('utf-8'))
            doc_id = json_data.get('did', '')
        except json.JSONDecodeError:
            return JsonResponse({'data': 'Invalid JSON data', 'status': False})
    else:
        doc_id = request.POST.get('did', '')
    try:
        # 验证Token
        token = UserToken.objects.get(token=token)
        doc = Doc.objects.get(id=doc_id)

        # 验证权限
        if doc.create_user == token.user:
            Doc.objects.filter(id=int(doc_id)).update(
                status=3,
                modify_time=datetime.datetime.now(),
            )
            return JsonResponse({'status': True, 'data': 'ok'})
        else:
            return JsonResponse({'status':False,'data':'非法请求'})
    except ObjectDoesNotExist:
        return JsonResponse({'status': False, 'data': 'token无效'})
    except:
        logger.exception("token修改文档异常")
        return JsonResponse({'status':False,'data':'系统异常'})