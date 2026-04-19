from __future__ import annotations

from xml.etree import ElementTree as ET

from .handler import _backup_urls, _base_url, _group_video_streams_by_codec, _proxy_stream_url, get_dash_data


def _append_representation_base_urls(representation: ET.Element, stream: dict, *, direct_playback: bool) -> bool:
    urls = []
    primary_url = _base_url(stream)
    if primary_url:
        urls.append(primary_url)
    urls.extend(_backup_urls(stream))

    emitted = set()
    for url in urls:
        proxied_url = _proxy_stream_url(url, direct_playback=direct_playback)
        if not proxied_url or proxied_url in emitted:
            continue
        base_url = ET.SubElement(representation, 'BaseURL')
        base_url.text = proxied_url
        emitted.add(proxied_url)

    return bool(emitted)


class BilibiliMpdBuilder:
    """Bilibili MPD构建器，实现MpdBuilder Protocol"""
    
    domain = 'bilibili.com'

    def build_mpd(self, video) -> str:
        direct_playback = bool(getattr(video, 'direct_playback', False))
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
        video_stream_groups = _group_video_streams_by_codec(dash_data.get('video') or [])

        for _, video_streams in video_stream_groups:
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

                if not _append_representation_base_urls(
                    representation,
                    stream,
                    direct_playback=direct_playback,
                ):
                    continue

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

        audio_streams = dash_data.get('audio') or []
        if audio_streams:
            audio_adaptation_set = ET.SubElement(period, "AdaptationSet", contentType="audio", mimeType="audio/mp4")
            for audio_stream in audio_streams:
                representation = ET.SubElement(audio_adaptation_set, "Representation")
                representation.set("id", str(audio_stream.get('id')))
                if 'codecs' in audio_stream:
                    representation.set("codecs", audio_stream['codecs'])
                if 'bandwidth' in audio_stream:
                    representation.set("bandwidth", str(audio_stream['bandwidth']))

                if not _append_representation_base_urls(
                    representation,
                    audio_stream,
                    direct_playback=direct_playback,
                ):
                    continue

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
