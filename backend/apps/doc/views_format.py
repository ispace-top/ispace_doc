# coding:utf-8
"""代码格式化 API — Python(autopep8) / JSON(json) / 其他(prettier)。"""

import json
import os
import re
import subprocess
import textwrap

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from loguru import logger

# -------------------------------------------------------------------
#  Prettier 语言映射 (language → prettier parser)
# -------------------------------------------------------------------

PRETTIER_LANGS = {
    'java': 'java',
    'javascript': 'babel', 'js': 'babel', 'jsx': 'babel',
    'typescript': 'typescript', 'ts': 'typescript', 'tsx': 'typescript',
    'html': 'html', 'css': 'css', 'scss': 'css', 'less': 'css',
    'json': 'json', 'json5': 'json',
    'markdown': 'markdown', 'md': 'markdown',
    'yaml': 'yaml', 'yml': 'yaml',
    'graphql': 'graphql',
}


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
    lines = code.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        normalized = re.sub(r' {2,}', ' ', stripped)
        cleaned.append(indent + normalized)
    return textwrap.dedent('\n'.join(cleaned)).strip() + '\n'


def _format_prettier(code: str, parser: str) -> str:
    """调用 Prettier 格式化代码。"""
    npx = 'npx.cmd' if os.name == 'nt' else 'npx'
    args = [npx, '-y', 'prettier', '--parser', parser, '--stdin-filepath', f'dummy.{parser}']
    if parser in ('java',):
        args.insert(3, 'prettier-plugin-java')
        args.insert(3, '--plugin')
    try:
        proc = subprocess.run(
            args,
            input=code,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, 'CI': '1'},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
        logger.warning(f'Prettier failed ({parser}): {proc.stderr[:200]}')
        raise RuntimeError(proc.stderr.strip() or '格式化失败')
    except FileNotFoundError:
        raise RuntimeError('npx 不可用，请安装 Node.js')
    except subprocess.TimeoutExpired:
        raise RuntimeError('prettier 格式化超时')


def _format_generic(code: str) -> str:
    """通用格式化：去公共缩进 + 去除多余空行。"""
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
}


def _get_formatter(language: str):
    """根据语言选择格式化器：优先内置(Python/JSON)，其次Prettier。"""
    if language in LANGUAGE_FORMATTERS:
        return LANGUAGE_FORMATTERS[language], None
    parser = PRETTIER_LANGS.get(language)
    if parser:
        return _format_prettier, parser
    return _format_generic, None


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

    formatter, extra = _get_formatter(language)
    try:
        if extra:
            formatted = formatter(code, extra)
        else:
            formatted = formatter(code)
        return JsonResponse({'code': 0, 'data': {'formatted': formatted}})
    except ValueError as e:
        return JsonResponse({'code': 5, 'msg': str(e)})
    except Exception as e:
        logger.exception(f'代码格式化失败 language={language}')
        return JsonResponse({'code': 5, 'msg': str(e)})
