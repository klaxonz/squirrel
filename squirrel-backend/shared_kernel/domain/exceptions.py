"""Domain exception hierarchy.

All business-rule violations raised from application/domain services should
derive from :class:`DomainError`. Each subclass carries the HTTP status code
its category maps to, so the FastAPI exception handler in ``application.app``
can translate them uniformly -- without routes having to ``try/except`` and
hand-craft the response per call site.

The response body shape mirrors ``infrastructure.http.response``: an integer
``code`` (aligned with ``ErrorCode`` so clients keep one numbering scheme) plus
a human-readable ``msg``.
"""

from __future__ import annotations

from typing import Iterable


class DomainError(Exception):
    """Base class for all domain/business errors.

    Attributes:
        http_status: HTTP status code the framework maps this error to.
        code: Integer business error code surfaced to clients in the ``code``
            field of the response body. Kept aligned with
            ``infrastructure.http.response.ErrorCode`` (400/401/403/404/409/500)
            so there is a single numbering scheme across the codebase.
    """

    http_status: int = 400
    code: int = 400

    def __init__(self, message: str | None = None, *, details: object | None = None) -> None:
        self.message = message or self._default_message()
        # ``details`` is opaque payload for the response body (e.g. field
        # errors). Kept optional and untyped to stay transport-agnostic.
        self.details = details
        super().__init__(self.message)

    def _default_message(self) -> str:
        return '请求处理失败'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(message={self.message!r}, http_status={self.http_status}, code={self.code})'


class ValidationError(DomainError):
    """Input failed business validation beyond what pydantic catches.

    Maps to HTTP 400. Prefer raising this over bare ``ValueError`` when the
    error is about the shape/content of a caller-supplied value.
    """

    http_status = 400
    code = 400

    def _default_message(self) -> str:
        return '参数错误'


class NotFoundError(DomainError):
    """A referenced resource does not exist. Maps to HTTP 404."""

    http_status = 404
    code = 404

    def __init__(
        self,
        resource: str | None = None,
        identifier: object | None = None,
        *,
        message: str | None = None,
        details: object | None = None,
    ) -> None:
        if message is None:
            if resource:
                ident = f' {identifier!r}' if identifier is not None else ''
                message = f'{resource}{ident} 不存在'
            else:
                message = '资源不存在'
        super().__init__(message, details=details)


class ConflictError(DomainError):
    """The request conflicts with existing state. Maps to HTTP 409.

    Use for duplicates, already-applied state transitions, etc.
    """

    http_status = 409
    code = 409

    def _default_message(self) -> str:
        return '资源冲突'


class ForbiddenError(DomainError):
    """The caller is authenticated but not allowed to do this. Maps to 403."""

    http_status = 403
    code = 403

    def _default_message(self) -> str:
        return '无操作权限'


class AuthenticationError(DomainError):
    """Credentials are missing/invalid/wrong. Maps to HTTP 401.

    Distinct from ``infrastructure.http.middleware.auth.AuthenticationError``
    (which guards the transport/auth middleware). This one is for *business*
    auth failures raised from services (e.g. wrong current password).
    """

    http_status = 401
    code = 401

    def _default_message(self) -> str:
        return '认证失败'


def collect_domain_errors() -> Iterable[type[DomainError]]:
    """Return all DomainError subclasses (introspection helper, mainly tests)."""
    return DomainError.__subclasses__()
