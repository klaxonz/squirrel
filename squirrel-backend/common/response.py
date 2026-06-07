from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class Response(BaseModel):
    code: int
    msg: str
    data: Any | None = None


def _payload(code: int, msg: str, data: Any = None) -> dict:
    return {
        "code": code,
        "msg": msg,
        "data": data,
    }


def success(data: Any = None, msg: str = "success") -> dict:
    """Return a success response

    Args:
        data: Response data
        msg: Success message

    """
    return _payload(0, msg, data)


# Predefined error codes
class ErrorCode:
    UNKNOWN_ERROR = 1  # Unknown error
    PARAM_ERROR = 400  # Parameter error
    UNAUTHORIZED = 401  # Unauthorized
    FORBIDDEN = 403  # Forbidden
    NOT_FOUND = 404  # Resource not found
    SERVER_ERROR = 500  # Server error


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
    """Return an error response

    Args:
        msg: Error message
        code: Error code, defaults to 1

    """
    return JSONResponse(
        status_code=_http_status_for_code(code),
        content=_payload(code, msg),
    )


# Common error responses
def param_error(msg: str = "Parameter error") -> JSONResponse:
    return error(msg, ErrorCode.PARAM_ERROR)


def unauthorized(msg: str = "Not logged in or session expired") -> JSONResponse:
    return error(msg, ErrorCode.UNAUTHORIZED)


def forbidden(msg: str = "No operation permission") -> JSONResponse:
    return error(msg, ErrorCode.FORBIDDEN)


def not_found(msg: str = "Resource not found") -> JSONResponse:
    return error(msg, ErrorCode.NOT_FOUND)


def server_error(msg: str = "Internal server error") -> JSONResponse:
    return error(msg, ErrorCode.SERVER_ERROR)
