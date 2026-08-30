from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware

from application.http.errors import EXCEPTION_HANDLERS
from infrastructure.config.settings import settings
from infrastructure.http.middleware.access_log import AccessLogMiddleware
from infrastructure.http.middleware.auth import AuthenticationMiddleware
from infrastructure.http.middleware.trace import RequestContextMiddleware


def register_middleware(application: FastAPI) -> None:
    """Register middleware from outermost request boundary inward."""
    application.add_middleware(AuthenticationMiddleware)
    application.add_middleware(ExceptionMiddleware, handlers=EXCEPTION_HANDLERS)
    application.add_middleware(AccessLogMiddleware)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*', 'Authorization', 'X-Trace-Id'],
        expose_headers=['X-Trace-Id'],
    )
