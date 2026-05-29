# coding:utf-8
from backend.apps.doc.models import Doc, DocTag, Image
from django import template
from django.utils.translation import gettext_lazy as _
from django.utils.html import strip_tags
import markdown

register = template.Library()


@register.filter(name='get_doc_count')
def get_doc_count(value):
    return Doc.objects.filter(status=1).count()


@register.filter(name='get_new_doc')
def get_new_doc(value):
    new_doc = Doc.objects.filter(status=1).order_by('-modify_time')[:3]
    if new_doc is None:
        new_doc = _('还没有文档……')
    return new_doc


@register.filter(name='img_group_cnt')
def get_img_group_cnt(value):
    cnt = Image.objects.filter(group_id=value).count()
    return cnt


@register.filter(name='tag_doc_cnt')
def get_tag_doc_cnt(value):
    cnt = DocTag.objects.filter(tag=value).count()
    return cnt


@register.filter(name='project_desc')
def get_project_desc(value):
    value = strip_tags(markdown.markdown(value))[:201]
    return value
