import glob
import os
import re
import tempfile
from typing import Tuple

from yt_dlp import YoutubeDL

from core import config
from models.video import Video
from sites.subtitles_origin import BaseSubtitlesProvider
from sites.subtitles_registry import register_subtitles


@register_subtitles
class BilibiliSubtitlesProvider(BaseSubtitlesProvider):
    domain = 'bilibili.com'

    def get_subtitles(self, video: Video, lang: str, fmt: str = 'srt') -> Tuple[str, str]:
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
                'postprocessors': [{
                    'key': 'FFmpegSubtitlesConvertor',
                    'format': 'srt'
                }],
                'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
            }

            cookie_file_path = config.get_cookies_file_path()
            # 保持与原逻辑一致：仅非 YouTube 才使用 cookies
            if cookie_file_path and 'youtube.com' not in video.url:
                ydl_opts['cookiefile'] = cookie_file_path

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

            bvid_match = re.search(r'(BV[\w-]+)', video.url)
            filename = f"{(bvid_match.group(1) if bvid_match else video.id)}.{lang}.srt"
            return srt_text, filename

