from __future__ import annotations

import copy
import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from crawl import filter_cookies_to_query_string, resolve_cookie_file_path

YOUTUBE_PLAYER_CLIENT = "android"
YOUTUBE_COOKIE_PLAYER_CLIENTS = ["tv", "web"]
YOUTUBE_POT_PLAYER_CLIENTS = ["mweb"]

YOUTUBE_POT_PROVIDER_MODE_ENV = "SQUIRREL_YOUTUBE_POT_PROVIDER_MODE"
YOUTUBE_POT_PROVIDER_BASE_URL_ENV = "SQUIRREL_YOUTUBE_POT_PROVIDER_BASE_URL"
YOUTUBE_POT_PROVIDER_SERVER_HOME_ENV = "SQUIRREL_YOUTUBE_POT_PROVIDER_SERVER_HOME"

YOUTUBE_POT_PROVIDER_MODE_AUTO = "auto"
YOUTUBE_POT_PROVIDER_MODE_OFF = "off"
YOUTUBE_POT_PROVIDER_MODE_SCRIPT = "script"
YOUTUBE_POT_PROVIDER_MODE_HTTP = "http"

LOCAL_BGUTIL_SERVER_HOME = Path(__file__).with_name("node")
YOUTUBE_PLAYER_RESPONSES_INFO_KEY = "_youtube_player_responses"
YOUTUBE_PLAYER_URL_INFO_KEY = "_youtube_player_url"

_YOUTUBE_PLAYER_RESPONSES_ATTR = "_squirrel_youtube_player_responses"
_YOUTUBE_PLAYER_URL_ATTR = "_squirrel_youtube_player_url"
_YOUTUBE_EXTRACT_HOOK_LOCK = threading.RLock()
_SKIP_VALUE = object()
_PLAYBACK_WORKER_PATH = Path(__file__).with_name("playback_worker.py")
logger = logging.getLogger(__name__)


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
    return importlib.util.find_spec("yt_dlp_plugins.extractor.getpot_bgutil_script") is not None


def _has_bgutil_http_plugin() -> bool:
    return importlib.util.find_spec("yt_dlp_plugins.extractor.getpot_bgutil_http") is not None


def _resolve_bgutil_server_home() -> Path:
    configured = _read_env(YOUTUBE_POT_PROVIDER_SERVER_HOME_ENV)
    if configured:
        return Path(configured).expanduser()
    return LOCAL_BGUTIL_SERVER_HOME


def _resolve_script_provider_args() -> dict[str, list[str]] | None:
    if not _has_bgutil_script_plugin():
        return None
    if not shutil.which("node"):
        return None

    server_home = _resolve_bgutil_server_home()
    script_path = server_home / "build" / "generate_once.js"
    if not script_path.is_file():
        return None

    return {"server_home": [str(server_home)]}


def _resolve_http_provider_args(*, require_explicit_base_url: bool) -> dict[str, list[str]] | dict | None:
    if not _has_bgutil_http_plugin():
        return None

    base_url = _read_env(YOUTUBE_POT_PROVIDER_BASE_URL_ENV)
    if require_explicit_base_url and not base_url:
        return None
    if base_url:
        return {"base_url": [base_url]}
    return {}


def _resolve_pot_provider_args() -> tuple[str, dict] | None:
    mode = _resolve_pot_provider_mode()
    if mode == YOUTUBE_POT_PROVIDER_MODE_OFF:
        return None

    if mode == YOUTUBE_POT_PROVIDER_MODE_SCRIPT:
        script_args = _resolve_script_provider_args()
        if script_args is None:
            return None
        return "youtubepot-bgutilscript", script_args

    if mode == YOUTUBE_POT_PROVIDER_MODE_HTTP:
        http_args = _resolve_http_provider_args(require_explicit_base_url=False)
        if http_args is None:
            return None
        return "youtubepot-bgutilhttp", http_args

    script_args = _resolve_script_provider_args()
    if script_args is not None:
        return "youtubepot-bgutilscript", script_args

    http_args = _resolve_http_provider_args(require_explicit_base_url=True)
    if http_args is not None:
        return "youtubepot-bgutilhttp", http_args

    return None


def apply_youtube_auth(url: str, opts: dict) -> bool:
    cookie_file = resolve_cookie_file_path(url)
    if cookie_file:
        opts["cookiefile"] = cookie_file
        return True

    cookies = filter_cookies_to_query_string(url)
    if cookies:
        opts["cookie"] = cookies
        return True

    return False


def apply_youtube_player_strategy(url: str, opts: dict) -> None:
    extractor_args = opts.setdefault("extractor_args", {})
    youtube_args = extractor_args.setdefault("youtube", {})
    youtube_args["player_client"] = [YOUTUBE_PLAYER_CLIENT]

    has_cookie_auth = apply_youtube_auth(url, opts)
    if not has_cookie_auth:
        return

    pot_provider = _resolve_pot_provider_args()
    if pot_provider is not None:
        provider_name, provider_args = pot_provider
        youtube_args["player_client"] = list(YOUTUBE_POT_PLAYER_CLIENTS)
        extractor_args[provider_name] = provider_args
        return

    youtube_args["player_client"] = list(YOUTUBE_COOKIE_PLAYER_CLIENTS)


