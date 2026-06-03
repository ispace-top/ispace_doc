# coding:utf-8
"""代码格式化 API — 支持多种语言的自动格式化。"""

import json
import re
import textwrap

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from loguru import logger


def _format_json(code: str) -> str:
    try:
        parsed = json.loads(code)
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError as e:
        raise ValueError(f'JSON 解析错误: {e}')


def _format_python(code: str) -> str:
    try:
        import autopep8
        result = autopep8.fix_code(code, options={'max_line_length': 100})
        if result.strip() != code.strip():
            return result
    except ImportError:
        pass
    # autopep8 didn't change anything or unavailable: manual cleanup
    lines = code.split('\n')
    cleaned = []
    for line in lines:
        # Normalize multiple spaces (preserve indent)
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        # Collapse multiple spaces between tokens (not inside strings)
        normalized = re.sub(r' {2,}', ' ', stripped)
        cleaned.append(indent + normalized)
    return textwrap.dedent('\n'.join(cleaned)).strip() + '\n'


def _format_js_like(code: str) -> str:
    """基础格式化适用于 JS/Java/C/Go 等类C语言。"""
    lines = code.split('\n')
    result = []
    for line in lines:
        indent = len(line) - len(line.lstrip())
        s = line.strip()
        if not s:
            result.append('')
            continue
        # comma spacing: x,y → x, y  (but not inside <generics>)
        s = re.sub(r',(?!\s)', ', ', s)
        # operator spacing: =+-*/  but not == != <= >= ++ --
        s = re.sub(r'(?<![=+\-*/%<>&|^!])([=+\-*/%])(?!=)', r' \1 ', s)
        s = re.sub(r'([=+\-*/%]) (?=[=+\-*/%])', r'\1', s)  # fix double-spaced ops
        # brace spacing: keyword{ → keyword {  and }{ → } {
        s = re.sub(r'(?<=\w)\{', ' {', s)
        s = re.sub(r'\}(?=\w)', '} ', s)
        # paren spacing: func( → func(  keep tight, but ( a ) → (a)
        s = re.sub(r'\(\s+', '(', s)
        s = re.sub(r'\s+\)', ')', s)
        # foreach/if/while/for spacing
        s = re.sub(r'\b(if|for|while|switch|catch|synchronized)\s*\(', r'\1 (', s)
        # collapse multiple spaces
        s = re.sub(r' {2,}', ' ', s)
        # strip trailing space
        s = s.rstrip()
        result.append(' ' * indent + s)
    return '\n'.join(result).strip() + '\n'


def _format_generic(code: str) -> str:
    """通用格式化：去公共缩进 + 去除多余空行 + 基础空格规范化。"""
    lines = code.split('\n')
    while lines and lines[0].strip() == '':
        lines.pop(0)
    while lines and lines[-1].strip() == '':
        lines.pop()
    if not lines:
        return ''
    result = []
    for line in lines:
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        normalized = re.sub(r' {2,}', ' ', stripped)
        result.append(indent + normalized)
    return textwrap.dedent('\n'.join(result)).strip() + '\n'


LANGUAGE_FORMATTERS = {
    'json': _format_json,
    'python': _format_python,
    'py': _format_python,
    'javascript': _format_js_like,
    'js': _format_js_like,
    'java': _format_js_like,
    'c': _format_js_like,
    'cpp': _format_js_like,
    'csharp': _format_js_like,
    'go': _format_js_like,
    'rust': _format_js_like,
    'php': _format_js_like,
    'typescript': _format_js_like,
    'ts': _format_js_like,
}


@require_POST
@csrf_exempt
def api_format_code(request):
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
        try:
            formatted = _format_generic(code)
            return JsonResponse({'code': 0, 'data': {'formatted': formatted}})
        except Exception as e:
            return JsonResponse({'code': 5, 'msg': str(e)})
