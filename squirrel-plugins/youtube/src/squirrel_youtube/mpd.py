from __future__ import annotations

import logging
import shutil
import struct
import threading
import time
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

import requests
from yt_dlp import YoutubeDL

from crawl import (
    AuthError,
    NetworkError,
    ParseError,
    apply_ytdlp_rate_limit,
    filter_cookies_to_query_string,
    resolve_cookie_file_path,
    get_http_headers,
)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36'
SITE_SLUG = 'youtube'
YOUTUBE_PLAYER_CLIENT = 'android'
SESSION = requests.Session()
logger = logging.getLogger(__name__)
VIDEO_INFO_CACHE_TTL_SECONDS = 30
VIDEO_INFO_CACHE_MAX_SIZE = 64
_VIDEO_INFO_CACHE: dict[str, tuple[float, dict]] = {}
_VIDEO_INFO_CACHE_LOCK = threading.Lock()
ISOBMFF_ON_DEMAND_PROFILE = 'urn:mpeg:dash:profile:isoff-on-demand:2011'
WEBM_ON_DEMAND_PROFILE = 'urn:mpeg:dash:profile:webm-on-demand:2012'
_WEBM_EBML_ID = 0x1A45DFA3
_WEBM_SEGMENT_ID = 0x18538067
_WEBM_SEEKHEAD_ID = 0x114D9B74
_WEBM_SEEK_ID = 0x4DBB
_WEBM_SEEKID_ID = 0x53AB
_WEBM_SEEKPOSITION_ID = 0x53AC
_WEBM_CUES_ID = 0x1C53BB6B
_WEBM_CLUSTER_ID = 0x1F43B675
_WEBM_CUES_BYTES = b'\x1C\x53\xBB\x6B'
_WEBM_CLUSTER_BYTES = b'\x1F\x43\xB6\x75'


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


def _probe_mp4_ranges(url: str, max_tries: int = 2, chunk_sizes=(1024 * 1024, 4 * 1024 * 1024)):
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


def _read_vint_length(first_byte: int) -> int | None:
    mask = 0x80
    for length in range(1, 9):
        if first_byte & mask:
            return length
        mask >>= 1
    return None


def _read_ebml_id(data: bytes, pos: int) -> tuple[int, int] | None:
    if pos >= len(data):
        return None
    length = _read_vint_length(data[pos])
    if not length or length > 4 or pos + length > len(data):
        return None
    return int.from_bytes(data[pos:pos + length], 'big'), length


def _read_ebml_size(data: bytes, pos: int) -> tuple[int | None, int] | None:
    if pos >= len(data):
        return None
    length = _read_vint_length(data[pos])
    if not length or pos + length > len(data):
        return None

    value = data[pos] & ((1 << (8 - length)) - 1)
    for idx in range(1, length):
        value = (value << 8) | data[pos + idx]

    unknown_value = (1 << (7 * length)) - 1
    if value == unknown_value:
        return None, length
    return value, length


def _read_ebml_element_end(data: bytes, pos: int) -> int | None:
    id_info = _read_ebml_id(data, pos)
    if not id_info:
        return None
    _, id_len = id_info
    size_info = _read_ebml_size(data, pos + id_len)
    if not size_info:
        return None
    size, size_len = size_info
    if size is None:
        return None
    return pos + id_len + size_len + size


def _find_webm_segment_data_start(data: bytes) -> int | None:
    pos = 0
    data_len = len(data)
    while pos < data_len:
        id_info = _read_ebml_id(data, pos)
        if not id_info:
            return None
        element_id, id_len = id_info
        size_info = _read_ebml_size(data, pos + id_len)
        if not size_info:
            return None
        size, size_len = size_info
        header_end = pos + id_len + size_len
        if element_id == _WEBM_SEGMENT_ID:
            return header_end
        if size is None:
            return None
        pos = header_end + size
    return None


