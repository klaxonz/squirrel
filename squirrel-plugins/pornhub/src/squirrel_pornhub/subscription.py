from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup

from crawl import (
    register_subscription,
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
    filter_cookies_to_query_string,
    request,
)


@register_subscription("pornhub", ["pornhub.com"])
class PornhubSubscription:
    def __init__(self, url: str) -> None:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()

        # 归一化子域：将 *.pornhub.com 统一为 www.pornhub.com，避免相同订阅因为子域不同被当成多条
        if netloc.endswith(".pornhub.com") and netloc != "www.pornhub.com":
            parsed = parsed._replace(netloc="www.pornhub.com")
            url = urlunparse(parsed)

        self.url = url

    def get_subscribe_info(self) -> SubscriptionMeta:
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }
        response = request('GET', self.url, headers=headers, timeout=15)
        response.raise_for_status()

        bs4 = BeautifulSoup(response.text, 'html.parser')
        channel_els = bs4.select('#channelsProfile .title > h1')

        if len(channel_els) > 0:
            name = channel_els[0].text.strip()
            subscribe_url = bs4.select('button[data-subscribe-url]')[0].get('data-subscribe-url')
            channel_id_match = re.search(r"id=([^&]+)", subscribe_url)
            channel_id = channel_id_match.group(1) if channel_id_match else None
        else:
            channel_id = None
            name_el = bs4.select('.nameSubscribe .name h1')
            if len(name_el) == 0:
                raise Exception(f'Can not find channel name in {self.url}')

            name = name_el[0].text.strip()
            add_friend_btn = bs4.select('.addFriendButton button[data-friend-url]')
            if len(add_friend_btn) > 0:
                channel_id = add_friend_btn[0].get('data-id')
            if channel_id is None:
                subscribe_btn = bs4.select('.subscribeButton button[data-subscribe-url]')
                if len(subscribe_btn) > 0:
                    match = re.search(r"id=([^&]+)", subscribe_btn[0].get('data-subscribe-url'))
                    if match:
                        channel_id = match.group(1)
                    else:
                        channel_id = subscribe_btn[0].get('data-id')
                        if channel_id is None:
                            raise Exception(f'Can not find channel id in {self.url}')

        url = re.search(r"^(.*?)(\?.*)?$", self.url).group(1)
        avatar = None
        avatar_els = bs4.select('#getAvatar')
        if len(avatar_els) > 0:
            avatar = avatar_els[0].get('src')
        if avatar is None:
            avatar_els = bs4.select('.topProfileHeader .thumbImage img')
            if len(avatar_els) > 0:
                avatar = avatar_els[0].get('src')

        return SubscriptionMeta(channel_id, name, avatar, url)

    def sync_videos(self, context: SubscriptionSyncContext) -> SubscriptionSyncResult:
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }

        if 'pornhub.com/model' in self.url or 'pornhub.com/pornstar' in self.url:
            self.url = self.url + '/videos'

        response = request('GET', self.url, headers=headers, timeout=15)
        if response.status_code == 404:
            self.url = self.url.replace('/videos', '')
            response = request('GET', self.url, headers=headers, timeout=15)
        response.raise_for_status()

        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        video_list: List[str] = []
        latest_video_url: Optional[str] = None
        limit = None if context.mode == 'full' else (context.limit or 30)

        bs4 = BeautifulSoup(response.text, 'html.parser')
        stop_reason, latest_video_url = self._extract_video_urls(bs4, base_url, video_list, context, latest_video_url, limit)
        if stop_reason:
            return self._build_sync_result(video_list, latest_video_url, context, stop_reason)

        page_next_list = bs4.select('.page_next')
        page = int(bs4.select('.page_next')[0].find_previous().text) if len(page_next_list) > 0 else 1
        current_page = 1

        while current_page < page and context.mode == 'full':
            current_page += 1
            response = request('GET', self.url + f'?page={current_page}', headers=headers, timeout=15)
            response.raise_for_status()
            bs4 = BeautifulSoup(response.text, 'html.parser')
            stop_reason, latest_video_url = self._extract_video_urls(bs4, base_url, video_list, context, latest_video_url, limit)
            if stop_reason:
                return self._build_sync_result(video_list, latest_video_url, context, stop_reason)

            new_page = int(bs4.select('.page_next')[0].find_previous().text) if len(page_next_list) > 0 else 1
            if new_page > page:
                page = new_page

        return self._build_sync_result(video_list, latest_video_url, context, 'source_exhausted')

    def _extract_video_urls(
        self,
        bs4: BeautifulSoup,
        base_url: str,
        video_list: list,
        context: SubscriptionSyncContext,
        latest_video_url: Optional[str],
        limit: Optional[int],
    ) -> tuple[Optional[str], Optional[str]]:
        video_els = []
        video_els.extend(bs4.select('#channelsProfile .videos a.videoPreviewBg'))
        video_els.extend(bs4.select('#profileContent .videos:not(#privateVideosSection) a.videoPreviewBg'))
        video_els.extend(bs4.select('#pornstarsVideoSection .videoPreviewBg'))
        for el in video_els:
            video_url = f'{base_url}{el["href"]}'
            if latest_video_url is None:
                latest_video_url = video_url
            if context.mode != 'full' and video_url == context.last_seen_video_url:
                return 'cursor_hit', latest_video_url
            video_list.append(video_url)
            if limit is not None and len(video_list) >= limit:
                return 'limit_reached', latest_video_url
        return None, latest_video_url

    def _build_sync_result(
        self,
        video_list: List[str],
        latest_video_url: Optional[str],
        context: SubscriptionSyncContext,
        stop_reason: str,
    ) -> SubscriptionSyncResult:
        return SubscriptionSyncResult(
            video_urls=video_list,
            latest_video_url=latest_video_url,
            cursor_payload={'latest_video_url': latest_video_url} if latest_video_url else context.cursor_payload,
            stop_reason=stop_reason,
            total_available=len(video_list),
        )


