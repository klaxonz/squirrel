from __future__ import annotations

from crawl import Actor, Video, register_meta


@register_meta
class YoutubeVideo(Video):
    domain = 'youtube.com'

    def __init__(self, url, base_info):
        super().__init__(url, base_info)

    @property
    def actors(self):
        if len(self._actors) == 0:
            actor = Actor(self._resolve_channel_url())
            actor.name = self._base_info.get('uploader') or self._base_info.get('channel')
            actor.avatar = self._resolve_channel_avatar()
            self._actors.append(actor)
        return self._actors

    def _resolve_channel_url(self) -> str:
        channel_url = (
            self._base_info.get('channel_url')
            or self._base_info.get('uploader_url')
        )
        if channel_url:
            return channel_url

        channel_id = self._base_info.get('channel_id') or self._base_info.get('uploader_id')
        if channel_id:
            return f"https://www.youtube.com/channel/{channel_id}"
        return self.url

    def _resolve_channel_avatar(self) -> str | None:
        if self._base_info.get('channel_thumbnail'):
            return self._base_info['channel_thumbnail']
        thumbnails = self._base_info.get('thumbnails')
        if isinstance(thumbnails, list):
            ordered = sorted(
                (t for t in thumbnails if isinstance(t, dict) and t.get('url')),
                key=lambda item: (item.get('width') or 0) * (item.get('height') or 0),
                reverse=True,
            )
            if ordered:
                return ordered[0].get('url')
        return self._base_info.get('thumbnail')


