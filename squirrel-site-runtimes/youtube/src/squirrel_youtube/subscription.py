from __future__ import annotations

import logging
import re
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

from . import ytdlp_support as youtube_ytdlp_support

logger = logging.getLogger(__name__)

FULL_SYNC_BATCH_SIZE = 100
HEAD_SAMPLE_LIMIT = 10
_CHANNEL_SOURCES: tuple[str, ...] = ('videos', 'shorts')
_UNSET = object()


class YoutubeSubscription:
    def __init__(self, url: str) -> None:
        self.url = url.rstrip('/')
        self.is_playlist = self._is_playlist_url(self.url)
        self._metadata_cache: dict[str, Any] | None = None
        self._total_available_cache: int | None | object = _UNSET

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
        video_urls, latest_video_url, stop_reason, cursor_payload, has_more, result_kwargs = self._collect_videos(context)
        if context.mode == 'full' and 'total_available' not in result_kwargs:
            total_available = self._resolve_total_available()
            if total_available is not None:
                result_kwargs['total_available'] = total_available
        return build_subscription_sync_result(
            video_urls=video_urls,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason=stop_reason,
            cursor_payload=cursor_payload,
            has_more=has_more,
            **result_kwargs,
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
    ) -> tuple[list[str], str | None, str, dict | None, bool, dict[str, Any]]:
        if self.is_playlist:
            return self._collect_playlist_videos(context)
        return self._collect_channel_videos(context)

    def _collect_playlist_videos(
        self,
        context: SubscriptionSyncContext,
    ) -> tuple[list[str], str | None, str, dict | None, bool, dict[str, Any]]:
        video_urls: list[str] = []
        latest_video_url: str | None = None
        seen_urls: set[str] = set()
        head_sample_urls: list[str] = []
        limit = resolve_subscription_limit(context)

        if context.mode == 'full':
            offset = self._resolve_playlist_offset(context)
            batch_limit = self._resolve_full_sync_batch_limit(context)
            info = self._extract_source_info(self.url, start=offset + 1, end=offset + batch_limit + 1)
            entries = list(info.get('entries') or [])
            scanned_entry_count = 0

            for entry in entries:
                watch_url = self._resolve_entry_url(entry, source_name='videos')
                if not watch_url or watch_url in seen_urls:
                    scanned_entry_count += 1
                    continue
                seen_urls.add(watch_url)
                if len(video_urls) >= batch_limit:
                    return (
                        video_urls,
                        latest_video_url,
                        'batch_exhausted',
                        {'source': 'playlist', 'offset': offset + scanned_entry_count},
                        True,
                        {},
                    )
                latest_video_url, stop_reason = append_subscription_video_url(
                    watch_url,
                    video_urls=video_urls,
                    context=context,
                    latest_video_url=latest_video_url,
                    limit=None,
                )
                if stop_reason:
                    return video_urls, latest_video_url, stop_reason, None, False, {}
                scanned_entry_count += 1

            if len(entries) >= batch_limit + 1:
                return (
                    video_urls,
                    latest_video_url,
                    'batch_exhausted',
                    {'source': 'playlist', 'offset': offset + len(entries)},
                    True,
                    {},
                )

            return video_urls, latest_video_url, 'source_exhausted', None, False, {}

        info = self._extract_source_info(self.url, end=limit + 1 if limit else None)
        entries = info.get('entries') or []
        for entry in entries:
            watch_url = self._resolve_entry_url(entry, source_name='videos')
            if not watch_url or watch_url in seen_urls:
                continue
            seen_urls.add(watch_url)
            self._append_head_sample(head_sample_urls, watch_url)
            latest_video_url, stop_reason = append_subscription_video_url(
                watch_url,
                video_urls=video_urls,
                context=context,
                latest_video_url=latest_video_url,
                limit=limit,
            )
            if stop_reason:
                return (
                    video_urls,
                    latest_video_url,
                    stop_reason,
                    None,
                    False,
                    self._build_incremental_result_kwargs(
                        context,
                        head_sample_urls=head_sample_urls,
                        anchor_found=True if stop_reason == 'cursor_hit' else None,
                    ),
                )

        return (
            video_urls,
            latest_video_url,
            'source_exhausted',
            None,
            False,
            self._build_incremental_result_kwargs(
                context,
                head_sample_urls=head_sample_urls,
                anchor_found=False if context.last_seen_video_url else None,
            ),
        )

    def _collect_channel_videos(
        self,
        context: SubscriptionSyncContext,
    ) -> tuple[list[str], str | None, str, dict | None, bool, dict[str, Any]]:
        video_urls: list[str] = []
        latest_video_url: str | None = None
        seen_urls: set[str] = set()
        head_sample_urls: list[str] = []
        limit = resolve_subscription_limit(context)

        if context.mode != 'full':
            for source_name in _CHANNEL_SOURCES:
                info = self._extract_source_info(self._build_channel_source_url(source_name), end=limit + 1 if limit else None)
                for entry in info.get('entries') or []:
                    watch_url = self._resolve_entry_url(entry, source_name=source_name)
                    if not watch_url or watch_url in seen_urls:
                        continue
                    seen_urls.add(watch_url)
                    self._append_head_sample(head_sample_urls, watch_url)
                    latest_video_url, stop_reason = append_subscription_video_url(
                        watch_url,
                        video_urls=video_urls,
                        context=context,
                        latest_video_url=latest_video_url,
                        limit=limit,
                    )
                    if stop_reason:
                        return (
                            video_urls,
                            latest_video_url,
                            stop_reason,
                            None,
                            False,
                            self._build_incremental_result_kwargs(
                                context,
                                head_sample_urls=head_sample_urls,
                                anchor_found=True if stop_reason == 'cursor_hit' else None,
                            ),
                        )
            return (
                video_urls,
                latest_video_url,
                'source_exhausted',
                None,
                False,
                self._build_incremental_result_kwargs(
                    context,
                    head_sample_urls=head_sample_urls,
                    anchor_found=False if context.last_seen_video_url else None,
                ),
            )

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
            entries = list(info.get('entries') or [])
            scanned_entry_count = 0

            for entry in entries:
                watch_url = self._resolve_entry_url(entry, source_name=source_name)
                if not watch_url or watch_url in seen_urls:
                    scanned_entry_count += 1
                    continue
                seen_urls.add(watch_url)
                if len(video_urls) >= batch_limit:
                    return (
                        video_urls,
                        latest_video_url,
                        'batch_exhausted',
                        {'source': source_name, 'offset': current_offset + scanned_entry_count},
                        True,
                        {},
                    )
                latest_video_url, stop_reason = append_subscription_video_url(
                    watch_url,
                    video_urls=video_urls,
                    context=context,
                    latest_video_url=latest_video_url,
                    limit=None,
                )
                if stop_reason:
                    return video_urls, latest_video_url, stop_reason, None, False, {}
                scanned_entry_count += 1

            if len(entries) >= remaining + 1:
                return (
                    video_urls,
                    latest_video_url,
                    'batch_exhausted',
                    {'source': source_name, 'offset': current_offset + len(entries)},
                    True,
                    {},
                )

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
                    {},
                )
            return video_urls, latest_video_url, 'source_exhausted', None, False, {}

        return video_urls, latest_video_url, 'source_exhausted', None, False, {}

    @staticmethod
    def _append_head_sample(head_sample_urls: list[str], watch_url: str) -> None:
        if watch_url in head_sample_urls or len(head_sample_urls) >= HEAD_SAMPLE_LIMIT:
            return
        head_sample_urls.append(watch_url)

    @staticmethod
    def _build_incremental_result_kwargs(
        context: SubscriptionSyncContext,
        *,
        head_sample_urls: list[str],
        anchor_found: bool | None,
    ) -> dict[str, Any]:
        if context.mode == 'full':
            return {}
        return {
            'head_sample_urls': list(head_sample_urls),
            'anchor_found': anchor_found,
        }

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

    def _resolve_total_available(self) -> int | None:
        if self._total_available_cache is not _UNSET:
            return self._total_available_cache if isinstance(self._total_available_cache, int) else None

        info = self._extract_source_info(self.url, end=1)
        total_available = self._normalize_total_available(info.get('playlist_count'))
        self._total_available_cache = total_available if total_available is not None else None
        return total_available

    @staticmethod
    def _normalize_total_available(raw_value: Any) -> int | None:
        try:
            total_available = int(raw_value)
        except (TypeError, ValueError):
            return None
        return total_available if total_available >= 0 else None

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
