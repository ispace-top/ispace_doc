"""
iSpaceDoc Standard API Response Helper.

Standard error codes:
    0 — Success
    1 — Not authenticated / login required
    2 — No permission / forbidden
    3 — Not found / resource does not exist
    4 — Server error / internal exception
    5 — Invalid parameter / validation error
    6 — Rate limited / too many requests
"""
from django.http import JsonResponse


class ApiResponse:
    """Build standard {code, data, message} JSON responses."""

    @staticmethod
    def success(data=None, message='ok'):
        return JsonResponse({'code': 0, 'data': data, 'message': message})

    @staticmethod
    def error(code, message='', data=None):
        return JsonResponse({'code': code, 'data': data, 'message': message})

    @staticmethod
    def auth_required(message='请先登录'):
        return JsonResponse({'code': 1, 'data': None, 'message': message})

    @staticmethod
    def forbidden(message='无权限访问'):
        return JsonResponse({'code': 2, 'data': None, 'message': message})

    @staticmethod
    def not_found(message='资源不存在'):
        return JsonResponse({'code': 3, 'data': None, 'message': message})

    @staticmethod
    def server_error(message='服务器内部错误'):
        return JsonResponse({'code': 4, 'data': None, 'message': message})

    @staticmethod
    def invalid_param(message='参数错误'):
        return JsonResponse({'code': 5, 'data': None, 'message': message})

    @staticmethod
    def rate_limited(message='请求过于频繁，请稍后再试'):
        return JsonResponse({'code': 6, 'data': None, 'message': message})

    # Convenience: from old {status: True/False, data: ...} format
    @staticmethod
    def from_legacy(status, data=None, message=''):
        if status:
            return ApiResponse.success(data=data, message=message)
        else:
            msg = message or (str(data) if isinstance(data, str) else '操作失败')
            return ApiResponse.error(4, message=msg, data=None if isinstance(data, str) else data)
