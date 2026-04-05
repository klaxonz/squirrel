from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'squirrel-plugins' / 'youtube' / 'src'))

from squirrel_youtube.playback_mapper import map_youtubei_result
from squirrel_youtube.youtubei_resolver import YoutubeiFormat, YoutubeiResult


def test_map_youtubei_result_prefers_progressive_and_builds_quality_list():
    result = YoutubeiResult(
        client='ANDROID',
        playability_status='OK',
        formats=[
            YoutubeiFormat(18, 'video/mp4; codecs="avc1.42001E, mp4a.40.2"', '360p', 'https://example.test/18', True, True),
            YoutubeiFormat(137, 'video/mp4; codecs="avc1.640028"', '1080p', 'https://example.test/137', False, True),
            YoutubeiFormat(140, 'audio/mp4; codecs="mp4a.40.2"', 'tiny', 'https://example.test/140', True, False),
        ],
    )

    payload = map_youtubei_result(123, result)

    assert payload['mpd_url'] == '/api/video/mpd?video_id=123'
    assert payload['video_url'] == 'https://example.test/18'
    assert payload['audio_url'] == 'https://example.test/140'
    assert payload['qualities'][0]['label'] == '1080p'


def test_map_youtubei_result_keeps_quality_list_when_only_best_urls_are_resolved():
    result = YoutubeiResult(
        client='MWEB',
        playability_status='OK',
        formats=[
            YoutubeiFormat(399, 'video/mp4; codecs="av01.0.08M.08"', '1080p', None, False, True, bitrate=3000, width=1920, height=1080),
            YoutubeiFormat(248, 'video/webm; codecs="vp9"', '1080p', None, False, True, bitrate=2800, width=1920, height=1080),
            YoutubeiFormat(137, 'video/mp4; codecs="avc1.640028"', '1080p', 'https://example.test/137', False, True, bitrate=2600, width=1920, height=1080),
            YoutubeiFormat(136, 'video/mp4; codecs="avc1.64001f"', '720p', None, False, True, bitrate=1800, width=1280, height=720),
            YoutubeiFormat(251, 'audio/webm; codecs="opus"', 'tiny', 'https://example.test/251', True, False, bitrate=128),
        ],
    )

    payload = map_youtubei_result(123, result)

    assert payload['video_url'] == 'https://example.test/137'
    assert payload['audio_url'] == 'https://example.test/251'
    assert [item['label'] for item in payload['qualities']] == ['1080p', '1080p', '1080p', '720p']
