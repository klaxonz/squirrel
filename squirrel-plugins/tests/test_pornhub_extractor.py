from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'squirrel-sdk' / 'src'))
sys.path.insert(0, str(ROOT / 'squirrel-plugins' / 'pornhub' / 'src'))

from crawl import ParseError
from squirrel_pornhub import extractor as pornhub_extractor


class _FakeYoutubeDL:
    def __init__(self, _opts):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_info(self, _url, download=False):
        raise RuntimeError(
            'ERROR: [PornHub] 698e147975244: Unable to extract encoded url; '
            'please report this issue on https://github.com/yt-dlp/yt-dlp/issues'
        )


def test_pornhub_extractor_marks_shorties_redirect_as_blocked(monkeypatch):
    monkeypatch.setattr(pornhub_extractor, 'YoutubeDL', _FakeYoutubeDL)
    monkeypatch.setattr(
        pornhub_extractor.PornhubExtractor,
        '_resolve_redirect_target',
        lambda self, url, cookie_file=None: 'https://www.pornhub.com/shorties/698e147975244',
        raising=False,
    )

    extractor = pornhub_extractor.PornhubExtractor()
    monkeypatch.setattr(extractor, '_build_ytdlp_opts', lambda url, queue_name=None: {})

    with pytest.raises(ParseError) as exc_info:
        extractor._extract_with_ytdlp('https://www.pornhub.com/view_video.php?viewkey=698e147975244')

    assert exc_info.value.context['blocked_reason_code'] == 'unsupported_short_redirect'
    assert exc_info.value.context['redirect_target'] == 'https://www.pornhub.com/shorties/698e147975244'
