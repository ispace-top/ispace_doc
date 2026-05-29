# coding:utf-8
# 文档自定义模板过滤器

from django import template
from django.utils.translation import gettext_lazy as _
from django.utils.html import strip_tags
from backend.apps.doc.models import Doc
import re
import markdown

register = template.Library()

# 获取文档的子文档
@register.filter(name='get_next_doc')
def get_next_doc(value):
    data = Doc.objects.filter(parent_doc=value,status=1).values('id','name').order_by('sort')
    return data

# 获取文档的上级文档名称
@register.filter(name='get_doc_parent')
def get_doc_parent(value):
    if int(value) != 0:
        try:
            data = Doc.objects.get(id=int(value))
        except:
            data = _('无上级文档')
        return data
    else:
        return _('无上级文档')

# 获取文档的下一篇文档
@register.filter(name='get_doc_next')
def get_doc_next(value):
    try:
        doc_id = value
        doc = Doc.objects.get(id=int(doc_id))
        docs = Doc.objects.filter(
            parent_doc=doc.parent_doc,
            status=1
        ).order_by('sort')
        docs_list = [d.id for d in docs]

        subdoc = Doc.objects.filter(parent_doc=doc.id, status=1)

        if subdoc.count() == 0:
            if docs_list.index(doc.id) == len(docs_list) - 1:
                try:
                    parentdoc = Doc.objects.get(id=doc.parent_doc)
                    parents = Doc.objects.filter(parent_doc=parentdoc.parent_doc, status=1).order_by('sort')
                    parent_list = [d.id for d in parents]
                except:
                    return None
                if parent_list.index(parentdoc.id) == len(parent_list) - 1:
                    try:
                        parentdoc2 = Doc.objects.get(id=parentdoc.parent_doc)
                        parents2 = Doc.objects.filter(parent_doc=parentdoc2.parent_doc, status=1).order_by('sort')
                        parent_list2 = [d.id for d in parents2]
                    except:
                        return None
                    if parent_list2.index(parentdoc2.id) == len(parent_list2) - 1:
                        next_doc = None
                        return next_doc
                    else:
                        next_id = parent_list2[parent_list2.index(parentdoc2.id) + 1]
                        return next_id
                else:
                    next_id = parent_list[parent_list.index(parentdoc.id) + 1]
                    return next_id
            else:
                next_id = docs_list[docs_list.index(doc.id) + 1]
                next_doc = Doc.objects.get(id=next_id)
                return next_doc.id
        else:
            next_doc = subdoc.order_by('sort')[0]
            return next_doc.id
    except Exception as e:
        pass

# 获取文档的上一篇文档
@register.filter(name='get_doc_previous')
def get_doc_previous(value):
    try:
        doc_id = value
        doc = Doc.objects.get(id=int(doc_id))
        docs = Doc.objects.filter(parent_doc=doc.parent_doc, status=1).order_by('sort')
        docs_list = [d.id for d in docs]
        if docs_list.index(doc.id) == 0:
            if doc.parent_doc == 0:
                previous = None
                return previous
            else:
                previous = Doc.objects.get(id=doc.parent_doc)
                return previous.id
        else:
            previou_id = docs_list[docs_list.index(doc.id) - 1]
            previous = Doc.objects.get(id=previou_id)
            previous_subdoc = Doc.objects.filter(parent_doc=previous.id, status=1).order_by('-sort')
            if previous_subdoc.count() == 0:
                return previou_id
            else:
                previous = previous_subdoc[:1][0]
                parent_list = Doc.objects.filter(parent_doc=previous.id, status=1).order_by('-sort')
                if parent_list.count() == 0:
                    return previous.id
                else:
                    previous = parent_list[:1][0]
                    return previous.id
    except Exception as e:
        import traceback
        print(traceback.print_exc())


# 获取内容的关键词上下文
@register.filter(name='get_key_context')
def get_key_context(value,args):
    value = value.replace('\n','') if value is not None else ''
    p = re.compile(args,flags=re.IGNORECASE)
    value_list = []
    for m in p.finditer(value):
        start_point = m.start() - 20
        if start_point < 0:
            start_point = 0
        end_point = m.end()+20
        value_list.append(value[start_point:end_point])
    if len(value_list) > 0:
        r = "…".join(value_list)
        if len(r) > 200:
            r = r[0:200]
    else:
        r = value[0:200]
    return r

# 摘取文档部分正文
@register.filter(name='remove_doc_tag')
def remove_doc_tag(doc):
    try:
        result = strip_tags(markdown.markdown(doc.pre_content))[:300]
    except Exception as e:
        result = doc.pre_content[:300]
    result = result.replace("&nbsp;",'')
    return result