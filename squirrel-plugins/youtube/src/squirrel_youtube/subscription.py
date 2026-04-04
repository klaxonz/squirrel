from __future__ import annotations

import importlib.util
import logging
import re
import sys
from pathlib import Path
from typing import Any

from crawl import (
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
    append_subscription_video_url,
    apply_ytdlp_rate_limit,
    build_subscription_sync_result,
    resolve_subscription_limit,
)

try:
    from . import ytdlp_support as youtube_ytdlp_support
except ImportError:  # pragma: no cover - fallback for direct module loading
    _HELPER_PATH = Path(__file__).with_name('ytdlp_support.py')
    _HELPER_SPEC = importlib.util.spec_from_file_location('_youtube_subscription_ytdlp_support', _HELPER_PATH)
    youtube_ytdlp_support = importlib.util.module_from_spec(_HELPER_SPEC)
    assert _HELPER_SPEC is not None and _HELPER_SPEC.loader is not None
    sys.modules['_youtube_subscription_ytdlp_support'] = youtube_ytdlp_support
    _HELPER_SPEC.loader.exec_module(youtube_ytdlp_support)


logger = logging.getLogger(__name__)

FULL_SYNC_BATCH_SIZE = 100
_CHANNEL_SOURCES: tuple[str, ...] = ('videos', 'shorts')


