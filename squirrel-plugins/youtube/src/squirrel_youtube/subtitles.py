from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from typing import Any, Tuple

from .video_id import extract_youtube_video_id
from .youtubei_resolver import resolve_captions_with_youtubei


def _safe_int(value: Any) -> int | None:
    try:
        return int(str(value))
    except Exception:
        return None


def _format_srt_timestamp(milliseconds: int) -> str:
    total_ms = max(int(milliseconds), 0)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'


def _normalize_caption_text(value: str) -> str:
    text = html.unescape(value or '')
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s*\n\s*', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def _extract_timedtext_entries(xml_text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError('No subtitles available: invalid timedtext payload') from exc

    entries: list[dict[str, Any]] = []
    for paragraph in root.findall('.//p'):
        start_ms = _safe_int(paragraph.attrib.get('t'))
        if start_ms is None:
            continue

        duration_ms = _safe_int(paragraph.attrib.get('d'))
        text = _normalize_caption_text(''.join(paragraph.itertext()))
        if not text:
            continue

        entries.append({
            'start_ms': start_ms,
            'duration_ms': duration_ms,
            'text': text,
        })

    return entries


def _entries_to_srt(entries: list[dict[str, Any]]) -> str:
    if not entries:
        raise ValueError('No subtitles available')

    lines: list[str] = []
    for index, entry in enumerate(entries, start=1):
        start_ms = int(entry['start_ms'])
        duration_ms = entry.get('duration_ms')
        if isinstance(duration_ms, int) and duration_ms > 0:
            end_ms = start_ms + duration_ms
        elif index < len(entries):
            next_start_ms = int(entries[index]['start_ms'])
            end_ms = max(start_ms + 500, next_start_ms)
        else:
            end_ms = start_ms + 2_000

        lines.extend([
            str(index),
            f'{_format_srt_timestamp(start_ms)} --> {_format_srt_timestamp(end_ms)}',
            str(entry['text']),
            '',
        ])

    return '\n'.join(lines).strip() + '\n'


class YoutubeSubtitlesProvider:
    """YouTube subtitles provider implemented on top of youtubei.js caption tracks."""

    domain = 'youtube.com'

    def get_subtitles(self, video, lang: str, fmt: str = 'srt') -> Tuple[str, str]:
        if fmt.lower() != 'srt':
            raise ValueError('Only srt format is supported')
        return self._do_get_subtitles(video, lang)

    def _do_get_subtitles(self, video, lang: str) -> Tuple[str, str]:
        video_id = extract_youtube_video_id(getattr(video, 'url', '') or '') or str(getattr(video, 'id', 'video'))
        payload = resolve_captions_with_youtubei(video_id, lang)
        timedtext_xml = str(payload.get('content') or '').strip()
        if not timedtext_xml:
            raise ValueError('No subtitles available')

        entries = _extract_timedtext_entries(timedtext_xml)
        srt_text = _entries_to_srt(entries)
        resolved_language = str(payload.get('language_code') or lang or 'default').strip() or 'default'
        filename = f'{video_id}.{resolved_language}.srt'
        return srt_text, filename
