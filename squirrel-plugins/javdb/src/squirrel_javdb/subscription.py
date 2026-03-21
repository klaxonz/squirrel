from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from crawl import (
    register_subscription,
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
    get,
    filter_cookies_to_query_string,
)


@register_subscription("javdb", ["javdb.com"])
class JavdbSubscription:
    def __init__(self, url: str) -> None:
        self.url = url

    def get_subscribe_info(self) -> SubscriptionMeta:
        cookies = filter_cookies_to_query_string(self.url)
        headers = {'Cookie': cookies} if cookies else {}
        response = get(self.url, headers=headers, bypass_mode="html")
        html = response.text
        bs4 = BeautifulSoup(html, 'html.parser')
        username_el = bs4.select('.actor-section-name')
        if len(username_el) == 0:
            raise Exception(f'Can not find channel name in {self.url}')

        name = username_el[0].text.strip()
        if ',' in name:
            name = name.split(',')[0]

        avatar_el = bs4.select('.avatar')[0]
        style = avatar_el['style']
        avatar_match = re.search(r'url\((.*?)\)', style)
        avatar = avatar_match.group(1) if avatar_match else None
        channel_id = self.url.split('/')[-1]

        return SubscriptionMeta(channel_id, name, avatar, self.url)

    def sync_videos(self, context: SubscriptionSyncContext) -> SubscriptionSyncResult:
        cookies = filter_cookies_to_query_string(self.url)
        headers = {'Cookie': cookies} if cookies else {}
        response = get(self.url, headers=headers, bypass_mode="html")
        html = response.text

        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        video_list: List[str] = []
        latest_video_url: Optional[str] = None
        limit = None if context.mode == 'full' else (context.limit or 30)

        bs4 = BeautifulSoup(html, 'html.parser')
        stop_reason, latest_video_url = self._extract_video_urls(bs4, base_url, video_list, context, latest_video_url, limit)
        if stop_reason:
            return self._build_sync_result(video_list, latest_video_url, context, stop_reason)

        page_next_list = bs4.select('a.pagination-link[rel="next"]')
        page = int(bs4.select('a.pagination-link[rel="next"]')[0].text) if len(page_next_list) > 0 else 1
        current_page = 1

        while current_page < page and context.mode == 'full':
            current_page += 1
            page_response = get(self.url + f'?page={current_page}&sort_type=0', headers=headers, bypass_mode="html")
            page_html = page_response.text
            bs4 = BeautifulSoup(page_html, 'html.parser')

            stop_reason, latest_video_url = self._extract_video_urls(bs4, base_url, video_list, context, latest_video_url, limit)
            if stop_reason:
                return self._build_sync_result(video_list, latest_video_url, context, stop_reason)

            page_next_list = bs4.select('a.pagination-link[rel="next"]')
            new_page = int(bs4.select('a.pagination-link[rel="next"]')[0].text) if len(page_next_list) > 0 else 1
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
        video_els = bs4.select('.movie-list .item a.box')
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