@contextmanager
def prepared_ytdlp_opts(opts: dict[str, Any]):
    cookie_file = opts.get("cookiefile")
    if not isinstance(cookie_file, str) or not cookie_file.strip():
        yield opts
        return

    source_path = Path(cookie_file).expanduser()
    if not source_path.is_file():
        yield opts
        return

    with tempfile.TemporaryDirectory(prefix="squirrel-ytdlp-cookies-") as temp_dir:
        temp_cookie_path = Path(temp_dir) / source_path.name
        shutil.copyfile(source_path, temp_cookie_path)
        prepared_opts = dict(opts)
        prepared_opts["cookiefile"] = str(temp_cookie_path)
        yield prepared_opts


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


def _extract_info_once(url: str, opts: dict[str, Any], *, process: bool = True) -> dict | None:
    from yt_dlp import YoutubeDL

    with prepared_ytdlp_opts(opts) as prepared_opts:
        with YoutubeDL(prepared_opts) as ydl:
            return ydl.extract_info(url, download=False, process=process)


def _extract_info_with_hooks_once(url: str, opts: dict[str, Any], *, process: bool = True) -> dict | None:
    from yt_dlp import YoutubeDL

    try:
        from yt_dlp.extractor.youtube._video import YoutubeIE
    except ImportError:
        return _extract_info_once(url, opts, process=process)

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
            with prepared_ytdlp_opts(opts) as prepared_opts:
                with YoutubeDL(prepared_opts) as ydl:
                    return ydl.extract_info(url, download=False, process=process)
        finally:
            YoutubeIE._extract_player_responses = original_extract_player_responses
            YoutubeIE._real_extract = original_real_extract


def _uses_bgutil_script_provider(opts: dict[str, Any]) -> bool:
    extractor_args = opts.get("extractor_args")
    if not isinstance(extractor_args, dict):
        return False
    return "youtubepot-bgutilscript" in extractor_args


def _is_bgutil_script_timeout(exc: Exception, opts: dict[str, Any]) -> bool:
    if not _uses_bgutil_script_provider(opts):
        return False
    if isinstance(exc, subprocess.TimeoutExpired):
        command = exc.cmd
        if isinstance(command, (list, tuple)):
            command_text = " ".join(str(part) for part in command)
        else:
            command_text = str(command)
        return "generate_once." in command_text
    message = str(exc).lower()
    return "generate_once." in message and "timed out" in message


def _build_bgutil_timeout_fallback_opts(opts: dict[str, Any]) -> dict[str, Any]:
    fallback_opts = copy.deepcopy(opts)
    extractor_args = fallback_opts.setdefault("extractor_args", {})
    extractor_args.pop("youtubepot-bgutilscript", None)
    extractor_args.pop("youtubepot-bgutilhttp", None)
    youtube_args = extractor_args.setdefault("youtube", {})
    youtube_args["player_client"] = list(YOUTUBE_COOKIE_PLAYER_CLIENTS)
    return fallback_opts


def _sanitize_json_value(value: Any):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            cleaned = _sanitize_json_value(item)
            if cleaned is _SKIP_VALUE:
                continue
            sanitized[str(key)] = cleaned
        return sanitized
    if isinstance(value, (list, tuple)):
        items = []
        for item in value:
            cleaned = _sanitize_json_value(item)
            if cleaned is _SKIP_VALUE:
                continue
            items.append(cleaned)
        return items
    return _SKIP_VALUE


def _parse_playback_worker_output(stdout: str, stderr: str, returncode: int) -> dict | None:
    payload_text = (stdout or "").strip()
    payload = {}
    if payload_text:
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"YouTube playback worker returned invalid JSON: {exc}"
            ) from exc

    if returncode != 0:
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict) and error.get("message"):
            raise RuntimeError(str(error["message"]))
        message = (stderr or "").strip() or payload_text or "YouTube playback worker failed"
        raise RuntimeError(message)

    if not isinstance(payload, dict):
        raise RuntimeError("YouTube playback worker returned an invalid payload")
    return payload.get("info")


def _extract_with_bgutil_timeout_fallback(extract_fn, url: str, opts: dict[str, Any], *, process: bool) -> dict | None:
    try:
        return extract_fn(url, opts, process=process)
    except Exception as exc:  # yt-dlp extraction boundary — must check for specific timeout condition
        if not _is_bgutil_script_timeout(exc, opts):
            raise

        logger.warning(
            "bgutil script provider timed out during YouTube extraction; retrying without POT provider",
            extra={"url": url, "error": str(exc)},
        )
        fallback_opts = _build_bgutil_timeout_fallback_opts(opts)
        return extract_fn(url, fallback_opts, process=process)


def extract_info(url: str, opts: dict[str, Any], *, process: bool = True) -> dict | None:
    return _extract_with_bgutil_timeout_fallback(
        _extract_info_once,
        url,
        opts,
        process=process,
    )


def extract_info_with_player_responses(url: str, opts: dict[str, Any], *, process: bool = True) -> dict | None:
    return _extract_with_bgutil_timeout_fallback(
        _extract_info_with_hooks_once,
        url,
        opts,
        process=process,
    )


def extract_info_with_player_responses_isolated(
    url: str,
    opts: dict[str, Any],
    *,
    process: bool = True,
    timeout_seconds: float | None = None,
) -> dict | None:
    payload = _sanitize_json_value({
        "url": url,
        "opts": opts,
        "process": process,
    })
    if payload is _SKIP_VALUE:
        raise RuntimeError("YouTube playback worker payload could not be serialized")

    completed = subprocess.run(
        [sys.executable, str(_PLAYBACK_WORKER_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return _parse_playback_worker_output(
        completed.stdout,
        completed.stderr,
        completed.returncode,
    )
