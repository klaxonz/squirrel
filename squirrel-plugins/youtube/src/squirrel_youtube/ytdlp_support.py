from __future__ import annotations

import importlib.util
import os
import shutil
import threading
from pathlib import Path
from typing import Any

from crawl import filter_cookies_to_query_string, resolve_cookie_file_path


YOUTUBE_PLAYER_CLIENT = 'android'
YOUTUBE_COOKIE_PLAYER_CLIENTS = ['tv', 'web']
YOUTUBE_POT_PLAYER_CLIENTS = ['mweb']

YOUTUBE_POT_PROVIDER_MODE_ENV = 'SQUIRREL_YOUTUBE_POT_PROVIDER_MODE'
YOUTUBE_POT_PROVIDER_BASE_URL_ENV = 'SQUIRREL_YOUTUBE_POT_PROVIDER_BASE_URL'
YOUTUBE_POT_PROVIDER_SERVER_HOME_ENV = 'SQUIRREL_YOUTUBE_POT_PROVIDER_SERVER_HOME'

YOUTUBE_POT_PROVIDER_MODE_AUTO = 'auto'
YOUTUBE_POT_PROVIDER_MODE_OFF = 'off'
YOUTUBE_POT_PROVIDER_MODE_SCRIPT = 'script'
YOUTUBE_POT_PROVIDER_MODE_HTTP = 'http'

DEFAULT_BGUTIL_SERVER_HOME = Path.home() / 'bgutil-ytdlp-pot-provider' / 'server'
YOUTUBE_PLAYER_RESPONSES_INFO_KEY = '_youtube_player_responses'
YOUTUBE_PLAYER_URL_INFO_KEY = '_youtube_player_url'

_YOUTUBE_PLAYER_RESPONSES_ATTR = '_squirrel_youtube_player_responses'
_YOUTUBE_PLAYER_URL_ATTR = '_squirrel_youtube_player_url'
_YOUTUBE_EXTRACT_HOOK_LOCK = threading.RLock()
_SKIP_VALUE = object()


def _read_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _resolve_pot_provider_mode() -> str:
    mode = (_read_env(YOUTUBE_POT_PROVIDER_MODE_ENV) or YOUTUBE_POT_PROVIDER_MODE_AUTO).lower()
    if mode in {
        YOUTUBE_POT_PROVIDER_MODE_AUTO,
        YOUTUBE_POT_PROVIDER_MODE_OFF,
        YOUTUBE_POT_PROVIDER_MODE_SCRIPT,
        YOUTUBE_POT_PROVIDER_MODE_HTTP,
    }:
        return mode
    return YOUTUBE_POT_PROVIDER_MODE_AUTO


def _has_bgutil_script_plugin() -> bool:
    return importlib.util.find_spec('yt_dlp_plugins.extractor.getpot_bgutil_script') is not None


def _has_bgutil_http_plugin() -> bool:
    return importlib.util.find_spec('yt_dlp_plugins.extractor.getpot_bgutil_http') is not None


def _resolve_bgutil_server_home() -> Path:
    configured = _read_env(YOUTUBE_POT_PROVIDER_SERVER_HOME_ENV)
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_BGUTIL_SERVER_HOME


def _resolve_script_provider_args() -> dict[str, list[str]] | None:
    if not _has_bgutil_script_plugin():
        return None
    if not shutil.which('node'):
        return None

    server_home = _resolve_bgutil_server_home()
    script_path = server_home / 'build' / 'generate_once.js'
    if not script_path.is_file():
        return None

    return {'server_home': [str(server_home)]}


def _resolve_http_provider_args(*, require_explicit_base_url: bool) -> dict[str, list[str]] | dict | None:
    if not _has_bgutil_http_plugin():
        return None

    base_url = _read_env(YOUTUBE_POT_PROVIDER_BASE_URL_ENV)
    if require_explicit_base_url and not base_url:
        return None
    if base_url:
        return {'base_url': [base_url]}
    return {}


