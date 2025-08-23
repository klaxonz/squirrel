from xml.etree import ElementTree as ET
import requests
from sites.mpd_origin import BaseMpdBuilder
from sites.mpd_registry import register_mpd
from models.video import Video
from .handler import fetch_html, extract_playinfo_from_html


@register_mpd
class BilibiliMpdBuilder(BaseMpdBuilder):
    domain = 'bilibili.com'

    def build_mpd(self, video: Video) -> str:
        html = fetch_html(video.url)
        if not html:
            raise RuntimeError("Failed to fetch video page")

        play_info = extract_playinfo_from_html(html)
        if not play_info or 'data' not in play_info or 'dash' not in play_info['data']:
            raise RuntimeError("Failed to extract play info")

        dash_data = play_info['data']['dash']
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

        # Video streams
        if 'video' in dash_data:
            # Prefer H.264/AVC for browser compatibility
            video_streams = [
                v for v in dash_data['video']
                if 'codecs' in v and any(x in v['codecs'] for x in ('avc', 'avc1', 'h264'))
            ] or dash_data['video']

            video_adaptation_set = ET.SubElement(period, "AdaptationSet", contentType="video", mimeType="video/mp4")
            for video_stream in video_streams:
                representation = ET.SubElement(video_adaptation_set, "Representation")
                representation.set("id", str(video_stream.get('id')))
                if 'codecs' in video_stream:
                    representation.set("codecs", video_stream['codecs'])
                if 'width' in video_stream:
                    representation.set("width", str(video_stream['width']))
                if 'height' in video_stream:
                    representation.set("height", str(video_stream['height']))
                if 'frameRate' in video_stream:
                    representation.set("frameRate", str(video_stream['frameRate']))
                if 'bandwidth' in video_stream:
                    representation.set("bandwidth", str(video_stream['bandwidth']))

                base_url = ET.SubElement(representation, "BaseURL")
                proxied_video_url = f"/api/video/proxy?domain=bilibili.com&url=" + \
                    requests.utils.quote(video_stream['baseUrl'], safe='')
                base_url.text = proxied_video_url

                if 'SegmentBase' in video_stream:
                    segment_base = ET.SubElement(representation, "SegmentBase")
                    if 'indexRange' in video_stream['SegmentBase']:
                        segment_base.set("indexRange", video_stream['SegmentBase']['indexRange'])
                    initialization = ET.SubElement(segment_base, "Initialization")
                    if 'Initialization' in video_stream['SegmentBase']:
                        initialization.set("range", video_stream['SegmentBase']['Initialization'])

        # Audio streams
        if 'audio' in dash_data:
            audio_adaptation_set = ET.SubElement(period, "AdaptationSet", contentType="audio", mimeType="audio/mp4")
            for audio_stream in dash_data['audio']:
                representation = ET.SubElement(audio_adaptation_set, "Representation")
                representation.set("id", str(audio_stream.get('id')))
                if 'codecs' in audio_stream:
                    representation.set("codecs", audio_stream['codecs'])
                if 'bandwidth' in audio_stream:
                    representation.set("bandwidth", str(audio_stream['bandwidth']))

                base_url = ET.SubElement(representation, "BaseURL")
                proxied_audio_url = f"/api/video/proxy?domain=bilibili.com&url=" + \
                    requests.utils.quote(audio_stream['baseUrl'], safe='')
                base_url.text = proxied_audio_url

                if 'SegmentBase' in audio_stream:
                    segment_base = ET.SubElement(representation, "SegmentBase")
                    if 'indexRange' in audio_stream['SegmentBase']:
                        segment_base.set("indexRange", audio_stream['SegmentBase']['indexRange'])
                    initialization = ET.SubElement(segment_base, "Initialization")
                    if 'Initialization' in audio_stream['SegmentBase']:
                        initialization.set("range", audio_stream['SegmentBase']['Initialization'])

        return ET.tostring(mpd, encoding='unicode')

