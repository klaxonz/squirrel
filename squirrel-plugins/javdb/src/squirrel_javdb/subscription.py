from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from crawl import (
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
    append_subscription_video_url,
    build_subscription_sync_result,
    resolve_subscription_limit,
)

from .html_client import fetch_javdb_html


class JavdbSubscription:
    def __init__(self, url: str) -> None:
        self.url = url

    def get_subscribe_info(self) -> SubscriptionMeta:
        response = fetch_javdb_html(self.url)
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
        response = fetch_javdb_html(self.url)
        html = response.text

        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        video_list: List[str] = []
        seen_urls: set[str] = set()
        latest_video_url: Optional[str] = None
        limit = resolve_subscription_limit(context)

        bs4 = BeautifulSoup(html, 'html.parser')
        stop_reason, latest_video_url = self._extract_video_urls(
            bs4,
            base_url,
            video_list,
            seen_urls,
            context,
            latest_video_url,
            limit,
        )
        if stop_reason:
            return build_subscription_sync_result(
                video_urls=video_list,
                latest_video_url=latest_video_url,
                context=context,
                stop_reason=stop_reason,
            )

        page_next_list = bs4.select('a.pagination-link[rel="next"]')
        page = int(bs4.select('a.pagination-link[rel="next"]')[0].text) if len(page_next_list) > 0 else 1
        current_page = 1

        while current_page < page and context.mode == 'full':
            current_page += 1
            page_response = fetch_javdb_html(self.url + f'?page={current_page}&sort_type=0')
            page_html = page_response.text
            bs4 = BeautifulSoup(page_html, 'html.parser')

            stop_reason, latest_video_url = self._extract_video_urls(
                bs4,
                base_url,
                video_list,
                seen_urls,
                context,
                latest_video_url,
                limit,
            )
            if stop_reason:
                return build_subscription_sync_result(
                    video_urls=video_list,
                    latest_video_url=latest_video_url,
                    context=context,
                    stop_reason=stop_reason,
                )

            page_next_list = bs4.select('a.pagination-link[rel="next"]')
            new_page = int(bs4.select('a.pagination-link[rel="next"]')[0].text) if len(page_next_list) > 0 else 1
            if new_page > page:
                page = new_page

        return build_subscription_sync_result(
            video_urls=video_list,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason='source_exhausted',
        )

    def _extract_video_urls(
        self,
        bs4: BeautifulSoup,
        base_url: str,
        video_list: list,
        seen_urls: set[str],
        context: SubscriptionSyncContext,
        latest_video_url: Optional[str],
        limit: Optional[int],
    ) -> tuple[Optional[str], Optional[str]]:
        video_els = bs4.select('.movie-list .item a.box')
        for el in video_els:
            video_url = f'{base_url}{el["href"]}'
            latest_video_url, stop_reason = append_subscription_video_url(
                video_url,
                video_urls=video_list,
                seen_urls=seen_urls,
                context=context,
                latest_video_url=latest_video_url,
                limit=limit,
            )
            if stop_reason:
                return stop_reason, latest_video_url
        return None, latest_video_url


