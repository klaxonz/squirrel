from __future__ import annotations

import atexit
import json
import queue
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKER_DIR = Path(__file__).with_name('node')
DAEMON_PATH = WORKER_DIR / 'youtubei_daemon.mjs'
WORKER_TIMEOUT_SECONDS = 20.0
RESULT_CACHE_TTL_SECONDS = 300.0
_RESULT_CACHE: dict[str, tuple[float, 'YoutubeiResult']] = {}
_RESULT_CACHE_LOCK = threading.Lock()
_WORKER_CLIENT: '_YoutubeiWorkerClient | None' = None
_WORKER_CLIENT_LOCK = threading.Lock()
_PREWARM_THREAD: threading.Thread | None = None
_PREWARM_THREAD_LOCK = threading.Lock()


@dataclass(slots=True)
class YoutubeiFormat:
    itag: int | None
    mime_type: str | None
    quality_label: str | None
    url: str | None
    has_audio: bool
    has_video: bool
    bitrate: int | None = None
    width: int | None = None
    height: int | None = None
    audio_quality: str | None = None
    audio_sample_rate: str | None = None
    audio_channels: int | None = None
    init_range: str | None = None
    index_range: str | None = None
    content_length: int | None = None
    language: str | None = None


@dataclass(slots=True)
class YoutubeiResult:
    client: str
    playability_status: str | None
    formats: list[YoutubeiFormat]


def _load_cookie_header_for_target(target_url: str) -> str:
    try:
        from crawl import filter_cookies_to_query_string
    except Exception:
        return ''

    try:
        return str(filter_cookies_to_query_string(target_url) or '').strip()
    except Exception:
        return ''


def _load_youtube_cookie_header(video_id: str) -> str:
    return _load_cookie_header_for_target(f'https://www.youtube.com/watch?v={video_id}')


def _cache_key(video_id: str, cookie_header: str) -> str:
    return f'{video_id}|auth={int(bool(cookie_header))}'


def _range_to_str(range_dict) -> str | None:
    if isinstance(range_dict, dict):
        start = range_dict.get('start') or range_dict.get('startMs') or range_dict.get('begin')
        end = range_dict.get('end') or range_dict.get('endMs') or range_dict.get('finish')
        if start is not None and end is not None:
            return f'{start}-{end}'
    if isinstance(range_dict, str):
        return range_dict
    return None


def parse_worker_payload(stdout: str) -> YoutubeiResult:
    payload = json.loads(stdout)
    if payload.get('status') != 'ok':
        error = payload.get('error') if isinstance(payload, dict) else None
        message = error.get('message') if isinstance(error, dict) else 'youtubei worker did not return success'
        raise ValueError(str(message))

    formats = [
        YoutubeiFormat(
            itag=item.get('itag'),
            mime_type=item.get('mime_type'),
            quality_label=item.get('quality_label'),
            url=item.get('url'),
            has_audio=bool(item.get('has_audio')),
            has_video=bool(item.get('has_video')),
            bitrate=int(item['bitrate']) if item.get('bitrate') is not None else None,
            width=int(item['width']) if item.get('width') is not None else None,
            height=int(item['height']) if item.get('height') is not None else None,
            audio_quality=item.get('audio_quality'),
            audio_sample_rate=str(item['audio_sample_rate']) if item.get('audio_sample_rate') is not None else None,
            audio_channels=int(item['audio_channels']) if item.get('audio_channels') is not None else None,
            init_range=_range_to_str(item.get('init_range')),
            index_range=_range_to_str(item.get('index_range')),
            content_length=int(item['content_length']) if item.get('content_length') is not None else None,
            language=item.get('language'),
        )
        for item in list(payload.get('formats') or [])
    ]
    if not formats:
        raise ValueError('youtubei worker did not return a complete format set')

    return YoutubeiResult(
        client=str(payload.get('client') or ''),
        playability_status=payload.get('playability_status'),
        formats=formats,
    )


def _get_cached_result(cache_key: str) -> YoutubeiResult | None:
    now = time.monotonic()
    with _RESULT_CACHE_LOCK:
        cached = _RESULT_CACHE.get(cache_key)
        if not cached:
            return None
        expires_at, result = cached
        if expires_at <= now:
            _RESULT_CACHE.pop(cache_key, None)
            return None
        return result


def _set_cached_result(cache_key: str, result: YoutubeiResult) -> None:
    with _RESULT_CACHE_LOCK:
        _RESULT_CACHE[cache_key] = (time.monotonic() + RESULT_CACHE_TTL_SECONDS, result)


