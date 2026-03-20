from __future__ import annotations

import logging
from xml.etree import ElementTree as ET
from urllib.parse import quote
import struct

import requests
from yt_dlp import YoutubeDL

from crawl import (
    MpdBuilder,
    register_mpd,
    get_http_headers,
)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36'
SITE_SLUG = 'youtube'
YOUTUBE_PLAYER_CLIENT = 'android'
SESSION = requests.Session()
logger = logging.getLogger(__name__)


def _be32(b: bytes, pos: int) -> int:
    return struct.unpack_from('>I', b, pos)[0]


def _be64(b: bytes, pos: int) -> int:
    return struct.unpack_from('>Q', b, pos)[0]


def _find_mp4_boxes_prefix(data: bytes):
    offset = 0
    length = len(data)
    moov_start = moov_end = -1
    sidx_start = sidx_end = -1

    for _ in range(1000):
        if offset + 8 > length:
            break
        try:
            size = _be32(data, offset)
            typ = data[offset + 4: offset + 8]
        except Exception:
            break

        if size == 0:
            box_end = length
        elif size == 1:
            if offset + 16 > length:
                break
            size = _be64(data, offset + 8)
            box_end = offset + int(size)
        else:
            box_end = offset + int(size)

        if box_end > length or size < 8:
            break

        if typ == b'moov':
            moov_start, moov_end = offset, box_end
        elif typ == b'sidx':
            sidx_start, sidx_end = offset, box_end

        if moov_start != -1 and sidx_start != -1:
            break

        offset = box_end

    return moov_start, moov_end, sidx_start, sidx_end


def _probe_ranges(url: str, max_tries: int = 2, chunk_sizes=(1024 * 1024, 4 * 1024 * 1024)):
    headers = get_http_headers(SITE_SLUG, {
        'User-Agent': USER_AGENT,
        'Accept': '*/*',
        'Connection': 'keep-alive',
    })
    for i in range(min(max_tries, len(chunk_sizes))):
        end = chunk_sizes[i] - 1
        try:
            resp = SESSION.get(url, headers={**headers, 'Range': f'bytes=0-{end}'}, timeout=15)
            if resp.status_code not in (200, 206):
                continue
            data = resp.content or b''
            if not data:
                continue
            moov_start, moov_end, sidx_start, sidx_end = _find_mp4_boxes_prefix(data)
            init_range = None
            index_range = None
            if moov_end > 0:
                init_range = f"{0}-{moov_end - 1}"
            if sidx_start >= 0 and sidx_end > sidx_start:
                index_range = f"{sidx_start}-{sidx_end - 1}"
            if init_range or index_range:
                return init_range, index_range
        except Exception:
            continue
    return None, None


def _proxy(u: str) -> str:
    # 保留 URL 结构字符，避免破坏 YouTube 签名
    # safe 参数保留 : / ? & = 等 URL 关键字符
    from urllib.parse import quote
    return f"/api/video/proxy?domain=youtube.com&url=" + quote(u, safe=':/?&=@')

def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default

def _build_ytdlp_opts(url: str) -> dict:
    opts = {
        'quiet': False,
        'skip_download': True,
        'noplaylist': True,
        'ignoreerrors': False,
        'extract_flat': False,
        'extractor_args': {
            'youtube': {
                'player_client': [YOUTUBE_PLAYER_CLIENT],
            }
        },
    }
    return opts


def _extract_video_info(url: str) -> dict | None:
    try:
        opts = _build_ytdlp_opts(url)
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            if info.get('_type') == 'playlist':
                entries = info.get('entries') or []
                if entries:
                    return entries[0]
            return info
    except Exception as exc:
        logger.error("yt-dlp failed to extract info for %s: %s", url, exc)
        return None


def _range_to_str(range_dict) -> str | None:
    if isinstance(range_dict, dict):
        start = range_dict.get('start') or range_dict.get('startMs') or range_dict.get('begin')
        end = range_dict.get('end') or range_dict.get('endMs') or range_dict.get('finish')
        if start is not None and end is not None:
            try:
                return f"{int(start)}-{int(end)}"
            except Exception:
                return f"{start}-{end}"
    return None


def _format_to_rep(fmt: dict) -> dict | None:
    if not isinstance(fmt, dict):
        return None
    stream_url = fmt.get('url')
    if not stream_url:
        return None
    format_id = fmt.get('format_id') or fmt.get('format') or fmt.get('itag')
    if not format_id:
        return None

    vcodec = (fmt.get('vcodec') or '').lower()
    acodec = (fmt.get('acodec') or '').lower()
    video_ext = (fmt.get('video_ext') or '')
    audio_ext = (fmt.get('audio_ext') or '')

    if video_ext:
        has_video = video_ext.lower() != 'none'
    else:
        has_video = bool(vcodec and vcodec != 'none')

    if audio_ext:
        has_audio = audio_ext.lower() != 'none'
    else:
        has_audio = bool(acodec and acodec != 'none')

    is_video = has_video and not has_audio
    is_audio = has_audio and not has_video
    if not (is_video or is_audio):
        return None

    ext = (fmt.get('ext') or '').lower()
    if is_video and ext not in ('mp4',):
        return None
    if is_audio and ext not in ('m4a', 'mp4'):
        return None

    init_range = _range_to_str(fmt.get('init_range') or fmt.get('initRange'))
    index_range = _range_to_str(fmt.get('index_range') or fmt.get('indexRange'))
    if (is_video or is_audio) and (init_range is None or index_range is None):
        probed_init, probed_index = _probe_ranges(stream_url)
        init_range = init_range or probed_init
        index_range = index_range or probed_index

    if not init_range or not index_range:
        return None

    mime_type = fmt.get('mime_type')
    if not mime_type:
        if is_video:
            mime_type = 'video/mp4'
        else:
            mime_type = 'audio/mp4'

    codecs_val = fmt.get('codecs') or (vcodec if is_video else acodec)
    bandwidth = fmt.get('tbr') or fmt.get('abr')
    if bandwidth:
        bandwidth = int(float(bandwidth) * 1000)

    audio_channels = fmt.get('audio_channels') or fmt.get('channels')
    if audio_channels is not None:
        try:
            audio_channels = int(audio_channels)
        except Exception:
            pass
    fps = fmt.get('fps')
    if fps is not None:
        try:
            fps = int(fps)
        except Exception:
            pass
    height = fmt.get('height')
    width = fmt.get('width')
    if height is not None:
        try:
            height = int(height)
        except Exception:
            pass
    if width is not None:
        try:
            width = int(width)
        except Exception:
            pass

    rep = {
        'id': str(format_id),
        'bandwidth': int(bandwidth) if bandwidth else None,
        'mime': mime_type,
        'codecs': codecs_val,
        'url': stream_url,
        'width': width,
        'height': height,
        'fps': fps,
        'audioSamplingRate': str(fmt.get('asr')) if fmt.get('asr') else None,
        'audioChannels': audio_channels,
        'initRange': init_range,
        'indexRange': index_range,
        'kind': 'video' if is_video else 'audio',
        'xml_lang': fmt.get('language'),
        'label': fmt.get('format_note'),
    }
    return rep


