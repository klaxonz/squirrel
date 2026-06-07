from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup
from crawl import (
    HEAD_SAMPLE_LIMIT,
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
    append_subscription_video_url,
    build_page_url,
    build_subscription_sync_result,
    count_page_unique_videos,
    filter_cookies_to_query_string,
    request,
    resolve_count_offset,
    resolve_page,
    resolve_previous_page_urls,
    resolve_subscription_limit,
)


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

        effective_url = self.url
        if 'pornhub.com/model' in effective_url or 'pornhub.com/pornstar' in effective_url:
            effective_url = effective_url + '/videos'

        page = resolve_page(context)
        count_offset = resolve_count_offset(context)
        previous_page_urls = resolve_previous_page_urls(context)
        response = request('GET', build_page_url(effective_url, page), headers=headers, timeout=15)
        if response.status_code == 404:
            effective_url = effective_url.replace('/videos', '')
            response = request('GET', build_page_url(effective_url, page), headers=headers, timeout=15)
        response.raise_for_status()

        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        video_list: list[str] = []
        seen_urls: set[str] = set()
        head_sample_urls: list[str] = []
        page_video_urls: list[str] = []
        latest_video_url: str | None = None
        limit = resolve_subscription_limit(context)

        bs4 = BeautifulSoup(response.text, 'html.parser')
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
        page_unique_count = count_page_unique_videos(page_video_urls, previous_page_urls)
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

    def _resolve_next_page(self, bs4: BeautifulSoup) -> int | None:
        page_next_list = bs4.select('.page_next')
        if not page_next_list:
            return None

        previous = page_next_list[0].find_previous()
        if previous is None:
            return None

        try:
            return int(previous.text.strip())
        except (AttributeError, ValueError):
            return None

    def _extract_video_urls(
        self,
        bs4: BeautifulSoup,
        base_url: str,
        video_list: list,
        seen_urls: set[str],
        context: SubscriptionSyncContext,
        latest_video_url: str | None,
        limit: int | None,
        head_sample_urls: list[str],
        page_video_urls: list[str],
    ) -> tuple[str | None, str | None]:
        video_els = []
        video_els.extend(bs4.select('#channelsProfile .videos a.videoPreviewBg'))
        video_els.extend(bs4.select('#profileContent .videos:not(#privateVideosSection) a.videoPreviewBg'))
        video_els.extend(bs4.select('#pornstarsVideoSection .videoPreviewBg'))
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


