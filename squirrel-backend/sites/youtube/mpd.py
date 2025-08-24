from xml.etree import ElementTree as ET
from urllib.parse import quote
import re
import struct
import requests
from pytubefix import YouTube
from sites.mpd_origin import BaseMpdBuilder
from sites.mpd_registry import register_mpd
from models.video import Video

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36'


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
            resp = requests.get(url, headers={**headers, 'Range': f'bytes=0-{end}'}, timeout=15)
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
    return f"/api/video/proxy?domain=youtube.com&url=" + quote(u, safe='')


def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default


def _collect_adaptive_meta(yt: YouTube):
    """Collect itag -> meta from player_response.streamingData.adaptiveFormats.
    Returns dict[itago] = {initRange, indexRange, averageBitrate, audioSampleRate, audioChannels, codecs, mimeType, isDrc, lastModified}
    """
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

    def build_mpd(self, video: Video) -> str:
        yt = YouTube(video.url)

        # Collect meta for ranges/bitrate/audio params
        by_itag_meta = _collect_adaptive_meta(yt)

        all_streams = yt.streams.filter(adaptive=True)

        kept_by_itag = {}
        for s in all_streams:
            # Skip progressive and OTF
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

        # Separate video/audio reps
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

            # bandwidth
            bandwidth = meta.get('averageBitrate') or getattr(s, 'bitrate', None)
            if not bandwidth and getattr(s, 'abr', None):
                abr_str = str(getattr(s, 'abr')).lower().replace('kbps', '').strip()
                if abr_str.isdigit():
                    bandwidth = int(abr_str) * 1000

            # dimensions and fps
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

            # audio meta
            audio_sr = meta.get('audioSampleRate')
            audio_ch = meta.get('audioChannels')

            # ranges
            ir = meta.get('initRange')
            xr = meta.get('indexRange')
            init_range = None
            index_range = None
            if isinstance(ir, dict) and 'start' in ir and 'end' in ir:
                init_range = f"{ir['start']}-{ir['end']}"
            if isinstance(xr, dict) and 'start' in xr and 'end' in xr:
                index_range = f"{xr['start']}-{xr['end']}"

            # duration
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

        # Build MPD
        mpd = ET.Element('MPD', xmlns='urn:mpeg:dash:schema:mpd:2011')
        mpd.set('type', 'static')
        mpd.set('profiles', 'urn:mpeg:dash:profile:isoff-on-demand:2011')
        duration_seconds = getattr(yt, 'length', None)
        if not duration_seconds and max_dur_ms:
            duration_seconds = max_dur_ms / 1000.0
        if duration_seconds:
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
            else:
                # Fallback probe if no ranges provided
                if r.get('url') and (r['mime'].startswith('video/mp4') or r['mime'].startswith('audio/mp4')):
                    init_probe, index_probe = _probe_ranges(r['url'])
                    if init_probe or index_probe:
                        seg = ET.SubElement(rep_el, 'SegmentBase')
                        if index_probe:
                            seg.set('indexRange', index_probe)
                        init = ET.SubElement(seg, 'Initialization')
                        if init_probe:
                            init.set('range', init_probe)

        # 仅保留带完整 range 的 MP4（稳定性更好）
        def has_ranges(r):
            return bool(r.get('initRange')) and bool(r.get('indexRange'))

        video_mp4 = [r for r in video_reps if isinstance(r.get('mime'), str) and r['mime'].startswith('video/mp4')]
        audio_mp4 = [r for r in audio_reps if isinstance(r.get('mime'), str) and r['mime'].startswith('audio/mp4')]

        # 尝试为缺少 range 的 MP4 探测一次（避免前端反复探测）
        for r in video_mp4 + audio_mp4:
            if not has_ranges(r) and r.get('url'):
                probed_init, probed_index = _probe_ranges(r['url'])
                if probed_init:
                    r['initRange'] = probed_init
                if probed_index:
                    r['indexRange'] = probed_index

        # 过滤掉仍然缺少 range 的表示，避免播放器小块探测请求风暴
        video_final = [r for r in video_mp4 if has_ranges(r)]
        audio_final = [r for r in audio_mp4 if has_ranges(r)]

        # 仅选择单一视频编解码族，避免跨编解码自动切换导致 SourceBuffer 码流不匹配
        def codec_family(r):
            cs = (r.get('codecs') or '').lower()
            if 'av01' in cs:
                return 'av1'
            if 'vp9' in cs:
                return 'vp9'
            if 'avc' in cs or 'h264' in cs:
                return 'avc'
            return 'unknown'

        preferred_order = ['avc', 'vp9', 'av1', 'unknown']
        family_groups = {}
        for v in video_final:
            fam = codec_family(v)
            family_groups.setdefault(fam, []).append(v)
        selected_family = None
        for fam in preferred_order:
            if fam in family_groups and family_groups[fam]:
                selected_family = fam
                break
        if selected_family:
            video_final = family_groups[selected_family]

        if video_final:
            # 保留所选编解码族下的所有 MP4 视频 itag，前端可按 itag 精确切换
            video_sorted = sorted(video_final, key=lambda r: (r.get('height') or 0, r.get('bandwidth') or 0), reverse=True)
            video_as = ET.SubElement(period, 'AdaptationSet', contentType='video', segmentAlignment='true')
            for v in video_sorted:
                add_rep(video_as, v, 'video')
        if audio_final:
            # 默认音轨优先；若没有默认标记，只保留码率最高的一个
            audio_sorted = sorted(audio_final, key=lambda r: (0 if r.get('is_default_audio') else 1, -(r.get('bandwidth') or 0)))
            # 至少保留一个
            keep = []
            default_tracks = [a for a in audio_sorted if a.get('is_default_audio')]
            if default_tracks:
                keep.append(default_tracks[0])
            else:
                keep.append(audio_sorted[0])
            audio_as = ET.SubElement(period, 'AdaptationSet', contentType='audio', segmentAlignment='true')
            for a in keep:
                add_rep(audio_as, a, 'audio')

        return ET.tostring(mpd, encoding='unicode')
