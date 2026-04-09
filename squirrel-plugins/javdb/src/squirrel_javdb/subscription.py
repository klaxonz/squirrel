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

HEAD_SAMPLE_LIMIT = 10


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
        count_offset = self._resolve_count_offset(context)
        previous_page_urls = self._resolve_previous_page_urls(context)
        response = fetch_javdb_html(self._build_page_url(page))
        html = response.text

        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        video_list: List[str] = []
        seen_urls: set[str] = set()
        head_sample_urls: list[str] = []
        page_video_urls: list[str] = []
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
            head_sample_urls,
            page_video_urls,
        )
        page_unique_count = self._count_page_unique_videos(page_video_urls, previous_page_urls)
        if stop_reason:
            return build_subscription_sync_result(
                video_urls=video_list,
                latest_video_url=latest_video_url,
                context=context,
                stop_reason=stop_reason,
                head_sample_urls=head_sample_urls if context.mode != 'full' else None,
                anchor_found=True if stop_reason == 'cursor_hit' and context.mode != 'full' else None,
            )

        if context.mode == 'full':
            next_page = self._resolve_next_page(bs4)
            if next_page is not None:
                return build_subscription_sync_result(
                    video_urls=video_list,
                    latest_video_url=latest_video_url,
                    context=context,
                    stop_reason='batch_exhausted',
                    cursor_payload={
                        'page': next_page,
                        'count_offset': count_offset + page_unique_count,
                        'previous_page_urls': page_video_urls,
                    },
                    has_more=True,
                )

        return build_subscription_sync_result(
            video_urls=video_list,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason='source_exhausted',
            total_available=count_offset + page_unique_count if context.mode == 'full' else None,
            head_sample_urls=head_sample_urls if context.mode != 'full' else None,
            anchor_found=False if context.mode != 'full' and context.last_seen_video_url else None,
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

    @staticmethod
    def _resolve_count_offset(context: SubscriptionSyncContext) -> int:
        raw_value = context.cursor_payload.get('count_offset', 0)
        try:
            return max(0, int(raw_value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _resolve_previous_page_urls(context: SubscriptionSyncContext) -> list[str]:
        previous_page_urls = context.cursor_payload.get('previous_page_urls')
        if not isinstance(previous_page_urls, list):
            return []
        return [url for url in previous_page_urls if isinstance(url, str) and url]

    @staticmethod
    def _count_page_unique_videos(page_video_urls: list[str], previous_page_urls: list[str]) -> int:
        previous_page_url_set = set(previous_page_urls)
        return sum(1 for url in page_video_urls if url not in previous_page_url_set)

    def _extract_video_urls(
        self,
        bs4: BeautifulSoup,
        base_url: str,
        video_list: list,
        seen_urls: set[str],
        context: SubscriptionSyncContext,
        latest_video_url: Optional[str],
        limit: Optional[int],
        head_sample_urls: list[str],
        page_video_urls: list[str],
    ) -> tuple[Optional[str], Optional[str]]:
        video_els = bs4.select('.movie-list .item a.box')
        for el in video_els:
            video_url = f'{base_url}{el["href"]}'
            if video_url not in page_video_urls:
                page_video_urls.append(video_url)
            if video_url not in head_sample_urls and len(head_sample_urls) < HEAD_SAMPLE_LIMIT:
                head_sample_urls.append(video_url)
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


