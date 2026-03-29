from __future__ import annotations

import glob
import os
import re
import tempfile
from typing import Tuple

from yt_dlp import YoutubeDL

from crawl import SubtitlesProvider
try:
    from . import ytdlp_support as youtube_ytdlp_support
except ImportError:  # pragma: no cover - fallback for direct module loading
    import importlib.util
    import sys
    from pathlib import Path

    _HELPER_PATH = Path(__file__).with_name('ytdlp_support.py')
    _HELPER_SPEC = importlib.util.spec_from_file_location('_youtube_ytdlp_support', _HELPER_PATH)
    youtube_ytdlp_support = importlib.util.module_from_spec(_HELPER_SPEC)
    assert _HELPER_SPEC is not None and _HELPER_SPEC.loader is not None
    sys.modules['_youtube_ytdlp_support'] = youtube_ytdlp_support
    _HELPER_SPEC.loader.exec_module(youtube_ytdlp_support)

YOUTUBE_PLAYER_CLIENT = youtube_ytdlp_support.YOUTUBE_PLAYER_CLIENT
YOUTUBE_COOKIE_PLAYER_CLIENTS = youtube_ytdlp_support.YOUTUBE_COOKIE_PLAYER_CLIENTS


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

            youtube_ytdlp_support.apply_youtube_player_strategy(video.url, ydl_opts)

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


