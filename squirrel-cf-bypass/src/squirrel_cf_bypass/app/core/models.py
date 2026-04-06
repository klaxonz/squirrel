from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ClearanceRecord:
    cookies: dict[str, str]
    user_agent: str
    created_at: float
    expires_at: float


@dataclass(slots=True)
class HtmlResult:
    html: str
    final_url: str
    status_code: int
    cookies: dict[str, str]
    user_agent: str


@dataclass(slots=True)
class MirrorResult:
    status_code: int
    headers: dict[str, str]
    body: bytes


@dataclass(slots=True)
class SessionRecord:
    session: Any
    created_at: float
