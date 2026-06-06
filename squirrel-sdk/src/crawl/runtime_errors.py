"""Runtime error models for site runtime V2."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class RuntimeErrorCode(str, Enum):
    """Stable error codes exchanged between host and site runtimes."""

    TIMEOUT = 'PLUGIN_TIMEOUT'
    CRASHED = 'PLUGIN_CRASHED'
    BAD_RESPONSE = 'PLUGIN_BAD_RESPONSE'
    AUTH_REQUIRED = 'PLUGIN_AUTH_REQUIRED'
    NETWORK_ERROR = 'PLUGIN_NETWORK_ERROR'
    PARSE_ERROR = 'PLUGIN_PARSE_ERROR'


@dataclass
class SiteRuntimeError:
    """Serializable runtime error payload."""

    code: RuntimeErrorCode
    message: str
    retryable: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['code'] = self.code.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SiteRuntimeError':
        raw_code = str(data.get('code', RuntimeErrorCode.CRASHED.value))
        try:
            code = RuntimeErrorCode(raw_code)
        except ValueError:
            code = RuntimeErrorCode.CRASHED
        return cls(
            code=code,
            message=str(data.get('message', 'Site runtime error')),
            retryable=bool(data.get('retryable', False)),
            details=dict(data.get('details') or {}),
        )

    @classmethod
    def timeout(cls, message: str, details: Optional[Dict[str, Any]] = None) -> 'SiteRuntimeError':
        return cls(RuntimeErrorCode.TIMEOUT, message, retryable=True, details=dict(details or {}))

    @classmethod
    def crashed(cls, message: str, details: Optional[Dict[str, Any]] = None) -> 'SiteRuntimeError':
        return cls(RuntimeErrorCode.CRASHED, message, retryable=False, details=dict(details or {}))

    @classmethod
    def bad_response(cls, message: str, details: Optional[Dict[str, Any]] = None) -> 'SiteRuntimeError':
        return cls(RuntimeErrorCode.BAD_RESPONSE, message, retryable=False, details=dict(details or {}))

    @classmethod
    def auth_required(cls, message: str, details: Optional[Dict[str, Any]] = None) -> 'SiteRuntimeError':
        return cls(RuntimeErrorCode.AUTH_REQUIRED, message, retryable=False, details=dict(details or {}))

    @classmethod
    def network_error(
        cls,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = True,
    ) -> 'SiteRuntimeError':
        return cls(RuntimeErrorCode.NETWORK_ERROR, message, retryable=retryable, details=dict(details or {}))

    @classmethod
    def parse_error(cls, message: str, details: Optional[Dict[str, Any]] = None) -> 'SiteRuntimeError':
        return cls(RuntimeErrorCode.PARSE_ERROR, message, retryable=False, details=dict(details or {}))
