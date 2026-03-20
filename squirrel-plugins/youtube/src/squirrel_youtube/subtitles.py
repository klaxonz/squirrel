from __future__ import annotations

import glob
import os
import re
import tempfile
from typing import Tuple

from yt_dlp import YoutubeDL

from crawl import SubtitlesProvider, register_subtitles

YOUTUBE_PLAYER_CLIENT = 'android'


@register_subtitles
class YoutubeSubtitlesProvider:
    """YouTube字幕提供者，实现SubtitlesProvider Protocol"""
    
    domain = 'youtube.com'

    def get_subtitles(self, video, lang: str, fmt: str = 'srt') -> Tuple[str, str]:
        if fmt.lower() != 'srt':
            raise ValueError('Only srt format is supported')

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
                'extractor_args': {
                    'youtube': {
                        'player_client': [YOUTUBE_PLAYER_CLIENT],
                    }
                },
                'postprocessors': [{
                    'key': 'FFmpegSubtitlesConvertor',
                    'format': 'srt'
                }],
                'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
            }

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([video.url])

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
            filename = f"{base}.{lang}.srt"
            return srt_text, filename