def _resolve_pot_provider_args() -> tuple[str, dict] | None:
    mode = _resolve_pot_provider_mode()
    if mode == YOUTUBE_POT_PROVIDER_MODE_OFF:
        return None

    if mode == YOUTUBE_POT_PROVIDER_MODE_SCRIPT:
        script_args = _resolve_script_provider_args()
        if script_args is None:
            return None
        return 'youtubepot-bgutilscript', script_args

    if mode == YOUTUBE_POT_PROVIDER_MODE_HTTP:
        http_args = _resolve_http_provider_args(require_explicit_base_url=False)
        if http_args is None:
            return None
        return 'youtubepot-bgutilhttp', http_args

    script_args = _resolve_script_provider_args()
    if script_args is not None:
        return 'youtubepot-bgutilscript', script_args

    http_args = _resolve_http_provider_args(require_explicit_base_url=True)
    if http_args is not None:
        return 'youtubepot-bgutilhttp', http_args

    return None


def apply_youtube_auth(url: str, opts: dict) -> bool:
    cookie_file = resolve_cookie_file_path(url)
    if cookie_file:
        opts['cookiefile'] = cookie_file
        return True

    cookies = filter_cookies_to_query_string(url)
    if cookies:
        opts['cookie'] = cookies
        return True

    return False


def apply_youtube_player_strategy(url: str, opts: dict) -> None:
    extractor_args = opts.setdefault('extractor_args', {})
    youtube_args = extractor_args.setdefault('youtube', {})
    youtube_args['player_client'] = [YOUTUBE_PLAYER_CLIENT]

    has_cookie_auth = apply_youtube_auth(url, opts)
    if not has_cookie_auth:
        return

    pot_provider = _resolve_pot_provider_args()
    if pot_provider is not None:
        provider_name, provider_args = pot_provider
        youtube_args['player_client'] = list(YOUTUBE_POT_PLAYER_CLIENTS)
        extractor_args[provider_name] = provider_args
        return

    youtube_args['player_client'] = list(YOUTUBE_COOKIE_PLAYER_CLIENTS)


def _sanitize_player_response_value(value: Any):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if callable(item):
                continue
            cleaned = _sanitize_player_response_value(item)
            if cleaned is _SKIP_VALUE:
                continue
            sanitized[key] = cleaned
        return sanitized
    if isinstance(value, (list, tuple)):
        items = []
        for item in value:
            cleaned = _sanitize_player_response_value(item)
            if cleaned is _SKIP_VALUE:
                continue
            items.append(cleaned)
        return items
    return _SKIP_VALUE


def extract_info_with_player_responses(url: str, opts: dict[str, Any]) -> dict | None:
    from yt_dlp import YoutubeDL

    try:
        from yt_dlp.extractor.youtube._video import YoutubeIE
    except Exception:
        with YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    original_extract_player_responses = YoutubeIE._extract_player_responses
    original_real_extract = YoutubeIE._real_extract

    def patched_extract_player_responses(self, *args, **kwargs):
        player_responses, player_url = original_extract_player_responses(self, *args, **kwargs)
        sanitized = _sanitize_player_response_value(player_responses)
        if isinstance(sanitized, list):
            setattr(self, _YOUTUBE_PLAYER_RESPONSES_ATTR, sanitized)
        setattr(self, _YOUTUBE_PLAYER_URL_ATTR, player_url)
        return player_responses, player_url

    def patched_real_extract(self, video_url):
        info = original_real_extract(self, video_url)
        if isinstance(info, dict):
            player_responses = getattr(self, _YOUTUBE_PLAYER_RESPONSES_ATTR, None)
            if isinstance(player_responses, list):
                info[YOUTUBE_PLAYER_RESPONSES_INFO_KEY] = player_responses
            player_url = getattr(self, _YOUTUBE_PLAYER_URL_ATTR, None)
            if isinstance(player_url, str) and player_url:
                info[YOUTUBE_PLAYER_URL_INFO_KEY] = player_url
        return info

    with _YOUTUBE_EXTRACT_HOOK_LOCK:
        YoutubeIE._extract_player_responses = patched_extract_player_responses
        YoutubeIE._real_extract = patched_real_extract
        try:
            with YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        finally:
            YoutubeIE._extract_player_responses = original_extract_player_responses
            YoutubeIE._real_extract = original_real_extract
