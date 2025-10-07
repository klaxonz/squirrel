from __future__ import annotations

from abc import ABC
from xml.etree import ElementTree as ET

from crawl import VideoUrlHandler, register_handler


@register_handler
class YouTubeHandler(VideoUrlHandler, ABC):
    domain = 'youtube.com'

    def get_video_url(self, video) -> dict:
        # Expect backend to call plugin's MPD builder endpoint; here we only return the path and qualities parsed from MPD
        from crawl import BaseMpdBuilder, MpdRegistry
        builder_cls = MpdRegistry.get_mpd_builder_class(self.domain)
        if not builder_cls:
            return {"mpd_url": f"/api/video/mpd?video_id={video.id}", "qualities": None}
        builder: BaseMpdBuilder = builder_cls()
        mpd_xml = builder.build_mpd(video)
        ns = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}
        root = ET.fromstring(mpd_xml)
        reps = []
        for period in root.findall('mpd:Period', ns):
            for aset in period.findall('mpd:AdaptationSet', ns):
                ctype = aset.get('contentType') or aset.get('mimeType')
                if (ctype or '').lower().startswith('video'):
                    for rep in aset.findall('mpd:Representation', ns):
                        rid = rep.get('id') or rep.get('ID') or rep.get('Id')
                        if not rid:
                            continue
                        height = rep.get('height')
                        bandwidth = rep.get('bandwidth')
                        label = f"{height}p (itag {rid})" if height else f"itag {rid}"
                        reps.append({
                            "value": str(rid),
                            "label": label,
                            "height": int(height) if height else None,
                            "bandwidth": int(bandwidth) if bandwidth else None,
                            "id": str(rid)
                        })
        reps.sort(key=lambda q: ((q.get('height') or 0), (q.get('bandwidth') or 0)), reverse=True)
        
        # 排序后分配index，与MPD中Representation的顺序一致
        for idx, q in enumerate(reps):
            q['index'] = idx
        
        if not any(q.get('value') == 'auto' for q in reps):
            reps.insert(0, {"value": "auto", "label": "自动", "index": -1})
        return {
            "mpd_url": f"/api/video/mpd?video_id={video.id}",
            "qualities": reps or None,
        }


