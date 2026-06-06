from __future__ import annotations

import glob
import logging
import os
import re
import tempfile
from typing import Tuple

from yt_dlp import YoutubeDL

from crawl import SubtitlesProvider, resolve_cookie_file_path

logger = logging.getLogger(__name__)


class BilibiliSubtitlesProvider:
    """Bilibili字幕提供者，实现SubtitlesProvider Protocol"""

    domain = 'bilibili.com'

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
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [lang],
                'subtitlesformat': 'srt',
                'postprocessors': [{
                    'key': 'FFmpegSubtitlesConvertor',
                    'format': 'srt'
                }],
                'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
            }

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video.url])
            except Exception as exc:
                logger.warning('yt-dlp subtitle extraction failed for %s: %s', video.url, exc)
                raise ValueError(f'No subtitles available: {exc}') from exc

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

            bvid_match = re.search(r'(BV[\w-]+)', video.url)
            filename = f'{(bvid_match.group(1) if bvid_match else video.id)}.{lang}.srt'
            return srt_text, filename