def _parse_seek_entry(data: bytes, start: int, end: int) -> tuple[int | None, int | None]:
    seek_id = None
    seek_pos = None
    pos = start
    while pos < end:
        id_info = _read_ebml_id(data, pos)
        if not id_info:
            break
        element_id, id_len = id_info
        size_info = _read_ebml_size(data, pos + id_len)
        if not size_info:
            break
        size, size_len = size_info
        if size is None:
            break
        value_start = pos + id_len + size_len
        value_end = value_start + size
        if value_end > end:
            break

        if element_id == _WEBM_SEEKID_ID:
            seek_id = int.from_bytes(data[value_start:value_end], 'big')
        elif element_id == _WEBM_SEEKPOSITION_ID:
            seek_pos = int.from_bytes(data[value_start:value_end], 'big')

        pos = value_end
    return seek_id, seek_pos


def _parse_seek_targets(data: bytes, segment_data_start: int) -> dict[int, int]:
    seek_targets: dict[int, int] = {}
    seekhead_pos = data.find(bytes.fromhex('114D9B74'), segment_data_start)
    if seekhead_pos < 0:
        return seek_targets

    seekhead_end = _read_ebml_element_end(data, seekhead_pos)
    if not seekhead_end or seekhead_end > len(data):
        return seek_targets

    id_info = _read_ebml_id(data, seekhead_pos)
    size_info = _read_ebml_size(data, seekhead_pos + id_info[1]) if id_info else None
    if not id_info or not size_info:
        return seek_targets

    payload_start = seekhead_pos + id_info[1] + size_info[1]
    pos = payload_start
    while pos < seekhead_end:
        child_id_info = _read_ebml_id(data, pos)
        if not child_id_info:
            break
        child_id, child_id_len = child_id_info
        child_size_info = _read_ebml_size(data, pos + child_id_len)
        if not child_size_info:
            break
        child_size, child_size_len = child_size_info
        if child_size is None:
            break
        child_start = pos + child_id_len + child_size_len
        child_end = child_start + child_size
        if child_end > seekhead_end:
            break

        if child_id == _WEBM_SEEK_ID:
            seek_id, seek_pos = _parse_seek_entry(data, child_start, child_end)
            if seek_id is not None and seek_pos is not None:
                seek_targets[seek_id] = segment_data_start + seek_pos

        pos = child_end

    return seek_targets


def _fetch_webm_element_end(url: str, offset: int, size: int = 64 * 1024) -> int | None:
    headers = get_http_headers(SITE_SLUG, {
        'User-Agent': USER_AGENT,
        'Accept': '*/*',
        'Connection': 'keep-alive',
        'Range': f'bytes={offset}-{offset + size - 1}',
    })
    try:
        resp = SESSION.get(url, headers=headers, timeout=15)
        if resp.status_code not in (200, 206):
            return None
        data = resp.content or b''
        if not data:
            return None
        element_end = _read_ebml_element_end(data, 0)
        if not element_end:
            return None
        return offset + element_end
    except Exception:
        return None


def _probe_webm_ranges(url: str, max_tries: int = 3, chunk_sizes=(1024 * 1024, 4 * 1024 * 1024, 8 * 1024 * 1024)):
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

            segment_data_start = _find_webm_segment_data_start(data)
            if segment_data_start is None:
                continue

            seek_targets = _parse_seek_targets(data, segment_data_start)
            cluster_pos = seek_targets.get(_WEBM_CLUSTER_ID, -1)
            if cluster_pos < 0:
                cluster_pos = data.find(_WEBM_CLUSTER_BYTES, segment_data_start)

            cues_pos = seek_targets.get(_WEBM_CUES_ID, -1)
            if cues_pos < 0:
                cues_pos = data.find(_WEBM_CUES_BYTES, segment_data_start)

            init_range = f"0-{cluster_pos - 1}" if cluster_pos > 0 else None
            index_range = None
            if cues_pos > 0:
                cues_end = None
                if cluster_pos > cues_pos:
                    cues_end = cluster_pos
                elif cues_pos < len(data):
                    cues_end = _read_ebml_element_end(data, cues_pos)
                else:
                    cues_end = _fetch_webm_element_end(url, cues_pos)
                if cues_end and cues_end > cues_pos:
                    index_range = f"{cues_pos}-{cues_end - 1}"

            if init_range and index_range:
                return init_range, index_range
        except Exception:
            continue
    return None, None


