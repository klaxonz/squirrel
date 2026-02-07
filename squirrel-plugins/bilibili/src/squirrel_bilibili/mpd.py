from __future__ import annotations

from urllib.parse import quote
from xml.etree import ElementTree as ET

from crawl import register_mpd
from .handler import get_dash_data, _base_url


@register_mpd
class BilibiliMpdBuilder:
    """Bilibili MPD构建器，实现MpdBuilder Protocol"""
    
    domain = 'bilibili.com'

    def build_mpd(self, video) -> str:
        dash_data = get_dash_data(video.url)
        duration = dash_data.get('duration')
        min_buffer_time = dash_data.get('minBufferTime')

        mpd = ET.Element("MPD", xmlns="urn:mpeg:dash:schema:mpd:2011")
        if min_buffer_time:
            mpd.set("minBufferTime", f"PT{min_buffer_time}S")
        if duration:
            mpd.set("mediaPresentationDuration", f"PT{duration}S")
        mpd.set("type", "static")
        mpd.set("profiles", "urn:mpeg:dash:profile:isoff-on-demand:2011")

        period = ET.SubElement(mpd, "Period")

        if 'video' in dash_data:
            video_streams = [
                v for v in dash_data['video']
                if 'codecs' in v and any(x in v['codecs'] for x in ('avc', 'avc1', 'h264'))
            ] or dash_data['video']
            
            # 按照bandwidth排序（高到低），确保与handler中qualities的排序一致
            # 这样qualities中的index就能正确对应MPD中Representation的顺序
            video_streams = sorted(video_streams, key=lambda x: (x.get('height', 0), x.get('bandwidth', 0)), reverse=True)

            video_adaptation_set = ET.SubElement(period, "AdaptationSet", contentType="video", mimeType="video/mp4")
            for stream in video_streams:
                representation = ET.SubElement(video_adaptation_set, "Representation")
                representation.set("id", str(stream.get('id')))
                if 'codecs' in stream:
                    representation.set("codecs", stream['codecs'])
                if 'width' in stream:
                    representation.set("width", str(stream['width']))
                if 'height' in stream:
                    representation.set("height", str(stream['height']))
                if 'frameRate' in stream:
                    representation.set("frameRate", str(stream['frameRate']))
                if 'bandwidth' in stream:
                    representation.set("bandwidth", str(stream['bandwidth']))

                base = _base_url(stream)
                if not base:
                    continue
                base_url = ET.SubElement(representation, "BaseURL")
                proxied = f"/api/video/proxy?domain=bilibili.com&url=" + quote(base, safe='')
                base_url.text = proxied

                segment_base = stream.get('SegmentBase')
                if isinstance(segment_base, dict):
                    seg = ET.SubElement(representation, "SegmentBase")
                    index_range = segment_base.get('indexRange')
                    if index_range:
                        seg.set('indexRange', index_range)
                    init_range = segment_base.get('Initialization')
                    if init_range:
                        init_el = ET.SubElement(seg, 'Initialization')
                        init_el.set('range', init_range)

        if 'audio' in dash_data:
            audio_adaptation_set = ET.SubElement(period, "AdaptationSet", contentType="audio", mimeType="audio/mp4")
            for audio_stream in dash_data['audio']:
                representation = ET.SubElement(audio_adaptation_set, "Representation")
                representation.set("id", str(audio_stream.get('id')))
                if 'codecs' in audio_stream:
                    representation.set("codecs", audio_stream['codecs'])
                if 'bandwidth' in audio_stream:
                    representation.set("bandwidth", str(audio_stream['bandwidth']))

                base = _base_url(audio_stream)
                if not base:
                    continue
                base_url = ET.SubElement(representation, "BaseURL")
                proxied = f"/api/video/proxy?domain=bilibili.com&url=" + quote(base, safe='')
                base_url.text = proxied

                segment_base = audio_stream.get('SegmentBase')
                if isinstance(segment_base, dict):
                    seg = ET.SubElement(representation, "SegmentBase")
                    index_range = segment_base.get('indexRange')
                    if index_range:
                        seg.set('indexRange', index_range)
                    init_range = segment_base.get('Initialization')
                    if init_range:
                        init_el = ET.SubElement(seg, 'Initialization')
                        init_el.set('range', init_range)

        return ET.tostring(mpd, encoding='unicode')


