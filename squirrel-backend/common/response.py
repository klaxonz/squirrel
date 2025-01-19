from typing import Any, Optional
from pydantic import BaseModel


class Response(BaseModel):
    code: int
    msg: str
    data: Optional[Any] = None


def success(data: Any = None, msg: str = "success") -> dict:
    """
    返回成功响应
    
    Args:
        data: 响应数据
        msg: 成功消息
    """
    return {
        "code": 0,
        "msg": msg,
        "data": data
    }


def error(msg: str, code: int = 1) -> dict:
    """
    返回错误响应
    
    Args:
        msg: 错误消息
        code: 错误码,默认为1
    """
    return {
        "code": code,
        "msg": msg,
        "data": None
    }


# 预定义的错误码
class ErrorCode:
    UNKNOWN_ERROR = 1  # 未知错误
    PARAM_ERROR = 400  # 参数错误
    UNAUTHORIZED = 401  # 未授权
    FORBIDDEN = 403  # 禁止访问
    NOT_FOUND = 404  # 资源不存在
    SERVER_ERROR = 500  # 服务器错误


# 常用错误响应
def param_error(msg: str = "参数错误") -> dict:
    return error(msg, ErrorCode.PARAM_ERROR)


def unauthorized(msg: str = "未登录或登录已过期") -> dict:
    return error(msg, ErrorCode.UNAUTHORIZED)


def forbidden(msg: str = "没有操作权限") -> dict:
    return error(msg, ErrorCode.FORBIDDEN)


def not_found(msg: str = "资源不存在") -> dict:
    return error(msg, ErrorCode.NOT_FOUND)


def server_error(msg: str = "服务器内部错误") -> dict:
    return error(msg, ErrorCode.SERVER_ERROR)
