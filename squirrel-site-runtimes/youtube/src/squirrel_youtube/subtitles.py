from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from typing import Any, Tuple

from crawl import NoSubtitlesError

from .video_id import extract_youtube_video_id
from .youtubei_resolver import resolve_captions_with_youtubei


def _safe_int(value: Any) -> int | None:
    try:
        return int(str(value))
    except (ValueError, TypeError):
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


def _extract_segmented_entries(paragraph: ET.Element, start_ms: int, duration_ms: int | None) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    has_relative_timing = False
    for segment in paragraph.findall('./s'):
        raw_text = html.unescape(''.join(segment.itertext()) or '').replace('\xa0', ' ')
        if not _normalize_caption_text(raw_text):
            continue

        relative_start_ms = _safe_int(segment.attrib.get('t'))
        if relative_start_ms is not None:
            has_relative_timing = True

        segments.append({
            'relative_start_ms': max(relative_start_ms or 0, 0),
            'raw_text': raw_text,
        })

    if not segments or not has_relative_timing:
        return []

    entries: list[dict[str, Any]] = []
    cumulative_parts: list[str] = []
    for index, segment in enumerate(segments):
        cumulative_parts.append(segment['raw_text'])
        cue_start_ms = start_ms + int(segment['relative_start_ms'])

        if index + 1 < len(segments):
            next_relative_start_ms = int(segments[index + 1]['relative_start_ms'])
            cue_duration_ms = max(0, next_relative_start_ms - int(segment['relative_start_ms']))
        elif isinstance(duration_ms, int) and duration_ms > 0:
            cue_duration_ms = max(0, duration_ms - int(segment['relative_start_ms']))
        else:
            cue_duration_ms = None

        entries.append({
            'start_ms': cue_start_ms,
            'duration_ms': cue_duration_ms,
            'text': _normalize_caption_text(''.join(cumulative_parts)),
        })

    return [entry for entry in entries if entry['text']]


def _extract_timedtext_entries(xml_text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise NoSubtitlesError('No subtitles available: invalid timedtext payload') from exc

    entries: list[dict[str, Any]] = []
    for paragraph in root.findall('.//p'):
        start_ms = _safe_int(paragraph.attrib.get('t'))
        if start_ms is None:
            continue

        duration_ms = _safe_int(paragraph.attrib.get('d'))
        segmented_entries = _extract_segmented_entries(paragraph, start_ms, duration_ms)
        if segmented_entries:
            entries.extend(segmented_entries)
            continue

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
        raise NoSubtitlesError()

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
        normalized_fmt = str(fmt or 'srt').strip().lower()
        if normalized_fmt not in {'srt', 'vtt'}:
            raise ValueError('Only srt and vtt formats are supported')
        return self._do_get_subtitles(video, lang, normalized_fmt)

    def _do_get_subtitles(self, video, lang: str, fmt: str) -> Tuple[str, str]:
        video_id = extract_youtube_video_id(getattr(video, 'url', '') or '') or str(getattr(video, 'id', 'video'))
        try:
            payload = resolve_captions_with_youtubei(video_id, lang, fmt=fmt)
        except ValueError as exc:
            raise NoSubtitlesError(str(exc) or 'No subtitles available') from exc
        content = str(payload.get('content') or '').strip()
        if not content:
            raise NoSubtitlesError()

        resolved_language = str(payload.get('language_code') or lang or 'default').strip() or 'default'
        if fmt == 'vtt':
            filename = f'{video_id}.{resolved_language}.vtt'
            return content, filename

        entries = _extract_timedtext_entries(content)
        srt_text = _entries_to_srt(entries)
        filename = f'{video_id}.{resolved_language}.srt'
        return srt_text, filename
