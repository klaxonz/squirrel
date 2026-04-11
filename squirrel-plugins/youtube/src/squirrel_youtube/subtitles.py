from __future__ import annotations

import glob
import logging
import os
import re
import tempfile
from typing import Tuple

from yt_dlp import YoutubeDL

from crawl import SubtitlesProvider, resolve_cookie_file_path
from . import ytdlp_support as youtube_ytdlp_support

logger = logging.getLogger(__name__)


class YoutubeSubtitlesProvider:
    """YouTube字幕提供者，实现SubtitlesProvider Protocol"""

    domain = 'youtube.com'

    def get_subtitles(self, video, lang: str, fmt: str = 'srt') -> Tuple[str, str]:
        if fmt.lower() != 'srt':
            raise ValueError('Only srt format is supported')

        cookie_file = resolve_cookie_file_path(video.url)
        original_cookie_content = None
        if cookie_file:
            try:
                original_cookie_content = open(cookie_file, 'r', encoding='utf-8').read()
            except Exception:
                original_cookie_content = None

        try:
            return self._do_get_subtitles(video, lang)
        finally:
            if cookie_file and original_cookie_content is not None:
                try:
                    with open(cookie_file, 'w', encoding='utf-8') as f:
                        f.write(original_cookie_content)
                except Exception as exc:
                    logger.warning('Failed to restore cookie file %s after yt-dlp: %s', cookie_file, exc)

    def _do_get_subtitles(self, video, lang: str) -> Tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                return self._download_subtitles(video, lang, tmpdir, use_runtime_auth_strategy=True)
            except ValueError as exc:
                if not self._should_retry_without_auth(exc):
                    if not self._is_transient_bot_challenge(exc):
                        raise
                    logger.info('Retrying YouTube subtitle extraction after bot challenge for %s', video.url)
                    try:
                        return self._download_subtitles(video, lang, tmpdir, use_runtime_auth_strategy=False)
                    except ValueError as retry_exc:
                        if not self._is_transient_bot_challenge(retry_exc):
                            raise
                        logger.info('Retrying YouTube subtitle extraction after repeated bot challenge for %s', video.url)
                        return self._download_subtitles(video, lang, tmpdir, use_runtime_auth_strategy=False)
                logger.info('Retrying YouTube subtitle extraction without authenticated player strategy for %s', video.url)
                try:
                    return self._download_subtitles(video, lang, tmpdir, use_runtime_auth_strategy=False)
                except ValueError as retry_exc:
                    if not self._is_transient_bot_challenge(retry_exc):
                        raise
                    logger.info('Retrying YouTube subtitle extraction after unauthenticated bot challenge for %s', video.url)
                    return self._download_subtitles(video, lang, tmpdir, use_runtime_auth_strategy=False)

    def _build_ydl_opts(self, video, lang: str, tmpdir: str, *, use_runtime_auth_strategy: bool) -> dict:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [lang],
            'subtitlesformat': 'srt',
            'extractor_args': {
                'youtube': {
                    'player_client': [youtube_ytdlp_support.YOUTUBE_PLAYER_CLIENT],
                }
            },
            'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
        }
        if use_runtime_auth_strategy:
            youtube_ytdlp_support.apply_youtube_player_strategy(video.url, ydl_opts)
        return ydl_opts

    @staticmethod
    def _uses_authenticated_strategy(ydl_opts: dict) -> bool:
        return bool(ydl_opts.get('cookiefile') or ydl_opts.get('cookie'))

    def _download_subtitles(
        self,
        video,
        lang: str,
        tmpdir: str,
        *,
        use_runtime_auth_strategy: bool,
    ) -> Tuple[str, str]:
        ydl_opts = self._build_ydl_opts(
            video,
            lang,
            tmpdir,
            use_runtime_auth_strategy=use_runtime_auth_strategy,
        )
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([video.url])
        except Exception as exc:
            logger.warning('yt-dlp subtitle extraction failed for %s: %s', video.url, exc)
            retryable = use_runtime_auth_strategy and self._uses_authenticated_strategy(ydl_opts)
            error = ValueError(f'No subtitles available: {exc}')
            setattr(error, '_retry_without_auth', retryable)
            raise error from exc

        srt_files = glob.glob(os.path.join(tmpdir, '*.srt'))
        preferred = None
        for path in srt_files:
            filename = os.path.basename(path)
            if f'.{lang}.' in filename or filename.endswith(f'.{lang}.srt'):
                preferred = path
                break
        target_path = preferred or (srt_files[0] if srt_files else None)
        if not target_path:
            raise ValueError('No subtitles available')

        with open(target_path, 'r', encoding='utf-8', errors='ignore') as rf:
            srt_text = rf.read()

        vid_match = re.search(r'(?:v=|/shorts/|/live/|/embed/)([\w-]{6,})', video.url)
        base = vid_match.group(1) if vid_match else str(getattr(video, 'id', 'video'))
        filename = f'{base}.{lang}.srt'
        return srt_text, filename

    @staticmethod
    def _should_retry_without_auth(exc: ValueError) -> bool:
        return bool(getattr(exc, '_retry_without_auth', False))

    @staticmethod
    def _is_transient_bot_challenge(exc: ValueError) -> bool:
        message = str(exc).lower()
        return 'sign in to confirm you' in message and 'not a bot' in message