def _proxy(u: str) -> str:
    return '/api/video/proxy?' + urlencode({
        'domain': 'youtube.com',
        'url': u,
    })

def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default


def _codec_family(codec: str | None) -> str | None:
    value = (codec or '').lower()
    if not value or value == 'none':
        return None
    if value.startswith('av01'):
        return 'av1'
    if value.startswith('avc1') or value.startswith('avc3') or value.startswith('h264'):
        return 'avc'
    if value.startswith('vp09') or value.startswith('vp9'):
        return 'vp9'
    if value.startswith('mp4a'):
        return 'aac'
    if value.startswith('opus'):
        return 'opus'
    return value.split('.', 1)[0]


def _codec_sort_value(rep: dict) -> int:
    codec = rep.get('codecFamily')
    if codec == 'av1':
        return 3
    if codec == 'vp9':
        return 2
    if codec == 'avc':
        return 1
    if codec == 'aac':
        return 2
    if codec == 'opus':
        return 1
    return 0


def _group_sort_key(reps: list[dict]) -> tuple[int, int, int]:
    first = reps[0] if reps else {}
    max_height = max((rep.get('height') or 0) for rep in reps) if reps else 0
    max_bandwidth = max((rep.get('bandwidth') or 0) for rep in reps) if reps else 0
    return max_height, _codec_sort_value(first), max_bandwidth


def _group_representations(reps: list[dict], kind: str) -> list[list[dict]]:
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    for rep in reps:
        group_key = (
            kind,
            str(rep.get('mime') or ''),
            str(rep.get('codecFamily') or ''),
        )
        grouped.setdefault(group_key, []).append(rep)

    for values in grouped.values():
        values.sort(
            key=lambda rep: (
                rep.get('height') or 0,
                rep.get('bandwidth') or 0,
            ),
            reverse=True,
        )

    return sorted(grouped.values(), key=_group_sort_key, reverse=True)


def _build_js_runtimes() -> dict:
    runtimes = {}

    node_path = shutil.which('node')
    if node_path:
        runtimes['node'] = {'path': node_path}

    bun_path = shutil.which('bun')
    if bun_path:
        runtimes['bun'] = {'path': bun_path}

    return runtimes


def _build_ytdlp_opts(url: str) -> dict:
    opts = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
        'ignoreerrors': False,
        'extract_flat': False,
        'socket_timeout': 30,
        'retries': 5,
        'extractor_retries': 3,
        'fragment_retries': 5,
        'file_access_retries': 3,
        'extractor_args': {
            'youtube': {
                'player_client': [YOUTUBE_PLAYER_CLIENT],
            }
        },
    }
    js_runtimes = _build_js_runtimes()
    if js_runtimes:
        opts['js_runtimes'] = js_runtimes

    cookie_file = resolve_cookie_file_path(url)
    if cookie_file:
        opts['cookiefile'] = cookie_file
    else:
        cookies = filter_cookies_to_query_string(url)
        if cookies:
            opts['cookie'] = cookies
    return apply_ytdlp_rate_limit(SITE_SLUG, opts)


def _get_cached_video_info(url: str) -> dict | None:
    now = time.monotonic()
    with _VIDEO_INFO_CACHE_LOCK:
        cached = _VIDEO_INFO_CACHE.get(url)
        if not cached:
            return None

        expires_at, info = cached
        if expires_at <= now:
            _VIDEO_INFO_CACHE.pop(url, None)
            return None

        return info


