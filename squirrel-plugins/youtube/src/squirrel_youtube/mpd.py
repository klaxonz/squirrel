from __future__ import annotations

from xml.etree import ElementTree as ET
from urllib.parse import quote
import re
import struct

import requests
from pytubefix import YouTube

from crawl import BaseMpdBuilder, register_mpd

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36'
SESSION = requests.Session()


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
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': '*/*',
        'Connection': 'keep-alive',
    }
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


def _collect_adaptive_meta(yt: YouTube):
    meta = {}
    pr = getattr(yt, 'player_response', None)
    sd = None
    if isinstance(pr, dict):
        sd = pr.get('streamingData')
    if sd is None:
        sd = getattr(yt, 'streaming_data', None)
    adaptive_formats = []
    if isinstance(sd, dict):
        adaptive_formats = sd.get('adaptiveFormats') or []
    for f in adaptive_formats:
        try:
            itag = int(f.get('itag'))
        except Exception:
            continue
        mime = ''
        codecs = ''
        mt = f.get('mimeType', '')
        if mt:
            parts = mt.split(';')
            mime = parts[0].strip()
            m = re.search(r'codecs="([^"]+)"', mt)
            if m:
                codecs = m.group(1)
        meta[itag] = {
            'initRange': f.get('initRange'),
            'indexRange': f.get('indexRange'),
            'averageBitrate': f.get('averageBitrate') or f.get('bitrate'),
            'audioSampleRate': f.get('audioSampleRate'),
            'audioChannels': f.get('audioChannels'),
            'codecs': codecs,
            'mimeType': mime or mt,
            'isDrc': f.get('isDrc', False),
            'lastModified': _safe_int(f.get('lastModified', 0), 0),
            'approxDurationMs': _safe_int(f.get('approxDurationMs', 0), 0),
        }
    return meta


@register_mpd
class YouTubeMpdBuilder(BaseMpdBuilder):
    domain = 'youtube.com'

    def build_mpd(self, video) -> str:
        yt = YouTube(video.url, use_po_token=True, client='WEB')
        by_itag_meta = _collect_adaptive_meta(yt)
        all_streams = yt.streams.filter(adaptive=True)
        kept_by_itag = {}
        for s in all_streams:
            if getattr(s, 'is_progressive', False):
                continue
            if getattr(s, 'is_otf', False):
                continue
            itag = _safe_int(getattr(s, 'itag', -1), -1)
            if itag < 0:
                continue

            def rank(stream):
                meta = by_itag_meta.get(itag, {})
                is_drc = meta.get('isDrc') if meta else getattr(stream, 'is_drc', False)
                last_mod = meta.get('lastModified') if meta else _safe_int(getattr(stream, 'last_Modified', 0), 0)
                return 0 if not is_drc else 1, -int(last_mod)

            if itag not in kept_by_itag:
                kept_by_itag[itag] = s
            else:
                if rank(s) < rank(kept_by_itag[itag]):
                    kept_by_itag[itag] = s

        video_reps = []
        audio_reps = []
        max_dur_ms = 0

        for itag, s in kept_by_itag.items():
            meta = by_itag_meta.get(itag, {})
            mime_type = getattr(s, 'mime_type', None) or meta.get('mimeType') or ''
            codecs_val = getattr(s, 'codecs', None)
            if isinstance(codecs_val, (list, tuple)):
                codecs_val = ",".join([str(x) for x in codecs_val if x])
            if not codecs_val:
                codecs_val = meta.get('codecs') or ''
            bandwidth = meta.get('averageBitrate') or getattr(s, 'bitrate', None)
            if not bandwidth and getattr(s, 'abr', None):
                abr_str = str(getattr(s, 'abr')).lower().replace('kbps', '').strip()
                if abr_str.isdigit():
                    bandwidth = int(abr_str) * 1000
            width = getattr(s, 'width', None)
            height = getattr(s, 'height', None)
            if not height:
                res = getattr(s, 'resolution', None)
                if isinstance(res, str) and res.endswith('p'):
                    try:
                        height = int(res[:-1])
                    except Exception:
                        height = None
            fps = getattr(s, 'fps', None)
            audio_sr = meta.get('audioSampleRate')
            audio_ch = meta.get('audioChannels')
            ir = meta.get('initRange')
            xr = meta.get('indexRange')
            init_range = None
            index_range = None
            if isinstance(ir, dict) and 'start' in ir and 'end' in ir:
                init_range = f"{ir['start']}-{ir['end']}"
            if isinstance(xr, dict) and 'start' in xr and 'end' in xr:
                index_range = f"{xr['start']}-{xr['end']}"
            max_dur_ms = max(max_dur_ms, _safe_int(getattr(s, 'durationMs', 0), 0), _safe_int(meta.get('approxDurationMs', 0), 0))

            rep = {
                'id': str(itag),
                'bandwidth': int(bandwidth) if bandwidth else None,
                'mime': mime_type,
                'codecs': codecs_val,
                'url': getattr(s, 'url', None),
                'width': width,
                'height': height,
                'fps': int(fps) if fps else None,
                'audioSamplingRate': str(audio_sr) if audio_sr else None,
                'audioChannels': int(audio_ch) if audio_ch else None,
                'initRange': init_range,
                'indexRange': index_range,
                'kind': getattr(s, 'type', None) or (mime_type.split('/')[0] if mime_type else None),
                'xml_lang': getattr(s, 'audio_track_language_id', None),
                'is_default_audio': getattr(s, 'is_default_audio_track', False),
                'label': getattr(s, 'audio_track_name_regionalized', None),
            }

            if rep['kind'] == 'video':
                video_reps.append(rep)
            elif rep['kind'] == 'audio':
                audio_reps.append(rep)

        mpd = ET.Element('MPD', xmlns='urn:mpeg:dash:schema:mpd:2011')
        mpd.set('type', 'static')
        mpd.set('profiles', 'urn:mpeg:dash:profile:isoff-on-demand:2011')
        duration_seconds = getattr(yt, 'length', None)
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


