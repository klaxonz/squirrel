from __future__ import annotations

import logging
from typing import List

from bilibili_api import channel_series, favorite_list, parse_link, ResourceType
from bilibili_api.user import User, VideoOrder, ChannelSeriesType
from crawl import register_subscription, SubscriptionMeta

from .api_client import build_credential, throttled_sync

logger = logging.getLogger(__name__)


@register_subscription("bilibili", ["bilibili.com"])
class BilibiliSubscription:
    def __init__(self, url: str) -> None:
        self.url = url
        self.credential = build_credential(url)
        self.target, self.resource_type = self._resolve_target()

    def _resolve_target(self):
        obj, res_type = throttled_sync(lambda: parse_link(self.url, self.credential))
        if obj == -1 or res_type not in (
            ResourceType.USER,
            ResourceType.FAVORITE_LIST,
            ResourceType.CHANNEL_SERIES,
        ):
            raise ValueError("Unsupported bilibili subscription url")

        # Ensure credential is attached for subsequent calls
        obj.credential = self.credential  # type: ignore[attr-defined]
        return obj, res_type

    def get_subscribe_info(self) -> SubscriptionMeta:
        if self.resource_type == ResourceType.FAVORITE_LIST:
            return self._get_favlist_info()
        if self.resource_type == ResourceType.CHANNEL_SERIES:
            return self._get_channel_info()
        return self._get_space_info()

    def _get_space_info(self) -> SubscriptionMeta:
        user_obj: User = self.target  # type: ignore[assignment]
        info = throttled_sync(lambda: user_obj.get_user_info())
        mid = info.get("mid") or user_obj.get_uid()
        channel_name = info.get("name") or info.get("uname")
        avatar_url = info.get("face")
        return SubscriptionMeta(str(mid), channel_name, avatar_url, self.url)

    def _get_favlist_info(self) -> SubscriptionMeta:
        fav: favorite_list.FavoriteList = self.target  # type: ignore[assignment]
        media_id = fav.get_media_id()
        info = throttled_sync(lambda: fav.get_info())
        title = info.get("title") or info.get("name") or "收藏夹"
        cover = info.get("cover") or info.get("cover_url")
        return SubscriptionMeta(f"fav_{media_id}", title, cover, self.url)

    def _get_channel_info(self) -> SubscriptionMeta:
        series: channel_series.ChannelSeries = self.target  # type: ignore[assignment]
        meta = throttled_sync(lambda: series.get_meta())
        prefix = "season" if series.get_type() == ChannelSeriesType.SEASON else "series"
        title = meta.get("title") or meta.get("name") or "合集"
        cover = meta.get("cover") or meta.get("square_cover")
        return SubscriptionMeta(f"{prefix}_{series.get_id()}", title, cover, self.url)

    def get_subscribe_videos(self, extract_all: bool) -> List[str]:
        if self.resource_type == ResourceType.FAVORITE_LIST:
            return self._get_favlist_videos(extract_all)
        if self.resource_type == ResourceType.CHANNEL_SERIES:
            return self._get_channel_videos(extract_all)
        return self._get_space_videos(extract_all)

    def _get_space_videos(self, extract_all: bool) -> List[str]:
        """获取空间（用户）的视频列表"""
        user_obj: User = self.target  # type: ignore[assignment]
        video_list: List[str] = []
        page = 1
        page_size = 50

        while True:
            data = throttled_sync(
                lambda: user_obj.get_videos(
                    pn=page,
                    ps=page_size,
                    order=VideoOrder.PUBDATE,
                )
            )
            vlist = (data.get("list") or {}).get("vlist") or data.get("vlist") or []
            if not isinstance(vlist, list) or not vlist:
                break

            for v in vlist:
                if v.get("is_union_video") == 1:
                    continue
                bvid = v.get("bvid")
                if bvid:
                    video_list.append(f"https://www.bilibili.com/video/{bvid}")

            if not extract_all:
                break

            page_info = data.get("page") or {}
            total = page_info.get("count") or 0
            if len(video_list) >= total or len(vlist) < page_size:
                break

            page += 1

        return video_list

    def _get_favlist_videos(self, extract_all: bool) -> List[str]:
        """获取收藏夹的视频列表"""
        fav: favorite_list.FavoriteList = self.target  # type: ignore[assignment]

        video_list: List[str] = []
        page = 1

        while True:
            data = throttled_sync(
                lambda: fav.get_content_video(
                    page=page,
                    order=favorite_list.FavoriteListContentOrder.MTIME,
                )
            )
            medias = data.get("medias") or data.get("data", {}).get("medias") or []
            if not medias:
                break

            for media in medias:
                bvid = media.get("bvid")
                if bvid:
                    video_list.append(f"https://www.bilibili.com/video/{bvid}")

            has_more = data.get("has_more", False)
            if not extract_all or not has_more:
                break
            page += 1

        logger.info(f"从收藏夹提取了 {len(video_list)} 个视频")
        return video_list

    def _get_channel_videos(self, extract_all: bool) -> List[str]:
        """获取合集的视频列表"""
        series: channel_series.ChannelSeries = self.target  # type: ignore[assignment]

        video_list: List[str] = []
        page = 1
        page_size = 100

        while True:
            data = throttled_sync(lambda: series.get_videos(pn=page, ps=page_size))
            archives = data.get("archives") or []
            if not archives:
                break

            for archive in archives:
                bvid = archive.get("bvid")
                if bvid:
                    video_list.append(f"https://www.bilibili.com/video/{bvid}")

            if not extract_all or len(archives) < page_size:
                break

            page += 1

        logger.info(f"从合集提取了 {len(video_list)} 个视频")
        return video_list