def _set_cached_video_info(url: str, info: dict) -> None:
    now = time.monotonic()
    with _VIDEO_INFO_CACHE_LOCK:
        expired_keys = [
            key for key, (expires_at, _) in _VIDEO_INFO_CACHE.items()
            if expires_at <= now
        ]
        for key in expired_keys:
            _VIDEO_INFO_CACHE.pop(key, None)

        if len(_VIDEO_INFO_CACHE) >= VIDEO_INFO_CACHE_MAX_SIZE:
            oldest_key = min(
                _VIDEO_INFO_CACHE.items(),
                key=lambda item: item[1][0],
            )[0]
            _VIDEO_INFO_CACHE.pop(oldest_key, None)

        _VIDEO_INFO_CACHE[url] = (now + VIDEO_INFO_CACHE_TTL_SECONDS, info)


def _extract_video_info(url: str) -> dict | None:
    cached_info = _get_cached_video_info(url)
    if cached_info:
        return cached_info

    try:
        opts = _build_ytdlp_opts(url)
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            if info.get('_type') == 'playlist':
                entries = info.get('entries') or []
                if entries:
                    info = entries[0]

            if isinstance(info, dict):
                _set_cached_video_info(url, info)
            return info
    except Exception as exc:
        error_msg = str(exc).lower()
        context = {'url': url, 'original_error': str(exc)}

        if any(token in error_msg for token in ('sign in', 'private video', 'members-only', 'not a bot', 'confirm your age')):
            raise AuthError(f'需要登录或通过风控校验后才能播放: {url}', context=context)
        if any(token in error_msg for token in ('timeout', 'connection', 'network', 'closed file', 'i/o operation')):
            raise NetworkError(f'YouTube playback network request failed: {url}', context=context)

        logger.error('yt-dlp failed to extract info for %s: %s', url, exc)
        raise ParseError(f'无法获取 YouTube 视频播放信息: {url}', context=context)


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
    if is_video and ext not in ('mp4', 'webm'):
        return None
    if is_audio and ext not in ('m4a', 'mp4', 'webm'):
        return None

    init_range = _range_to_str(fmt.get('init_range') or fmt.get('initRange'))
    index_range = _range_to_str(fmt.get('index_range') or fmt.get('indexRange'))
    if (is_video or is_audio) and (init_range is None or index_range is None):
        if ext == 'webm':
            probed_init, probed_index = _probe_webm_ranges(stream_url)
        else:
            probed_init, probed_index = _probe_mp4_ranges(stream_url)
        init_range = init_range or probed_init
        index_range = index_range or probed_index

    if not init_range or not index_range:
        return None

    mime_type = fmt.get('mime_type')
    if not mime_type:
        if is_video:
            mime_type = 'video/webm' if ext == 'webm' else 'video/mp4'
        else:
            mime_type = 'audio/webm' if ext == 'webm' else 'audio/mp4'

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
        'codecFamily': _codec_family(codecs_val),
        'xml_lang': fmt.get('language'),
        'label': fmt.get('format_note'),
    }
    return rep


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
        profiles = [ISOBMFF_ON_DEMAND_PROFILE]
        if any(str(rep.get('mime') or '').endswith('/webm') for rep in kept_by_itag.values()):
            profiles.append(WEBM_ON_DEMAND_PROFILE)
        mpd.set('profiles', ','.join(profiles))
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

        for group in _group_representations(video_reps, 'video'):
            first = group[0]
            video_as = ET.SubElement(
                period,
                'AdaptationSet',
                contentType='video',
                segmentAlignment='true',
                subsegmentAlignment='true',
            )
            if first.get('mime'):
                video_as.set('mimeType', str(first['mime']))
            for rep in group:
                add_rep(video_as, rep, 'video')

        for group in _group_representations(audio_reps, 'audio'):
            first = group[0]
            audio_as = ET.SubElement(
                period,
                'AdaptationSet',
                contentType='audio',
                segmentAlignment='true',
                subsegmentAlignment='true',
            )
            if first.get('mime'):
                audio_as.set('mimeType', str(first['mime']))
            add_rep(audio_as, first, 'audio')

        return ET.tostring(mpd, encoding='unicode')
