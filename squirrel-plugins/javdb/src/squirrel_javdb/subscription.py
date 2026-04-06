from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

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

        avatar = self._extract_avatar(bs4)
        channel_id = self.url.split('/')[-1]

        return SubscriptionMeta(channel_id, name, avatar, self.url)

    def _extract_avatar(self, bs4: BeautifulSoup) -> Optional[str]:
        avatar_els = bs4.select('.avatar')
        if not avatar_els:
            return None

        avatar_el = avatar_els[0]
        style = avatar_el.get('style', '')
        avatar_match = re.search(r'url\((.*?)\)', style)
        if avatar_match:
            return avatar_match.group(1)

        image_els = avatar_el.select('img')
        if image_els:
            return image_els[0].get('src')

        return None

    def sync_videos(self, context: SubscriptionSyncContext) -> SubscriptionSyncResult:
        page = self._resolve_page(context)
        response = fetch_javdb_html(self._build_page_url(page))
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

        if context.mode == 'full':
            next_page = self._resolve_next_page(bs4)
            if next_page is not None:
                return build_subscription_sync_result(
                    video_urls=video_list,
                    latest_video_url=latest_video_url,
                    context=context,
                    stop_reason='batch_exhausted',
                    cursor_payload={'page': next_page},
                    has_more=True,
                )

        return build_subscription_sync_result(
            video_urls=video_list,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason='source_exhausted',
        )

    def _resolve_page(self, context: SubscriptionSyncContext) -> int:
        page = context.cursor_payload.get('page', 1)
        try:
            return max(1, int(page))
        except (TypeError, ValueError):
            return 1

    def _build_page_url(self, page: int) -> str:
        if page <= 1:
            return self.url

        parsed = urlparse(self.url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query['page'] = str(page)
        query['sort_type'] = '0'
        return urlunparse(parsed._replace(query=urlencode(query)))

    def _resolve_next_page(self, bs4: BeautifulSoup) -> Optional[int]:
        page_next_list = bs4.select('a.pagination-link[rel="next"]')
        if not page_next_list:
            return None

        next_page_text = page_next_list[0].text.strip()
        try:
            return int(next_page_text)
        except ValueError:
            return None

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