@register_mpd
class YouTubeMpdBuilder:
    """YouTube MPD构建器，实现MpdBuilder Protocol"""
    
    domain = 'youtube.com'

    def build_mpd(self, video) -> str:
        info = _extract_video_info(video.url)
        if not info or not info.get('formats'):
            raise RuntimeError("Failed to fetch YouTube stream metadata via yt-dlp")

        kept_by_itag: dict[str, dict] = {}
        for fmt in info.get('formats', []):
            rep = _format_to_rep(fmt)
            if not rep:
                continue
            itag = rep['id']
            if itag not in kept_by_itag:
                kept_by_itag[itag] = rep

        video_reps = []
        audio_reps = []

        for rep in kept_by_itag.values():
            if rep['kind'] == 'video':
                video_reps.append(rep)
            elif rep['kind'] == 'audio':
                audio_reps.append(rep)

        mpd = ET.Element('MPD', xmlns='urn:mpeg:dash:schema:mpd:2011')
        mpd.set('type', 'static')
        mpd.set('profiles', 'urn:mpeg:dash:profile:isoff-on-demand:2011')
        duration_seconds = info.get('duration') or getattr(video, 'duration', None)
        if duration_seconds and isinstance(duration_seconds, (int, float)):
            mpd.set('mediaPresentationDuration', f"PT{int(float(duration_seconds))}S")
        mpd.set('minBufferTime', 'PT4S')

        period = ET.SubElement(mpd, 'Period', start='PT0S')

        def add_rep(parent, r, typ):
            rep_el = ET.SubElement(parent, 'Representation')
            rep_el.set('id', r['id'])
            if r.get('bandwidth'):
                rep_el.set('bandwidth', str(r['bandwidth']))
            if r.get('codecs'):
                rep_el.set('codecs', r['codecs'])
            if r.get('mime'):
                rep_el.set('mimeType', r['mime'])
            if typ == 'video':
                if r.get('width'):
                    rep_el.set('width', str(r['width']))
                if r.get('height'):
                    rep_el.set('height', str(r['height']))
                if r.get('fps'):
                    rep_el.set('frameRate', str(r['fps']))
            else:
                if r.get('audioSamplingRate'):
                    rep_el.set('audioSamplingRate', r['audioSamplingRate'])
                if r.get('xml_lang'):
                    rep_el.set('{http://www.w3.org/XML/1998/namespace}lang', r['xml_lang'])

            if typ == 'audio' and r.get('audioChannels'):
                ET.SubElement(
                    rep_el,
                    'AudioChannelConfiguration',
                    attrib={
                        'schemeIdUri': 'urn:mpeg:dash:23003:3:audio_channel_configuration:2011',
                        'value': str(r['audioChannels'])
                    }
                )
            if typ == 'audio' and r.get('label'):
                lab = ET.SubElement(rep_el, 'Label')
                lab.text = str(r['label'])

            if r.get('url'):
                base = ET.SubElement(rep_el, 'BaseURL')
                base.text = _proxy(r['url'])

            if r.get('initRange') or r.get('indexRange'):
                seg = ET.SubElement(rep_el, 'SegmentBase')
                if r.get('indexRange'):
                    seg.set('indexRange', r['indexRange'])
                init = ET.SubElement(seg, 'Initialization')
                if r.get('initRange'):
                    init.set('range', r['initRange'])

        video_mp4 = [r for r in video_reps if isinstance(r.get('mime'), str) and r['mime'].startswith('video/mp4')]
        audio_mp4 = [r for r in audio_reps if isinstance(r.get('mime'), str) and r['mime'].startswith('audio/mp4')]

        if video_mp4:
            video_sorted = sorted(video_mp4, key=lambda r: (r.get('height') or 0, r.get('bandwidth') or 0), reverse=True)
            video_as = ET.SubElement(period, 'AdaptationSet', contentType='video', segmentAlignment='true')
            for v in video_sorted:
                add_rep(video_as, v, 'video')
        if audio_mp4:
            audio_sorted = sorted(audio_mp4, key=lambda r: (r.get('bandwidth') or 0), reverse=True)
            audio_as = ET.SubElement(period, 'AdaptationSet', contentType='audio', segmentAlignment='true')
            for a in audio_sorted[:1]:
                add_rep(audio_as, a, 'audio')

        return ET.tostring(mpd, encoding='unicode')
