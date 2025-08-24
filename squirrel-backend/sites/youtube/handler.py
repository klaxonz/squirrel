import json
import subprocess
from abc import ABC
from typing import Tuple, Optional
from xml.etree import ElementTree as ET
from core.exceptions.video_exceptions import VideoUrlExtractionError
from models.video import Video
from schemas.video.dto.video_dto import VideoUrlDto, QualityOptionDto
from sites.handler import VideoUrlHandler
from sites.handler_registry import register_handler
from sites.mpd import MpdFactory


@register_handler
class YouTubeHandler(VideoUrlHandler, ABC):

    domain = 'youtube.com'

    def get_video_url(self, video: Video) -> VideoUrlDto:
        try:
            mpd_xml = MpdFactory.build_mpd_for_video(video)

            ns = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}
            root = ET.fromstring(mpd_xml)
            reps: list[QualityOptionDto] = []
            for period in root.findall('mpd:Period', ns):
                for aset in period.findall('mpd:AdaptationSet', ns):
                    ctype = aset.get('contentType') or aset.get('mimeType')
                    if (ctype or '').lower().startswith('video'):
                        for rep in aset.findall('mpd:Representation', ns):
                            rid = rep.get('id') or rep.get('ID') or rep.get('Id')
                            if not rid:
                                continue
                            # attributes
                            height = None
                            try:
                                h_str = rep.get('height')
                                if h_str:
                                    height = int(h_str)
                            except Exception:
                                height = None
                            bw = None
                            try:
                                bw_str = rep.get('bandwidth')
                                if bw_str:
                                    bw = int(bw_str)
                            except Exception:
                                bw = None
                            fps = rep.get('frameRate')
                            fps_suffix = ''
                            try:
                                if fps and (int(str(fps).split('/')[0]) >= 50):
                                    fps_suffix = '60'
                            except Exception:
                                fps_suffix = ''
                            codecs = rep.get('codecs') or ''
                            codec_short = ''
                            cs = codecs.lower()
                            if 'av01' in cs:
                                codec_short = 'AV1'
                            elif 'vp9' in cs:
                                codec_short = 'VP9'
                            elif 'avc' in cs or 'h264' in cs:
                                codec_short = 'AVC'

                            label_parts = []
                            if height:
                                label_parts.append(f"{height}p{fps_suffix}")
                            if codec_short:
                                label_parts.append(codec_short)
                            label = ' '.join(label_parts) if label_parts else f"itag {rid}"
                            label = (label + f" (itag {rid})") if 'itag' not in label else label

                            reps.append(QualityOptionDto(
                                value=str(rid),
                                label=label,
                                height=height,
                                bandwidth=bw,
                                id=str(rid)
                            ))

            reps.sort(key=lambda q: ((q.height or 0), (q.bandwidth or 0)), reverse=True)
            if not any(q.value == 'auto' for q in reps):
                reps.insert(0, QualityOptionDto(value='auto', label='自动'))

            return VideoUrlDto(
                mpd_url=f"/api/video/mpd?video_id={video.id}",
                qualities=reps or None,
            )

        except Exception as e:
            raise VideoUrlExtractionError(f"Failed to extract YouTube video URL: {str(e)}")


def po_token_verifier(_: None = None) -> Optional[Tuple[str, str]]:
    token_object = generate_youtube_token()
    return token_object["visitorData"], token_object["poToken"]


def generate_youtube_token() -> dict:
    try:
        result = subprocess.run(
            ["node", "scripts/youtube-token-generator.js"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        raise Exception(f"Failed to generate YouTube token: ", e)
