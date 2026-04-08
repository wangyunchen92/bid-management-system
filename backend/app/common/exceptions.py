"""
自定义异常类
"""


class BusinessException(Exception):
    def __init__(self, message: str = "业务处理异常", code: int = 400):
        self.code = code
        self.message = message
        super().__init__(self.message)


class NotFoundException(Exception):
    def __init__(self, message: str = "请求的资源不存在"):
        self.message = message
        super().__init__(self.message)


class ForbiddenException(Exception):
    def __init__(self, message: str = "权限不足，无法执行此操作"):
        self.message = message
        super().__init__(self.message)


class UnauthorizedException(Exception):
    def __init__(self, message: str = "未登录或登录已过期"):
        self.message = message
        super().__init__(self.message)


class ValidationException(BusinessException):
    def __init__(self, message: str = "参数校验失败", errors: list = None):
        super().__init__(message=message, code=422)
        self.errors = errors or []


class DuplicateException(BusinessException):
    def __init__(self, message: str = "数据已存在"):
        super().__init__(message=message, code=409)