class _YoutubeiWorkerClient:
    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._io_lock = threading.Lock()
        self._stderr_thread: threading.Thread | None = None
        self._stderr_tail: deque[str] = deque(maxlen=40)
        self._request_seq = 0

    def close(self) -> None:
        with self._io_lock:
            self._stop_process()

    def request(self, payload: dict[str, Any], timeout_seconds: float) -> str:
        with self._io_lock:
            process = self._ensure_process()
            request_payload = dict(payload)
            request_payload.setdefault('request_id', self._next_request_id())
            encoded = json.dumps(request_payload, ensure_ascii=False) + '\n'

            assert process.stdin is not None
            process.stdin.write(encoded)
            process.stdin.flush()

            line = self._readline_with_timeout(process.stdout, timeout_seconds)
            if line is None:
                stderr_tail = ''.join(self._stderr_tail).strip()
                self._stop_process()
                raise subprocess.TimeoutExpired(
                    cmd=['node', str(DAEMON_PATH)],
                    timeout=timeout_seconds,
                    stderr=stderr_tail or None,
                )

            stripped = line.strip()
            if not stripped:
                stderr_tail = ''.join(self._stderr_tail).strip()
                self._stop_process()
                raise RuntimeError(stderr_tail or 'youtubei daemon closed without a response')
            return stripped

    def prewarm(self, cookie_header: str = '') -> None:
        payload: dict[str, Any] = {'action': 'prewarm'}
        if cookie_header:
            payload['cookie'] = cookie_header
        try:
            self.request(payload, timeout_seconds=WORKER_TIMEOUT_SECONDS)
        except Exception:
            return

    def _next_request_id(self) -> str:
        self._request_seq += 1
        return f'yt-{self._request_seq}'

    def _readline_with_timeout(self, stream, timeout_seconds: float) -> str | None:
        if stream is None:
            return None

        result_queue: queue.Queue[tuple[str | None, BaseException | None]] = queue.Queue(maxsize=1)

        def _reader() -> None:
            try:
                result_queue.put((stream.readline(), None))
            except BaseException as exc:  # pragma: no cover - defensive
                result_queue.put((None, exc))

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()
        try:
            line, exc = result_queue.get(timeout=timeout_seconds)
        except queue.Empty:
            return None

        if exc is not None:
            raise RuntimeError(f'youtubei daemon read failed: {exc}') from exc
        return line

    def _ensure_process(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process

        self._stop_process()
        process = subprocess.Popen(  # noqa: S603
            ['node', str(DAEMON_PATH)],
            cwd=str(WORKER_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            bufsize=1,
        )
        self._process = process
        self._stderr_tail.clear()
        self._stderr_thread = threading.Thread(target=self._drain_stderr, args=(process,), daemon=True)
        self._stderr_thread.start()
        return process

    def _stop_process(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        try:
            if process.stdin is not None:
                process.stdin.close()
        except Exception:
            pass
        try:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=2)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    def _drain_stderr(self, process: subprocess.Popen[str]) -> None:
        stream = process.stderr
        if stream is None:
            return
        try:
            for line in stream:
                self._stderr_tail.append(line)
        except Exception:
            return


def _get_worker_client() -> _YoutubeiWorkerClient:
    global _WORKER_CLIENT
    with _WORKER_CLIENT_LOCK:
        if _WORKER_CLIENT is None:
            _WORKER_CLIENT = _YoutubeiWorkerClient()
        return _WORKER_CLIENT


def shutdown_youtubei_worker() -> None:
    global _WORKER_CLIENT
    global _PREWARM_THREAD
    with _PREWARM_THREAD_LOCK:
        _PREWARM_THREAD = None
    with _WORKER_CLIENT_LOCK:
        client = _WORKER_CLIENT
        _WORKER_CLIENT = None
    if client is not None:
        close = getattr(client, 'close', None)
        if callable(close):
            close()


def _run_prewarm(cookie_header: str) -> None:
    global _PREWARM_THREAD
    try:
        _get_worker_client().prewarm(cookie_header)
    finally:
        with _PREWARM_THREAD_LOCK:
            current = threading.current_thread()
            if _PREWARM_THREAD is current:
                _PREWARM_THREAD = None


def prewarm_youtubei_worker() -> None:
    global _PREWARM_THREAD
    cookie_header = _load_cookie_header_for_target('https://www.youtube.com/')
    with _PREWARM_THREAD_LOCK:
        if _PREWARM_THREAD is not None and _PREWARM_THREAD.is_alive():
            return
        thread = threading.Thread(
            target=_run_prewarm,
            args=(cookie_header,),
            name='youtubei-prewarm',
            daemon=True,
        )
        _PREWARM_THREAD = thread
        thread.start()


atexit.register(shutdown_youtubei_worker)


def resolve_with_youtubei(
    video_id: str,
    timeout_seconds: float = WORKER_TIMEOUT_SECONDS,
    resolution_mode: str = 'playback',
) -> YoutubeiResult:
    cookie_header = _load_youtube_cookie_header(video_id)
    cache_key = f'{_cache_key(video_id, cookie_header)}|mode={resolution_mode}'
    cached = _get_cached_result(cache_key)
    if cached:
        return cached

    worker_payload: dict[str, Any] = {'video_id': video_id, 'resolution_mode': resolution_mode}
    if cookie_header:
        worker_payload['cookie'] = cookie_header

    response_text = _get_worker_client().request(worker_payload, timeout_seconds)
    result = parse_worker_payload(response_text)
    _set_cached_result(cache_key, result)
    return result
