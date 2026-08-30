import logging

from fastapi import status
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from infrastructure.http import response
from infrastructure.http.middleware.auth import (
    AuthenticationError,
    TokenExpiredError,
    TokenMissingError,
)
from infrastructure.http.response import ErrorCode
from shared_kernel.domain.exceptions import DomainError

logger = logging.getLogger(__name__)

_STATUS_CODE_TO_ERROR_CODE: dict[int, int] = {
    status.HTTP_400_BAD_REQUEST: ErrorCode.PARAM_ERROR,
    status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
    status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    status.HTTP_500_INTERNAL_SERVER_ERROR: ErrorCode.SERVER_ERROR,
}


async def authentication_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    logger.error('AuthenticationError: %s', exc.detail, exc_info=True)
    return response.error(exc.detail, ErrorCode.UNAUTHORIZED)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.error('HTTPException: %s', exc.detail, exc_info=True)
    code = _STATUS_CODE_TO_ERROR_CODE.get(exc.status_code, ErrorCode.UNKNOWN_ERROR)
    return JSONResponse(
        status_code=exc.status_code,
        content={'code': code, 'msg': exc.detail},
    )


async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.error('RequestValidationError: %s', exc, exc_info=True)
    return response.param_error('请求参数错误')


async def default_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error('DefaultException: %s', exc, exc_info=True)
    return response.server_error('服务器内部错误')


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    logger.info('DomainError [%s]: %s', exc.code, exc.message)
    body: dict = {'code': exc.code, 'msg': exc.message}
    if exc.details is not None:
        body['data'] = exc.details
    return JSONResponse(status_code=exc.http_status, content=body)


EXCEPTION_HANDLERS = {
    FastAPIHTTPException: http_exception_handler,
    RequestValidationError: request_validation_error_handler,
    StarletteHTTPException: http_exception_handler,
    Exception: default_exception_handler,
    DomainError: domain_error_handler,
    AuthenticationError: authentication_error_handler,
    TokenMissingError: authentication_error_handler,
    TokenExpiredError: authentication_error_handler,
}
