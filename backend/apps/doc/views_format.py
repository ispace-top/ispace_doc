# coding:utf-8
"""代码格式化 API — 支持多种语言的自动格式化。"""

import json
import textwrap

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from loguru import logger


# 语言到格式化函数的映射
LANGUAGE_FORMATTERS = {}


def _format_json(code: str) -> str:
    try:
        parsed = json.loads(code)
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError as e:
        raise ValueError(f'JSON 解析错误: {e}')


def _format_python(code: str) -> str:
    try:
        import autopep8
        return autopep8.fix_code(code, options={'max_line_length': 100})
    except ImportError:
        pass
    # fallback: basic dedent + reindent
    return textwrap.dedent(code)


def _format_generic(code: str) -> str:
    """通用格式化：去公共缩进 + 去除多余空行。"""
    lines = code.split('\n')
    # Remove leading/trailing empty lines
    while lines and lines[0].strip() == '':
        lines.pop(0)
    while lines and lines[-1].strip() == '':
        lines.pop()
    # Dedent
    return textwrap.dedent('\n'.join(lines))


LANGUAGE_FORMATTERS = {
    'json': _format_json,
    'python': _format_python,
    'py': _format_python,
}


@require_POST
def api_format_code(request):
    """格式化代码。

    POST JSON:
        code: str — 待格式化的代码
        language: str — 语言标识 (python/json/js/html/css/java/go/...)

    Returns:
        {"code": 0, "data": {"formatted": "..."}} 或
        {"code": 5, "msg": "错误信息"}
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        body = {}

    code = body.get('code', '')
    language = (body.get('language', '') or '').lower().strip()

    if not code.strip():
        return JsonResponse({'code': 5, 'msg': '代码不能为空'})

    formatter = LANGUAGE_FORMATTERS.get(language)
    if formatter:
        try:
            formatted = formatter(code)
            return JsonResponse({'code': 0, 'data': {'formatted': formatted}})
        except ValueError as e:
            return JsonResponse({'code': 5, 'msg': str(e)})
        except Exception as e:
            logger.exception(f'代码格式化失败 language={language}')
            return JsonResponse({'code': 5, 'msg': f'格式化失败: {e}'})
    else:
        # 不支持的语言使用通用格式化
        try:
            formatted = _format_generic(code)
            return JsonResponse({'code': 0, 'data': {'formatted': formatted}})
        except Exception as e:
            return JsonResponse({'code': 5, 'msg': str(e)})
