from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ClearanceRecord:
    cookies: dict[str, str]
    user_agent: str
    created_at: float
    expires_at: float
    browser_config: dict[str, Any] | None = None
    browser_os: str | None = None
    http_usable: bool = True


@dataclass(slots=True)
class HtmlResult:
    html: str
    final_url: str
    status_code: int
    cookies: dict[str, str]
    user_agent: str
    browser_config: dict[str, Any] | None = None
    browser_os: str | None = None
    source: str | None = None


@dataclass(slots=True)
class MirrorResult:
    status_code: int
    headers: dict[str, str]
    body: bytes


@dataclass(slots=True)
class SessionRecord:
    session: Any
    created_at: float
