from typing import Any, Optional

from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class Response(BaseModel):
    code: int
    msg: str
    data: Optional[Any] = None


def _payload(code: int, msg: str, data: Any = None) -> dict:
    return {
        'code': code,
        'msg': msg,
        'data': data
    }


def success(data: Any = None, msg: str = 'success') -> dict:
    """
    返回成功响应
    
    Args:
        data: 响应数据
        msg: 成功消息
    """
    return _payload(0, msg, data)


# 预定义的错误码
class ErrorCode:
    UNKNOWN_ERROR = 1  # 未知错误
    PARAM_ERROR = 400  # 参数错误
    UNAUTHORIZED = 401  # 未授权
    FORBIDDEN = 403  # 禁止访问
    NOT_FOUND = 404  # 资源不存在
    SERVER_ERROR = 500  # 服务器错误


def _http_status_for_code(code: int) -> int:
    if code in {
        ErrorCode.PARAM_ERROR,
        ErrorCode.UNAUTHORIZED,
        ErrorCode.FORBIDDEN,
        ErrorCode.NOT_FOUND,
        ErrorCode.SERVER_ERROR,
    }:
        return code
    if status.HTTP_400_BAD_REQUEST <= code <= 599:
        return code
    return status.HTTP_400_BAD_REQUEST


def error(msg: str, code: int = ErrorCode.UNKNOWN_ERROR) -> JSONResponse:
    """
    返回错误响应
    
    Args:
        msg: 错误消息
        code: 错误码,默认为1
    """
    return JSONResponse(
        status_code=_http_status_for_code(code),
        content=_payload(code, msg),
    )


# 常用错误响应
def param_error(msg: str = '参数错误') -> JSONResponse:
    return error(msg, ErrorCode.PARAM_ERROR)


def unauthorized(msg: str = '未登录或登录已过期') -> JSONResponse:
    return error(msg, ErrorCode.UNAUTHORIZED)


def forbidden(msg: str = '没有操作权限') -> JSONResponse:
    return error(msg, ErrorCode.FORBIDDEN)


def not_found(msg: str = '资源不存在') -> JSONResponse:
    return error(msg, ErrorCode.NOT_FOUND)


def server_error(msg: str = '服务器内部错误') -> JSONResponse:
    return error(msg, ErrorCode.SERVER_ERROR)
