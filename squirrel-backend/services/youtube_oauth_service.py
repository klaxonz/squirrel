from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.config import settings


@dataclass(slots=True)
class YouTubeOAuthAccount:
    name: str = ""
    email: str = ""
    avatar: str = ""


@dataclass(slots=True)
class YouTubeOAuthState:
    status: str
    account: YouTubeOAuthAccount | None = None
    verification_url: str | None = None
    user_code: str | None = None
    error: str | None = None
    pending: bool = False


class YouTubeOauthService:
    def __init__(self):
        self._oauth_file = settings.config_dir / "youtube_oauth.json"

    def _get_oauth_state_file(self) -> Path:
        return self._oauth_file

    def _read_oauth_state_file(self) -> dict[str, Any] | None:
        path = self._get_oauth_state_file()
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None

    @staticmethod
    def _extract_account(raw: dict[str, Any] | None) -> YouTubeOAuthAccount | None:
        if not raw:
            return None
        return YouTubeOAuthAccount(
            name=str(raw.get("name") or ""),
            email=str(raw.get("email") or ""),
            avatar=str(raw.get("avatar") or ""),
        )

    def get_oauth_credentials_for_daemon(self) -> str:
        return str(self._get_oauth_state_file())

    def get_oauth_cache_scope(self) -> str:
        path = self._get_oauth_state_file()
        try:
            payload = path.read_bytes()
        except OSError:
            return "oauth:none"
        return f"oauth:{hashlib.sha256(payload).hexdigest()[:16]}"

    def get_oauth_state(self, timeout_seconds: float = 5.0) -> YouTubeOAuthState:
        return self.poll_oauth_status_via_daemon(timeout_seconds=timeout_seconds)

    def setup_oauth_via_daemon(self, timeout_seconds: float = 10.0) -> YouTubeOAuthState:
        from squirrel_youtube.youtubei_resolver import resolve_oauth_setup_via_daemon

        oauth_result = resolve_oauth_setup_via_daemon(
            oauth_state_file=self.get_oauth_credentials_for_daemon(),
            timeout_seconds=timeout_seconds,
        )
        return self._parse_daemon_oauth_response(oauth_result)

    def poll_oauth_status_via_daemon(self, timeout_seconds: float = 10.0) -> YouTubeOAuthState:
        from squirrel_youtube.youtubei_resolver import resolve_oauth_status_via_daemon

        oauth_result = resolve_oauth_status_via_daemon(
            oauth_state_file=self.get_oauth_credentials_for_daemon(),
            timeout_seconds=timeout_seconds,
        )
        return self._parse_daemon_oauth_response(oauth_result)

    def revoke_oauth_via_daemon(self, timeout_seconds: float = 30.0) -> bool:
        from squirrel_youtube.youtubei_resolver import resolve_oauth_revoke_via_daemon

        oauth_result = resolve_oauth_revoke_via_daemon(
            oauth_state_file=self.get_oauth_credentials_for_daemon(),
            timeout_seconds=timeout_seconds,
        )
        return oauth_result.get("status") == "done"

    def _parse_daemon_oauth_response(self, result: dict[str, Any]) -> YouTubeOAuthState:
        status = str(result.get("status") or "not_configured")

        if status == "not_configured":
            return YouTubeOAuthState(status="not_configured")

        if status == "error":
            return YouTubeOAuthState(status="error", error=str(result.get("error", "Unknown error")))

        if status == "pending":
            return YouTubeOAuthState(
                status="pending",
                pending=True,
                verification_url=str(result.get("verification_url") or ""),
                user_code=str(result.get("user_code") or ""),
            )

        if status in {"authenticated", "already_authenticated"}:
            return YouTubeOAuthState(
                status="authenticated",
                account=self._extract_account(result.get("account")),
            )

        if status == "expired":
            return YouTubeOAuthState(status="expired")

        if status == "done":
            return YouTubeOAuthState(status="not_configured")

        return YouTubeOAuthState(status=status)


_default = YouTubeOauthService()
get_oauth_credentials_for_daemon = _default.get_oauth_credentials_for_daemon
get_oauth_cache_scope = _default.get_oauth_cache_scope
get_oauth_state = _default.get_oauth_state
setup_oauth_via_daemon = _default.setup_oauth_via_daemon
poll_oauth_status_via_daemon = _default.poll_oauth_status_via_daemon
revoke_oauth_via_daemon = _default.revoke_oauth_via_daemon