class YoutubeSubscription:
    def __init__(self, url: str) -> None:
        self.url = url.rstrip('/')
        self.is_playlist = self._is_playlist_url(self.url)
        self._metadata_cache: dict[str, Any] | None = None

    @staticmethod
    def _is_playlist_url(url: str) -> bool:
        return 'list=' in url or '/playlist?' in url

    def get_subscribe_info(self) -> SubscriptionMeta:
        info = self._get_metadata()
        if self.is_playlist:
            return SubscriptionMeta(
                info.get('id') or self._extract_playlist_id(self.url),
                info.get('title') or 'YouTube Playlist',
                None,
                self.url,
            )

        channel_id = info.get('channel_id')
        canonical_url = self.url
        if channel_id:
            canonical_url = f'https://www.youtube.com/channel/{channel_id}'
            self.url = canonical_url

        return SubscriptionMeta(
            channel_id,
            info.get('channel') or info.get('uploader') or info.get('title') or 'YouTube Channel',
            self._resolve_thumbnail_url(info),
            canonical_url,
        )

    @staticmethod
    def _extract_playlist_id(url: str) -> str:
        match = re.search(r'list=([^&]+)', url)
        return match.group(1) if match else ''

    def sync_videos(self, context: SubscriptionSyncContext) -> SubscriptionSyncResult:
        video_urls, latest_video_url, stop_reason, cursor_payload, has_more = self._collect_videos(context)
        return build_subscription_sync_result(
            video_urls=video_urls,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason=stop_reason,
            cursor_payload=cursor_payload,
            has_more=has_more,
        )

    @staticmethod
    def _resolve_full_sync_batch_limit(context: SubscriptionSyncContext) -> int:
        if context.limit is None:
            return FULL_SYNC_BATCH_SIZE
        try:
            return max(1, int(context.limit))
        except (TypeError, ValueError):
            return FULL_SYNC_BATCH_SIZE

    def _collect_videos(
        self,
        context: SubscriptionSyncContext,
    ) -> tuple[list[str], str | None, str, dict | None, bool]:
        if self.is_playlist:
            return self._collect_playlist_videos(context)
        return self._collect_channel_videos(context)

    def _collect_playlist_videos(
        self,
        context: SubscriptionSyncContext,
    ) -> tuple[list[str], str | None, str, dict | None, bool]:
        video_urls: list[str] = []
        latest_video_url: str | None = None
        seen_urls: set[str] = set()
        limit = resolve_subscription_limit(context)

        if context.mode == 'full':
            offset = self._resolve_playlist_offset(context)
            batch_limit = self._resolve_full_sync_batch_limit(context)
            info = self._extract_source_info(self.url, start=offset + 1, end=offset + batch_limit + 1)
            entries = info.get('entries') or []

            for entry in entries:
                watch_url = self._resolve_entry_url(entry, source_name='videos')
                if not watch_url or watch_url in seen_urls:
                    continue
                seen_urls.add(watch_url)
                if len(video_urls) >= batch_limit:
                    return (
                        video_urls,
                        latest_video_url,
                        'batch_exhausted',
                        {'source': 'playlist', 'offset': offset + len(video_urls)},
                        True,
                    )
                latest_video_url, stop_reason = append_subscription_video_url(
                    watch_url,
                    video_urls=video_urls,
                    context=context,
                    latest_video_url=latest_video_url,
                    limit=None,
                )
                if stop_reason:
                    return video_urls, latest_video_url, stop_reason, None, False

            return video_urls, latest_video_url, 'source_exhausted', None, False

        info = self._extract_source_info(self.url, end=limit + 1 if limit else None)
        entries = info.get('entries') or []
        for entry in entries:
            watch_url = self._resolve_entry_url(entry, source_name='videos')
            if not watch_url or watch_url in seen_urls:
                continue
            seen_urls.add(watch_url)
            latest_video_url, stop_reason = append_subscription_video_url(
                watch_url,
                video_urls=video_urls,
                context=context,
                latest_video_url=latest_video_url,
                limit=limit,
            )
            if stop_reason:
                return video_urls, latest_video_url, stop_reason, None, False

        return video_urls, latest_video_url, 'source_exhausted', None, False

    def _collect_channel_videos(
        self,
        context: SubscriptionSyncContext,
    ) -> tuple[list[str], str | None, str, dict | None, bool]:
        video_urls: list[str] = []
        latest_video_url: str | None = None
        seen_urls: set[str] = set()
        limit = resolve_subscription_limit(context)

        if context.mode != 'full':
            for source_name in _CHANNEL_SOURCES:
                info = self._extract_source_info(self._build_channel_source_url(source_name), end=limit + 1 if limit else None)
                for entry in info.get('entries') or []:
                    watch_url = self._resolve_entry_url(entry, source_name=source_name)
                    if not watch_url or watch_url in seen_urls:
                        continue
                    seen_urls.add(watch_url)
                    latest_video_url, stop_reason = append_subscription_video_url(
                        watch_url,
                        video_urls=video_urls,
                        context=context,
                        latest_video_url=latest_video_url,
                        limit=limit,
                    )
                    if stop_reason:
                        return video_urls, latest_video_url, stop_reason, None, False
            return video_urls, latest_video_url, 'source_exhausted', None, False

        start_source, source_offset = self._resolve_channel_cursor(context)
        batch_limit = self._resolve_full_sync_batch_limit(context)

        for index, source_name in enumerate(_CHANNEL_SOURCES):
            if index < _CHANNEL_SOURCES.index(start_source):
                continue

            current_offset = source_offset if source_name == start_source else 0
            remaining = batch_limit - len(video_urls)
            if remaining <= 0:
                break

            info = self._extract_source_info(
                self._build_channel_source_url(source_name),
                start=current_offset + 1,
                end=current_offset + remaining + 1,
            )

            added_in_source = 0
            for entry in info.get('entries') or []:
                watch_url = self._resolve_entry_url(entry, source_name=source_name)
                if not watch_url or watch_url in seen_urls:
                    continue
                seen_urls.add(watch_url)
                if len(video_urls) >= batch_limit:
                    return (
                        video_urls,
                        latest_video_url,
                        'batch_exhausted',
                        {'source': source_name, 'offset': current_offset + added_in_source},
                        True,
                    )
                latest_video_url, stop_reason = append_subscription_video_url(
                    watch_url,
                    video_urls=video_urls,
                    context=context,
                    latest_video_url=latest_video_url,
                    limit=None,
                )
                if stop_reason:
                    return video_urls, latest_video_url, stop_reason, None, False
                added_in_source += 1

            if len(video_urls) < batch_limit:
                continue

            next_source = self._next_channel_source(source_name)
            if next_source is not None and self._channel_source_has_entries(next_source):
                return (
                    video_urls,
                    latest_video_url,
                    'batch_exhausted',
                    {'source': next_source, 'offset': 0},
                    True,
                )
            return video_urls, latest_video_url, 'source_exhausted', None, False

        return video_urls, latest_video_url, 'source_exhausted', None, False

    def _get_metadata(self) -> dict[str, Any]:
        if self._metadata_cache is not None:
            return self._metadata_cache

        if self.is_playlist:
            self._metadata_cache = self._extract_source_info(self.url, end=1)
            return self._metadata_cache

        for source_name in _CHANNEL_SOURCES:
            info = self._extract_source_info(self._build_channel_source_url(source_name), end=1)
            if info.get('channel_id') or info.get('channel') or info.get('title'):
                self._metadata_cache = info
                return info

        self._metadata_cache = {}
        return self._metadata_cache

    def _extract_source_info(self, url: str, *, start: int | None = None, end: int | None = None) -> dict[str, Any]:
        ydl_opts = self._build_ytdlp_opts(url, start=start, end=end)
        info = youtube_ytdlp_support.extract_info(url, ydl_opts, process=False)
        return info or {}

    def _build_ytdlp_opts(self, url: str, *, start: int | None = None, end: int | None = None) -> dict[str, Any]:
        ydl_opts: dict[str, Any] = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': 'in_playlist',
            'socket_timeout': 30,
            'retries': 5,
            'extractor_retries': 3,
            'ignoreerrors': True,
            'noplaylist': False,
        }
        if start is not None and start > 0:
            ydl_opts['playliststart'] = start
        if end is not None and end > 0:
            ydl_opts['playlistend'] = end

        youtube_ytdlp_support.apply_youtube_player_strategy(url, ydl_opts)
        return apply_ytdlp_rate_limit('youtube', ydl_opts)

    def _build_channel_source_url(self, source_name: str) -> str:
        return f'{self.url}/{source_name}'

    def _channel_source_has_entries(self, source_name: str) -> bool:
        info = self._extract_source_info(self._build_channel_source_url(source_name), end=1)
        entries = info.get('entries') or []
        return any(self._resolve_entry_url(entry, source_name=source_name) for entry in entries)

    @staticmethod
    def _resolve_entry_url(entry: Any, *, source_name: str) -> str | None:
        if isinstance(entry, str):
            return entry
        if not isinstance(entry, dict):
            return None

        url = entry.get('url') or entry.get('webpage_url') or entry.get('original_url')
        if isinstance(url, str) and url:
            return url

        video_id = entry.get('id')
        if not isinstance(video_id, str) or not video_id:
            return None
        if source_name == 'shorts':
            return f'https://www.youtube.com/shorts/{video_id}'
        return f'https://www.youtube.com/watch?v={video_id}'

    @staticmethod
    def _resolve_thumbnail_url(info: dict[str, Any]) -> str | None:
        for thumbnail in info.get('thumbnails') or []:
            if isinstance(thumbnail, dict) and thumbnail.get('url'):
                return str(thumbnail['url'])
        return None

    @staticmethod
    def _resolve_playlist_offset(context: SubscriptionSyncContext) -> int:
        payload = context.cursor_payload or {}
        raw_offset = payload.get('offset', payload.get('playlist_offset', 0))
        try:
            return max(0, int(raw_offset))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _resolve_channel_cursor(context: SubscriptionSyncContext) -> tuple[str, int]:
        payload = context.cursor_payload or {}
        source = payload.get('source')
        if source in _CHANNEL_SOURCES:
            raw_offset = payload.get('offset', 0)
        else:
            source = 'videos'
            raw_offset = payload.get('videos_offset', payload.get('offset', 0))

        try:
            offset = max(0, int(raw_offset))
        except (TypeError, ValueError):
            offset = 0
        return source, offset

    @staticmethod
    def _next_channel_source(source_name: str) -> str | None:
        try:
            index = _CHANNEL_SOURCES.index(source_name)
        except ValueError:
            return None
        next_index = index + 1
        if next_index >= len(_CHANNEL_SOURCES):
            return None
        return _CHANNEL_SOURCES[next_index]
