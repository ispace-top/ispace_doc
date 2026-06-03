"""
强制语言中间件

当 [locale] force = True 时，强制使用配置的默认语言，
忽略浏览器 Accept-Language 头。
"""

from django.conf import settings
from django.utils import translation


class ForceDefaultLanguageMiddleware:
    """强制使用配置的默认语言。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = language
        response = self.get_response(request)
        translation.deactivate()
        return response
