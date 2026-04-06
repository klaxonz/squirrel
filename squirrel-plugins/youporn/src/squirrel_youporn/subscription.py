from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from crawl import (
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
    append_subscription_video_url,
    build_subscription_sync_result,
    filter_cookies_to_query_string,
    resolve_subscription_limit,
    request,
)


DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}


class YouPornSubscription:
    def __init__(self, url: str) -> None:
        self.url = self._normalize_url(url)

    def get_subscribe_info(self) -> SubscriptionMeta:
        response = request('GET', self.url, headers=self._build_headers(), timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        name = self._extract_name(soup)
        channel_id = self._extract_channel_id(soup)
        avatar = self._extract_avatar(soup)

        return SubscriptionMeta(
            id=channel_id,
            name=name,
            avatar=avatar,
            url=self._canonical_url(),
        )

    def sync_videos(self, context: SubscriptionSyncContext) -> SubscriptionSyncResult:
        page = self._resolve_page(context)
        response = request('GET', self._build_page_url(page), headers=self._build_headers(), timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        base_url = self._base_url()
        limit = resolve_subscription_limit(context)
        latest_video_url: Optional[str] = None
        video_urls: list[str] = []
        seen_urls: set[str] = set()

        for selector in ('a[data-testid="plw_video_thumbnail_link"]', 'a.video-box-image[href^="/watch/"]'):
            for element in soup.select(selector):
                href = element.get('href')
                if not isinstance(href, str) or not href.startswith('/watch/'):
                    continue

                video_url = urljoin(base_url, href)
                latest_video_url, stop_reason = append_subscription_video_url(
                    video_url,
                    video_urls=video_urls,
                    seen_urls=seen_urls,
                    context=context,
                    latest_video_url=latest_video_url,
                    limit=limit,
                )
                if stop_reason:
                    return build_subscription_sync_result(
                        video_urls=video_urls,
                        latest_video_url=latest_video_url,
                        context=context,
                        stop_reason=stop_reason,
                    )

        if context.mode == 'full':
            next_page = self._resolve_next_page(soup, page)
            if next_page is not None:
                return build_subscription_sync_result(
                    video_urls=video_urls,
                    latest_video_url=latest_video_url,
                    context=context,
                    stop_reason='batch_exhausted',
                    cursor_payload={'page': next_page},
                    has_more=True,
                )

        return build_subscription_sync_result(
            video_urls=video_urls,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason='source_exhausted',
        )

    def _build_headers(self) -> dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        cookies = filter_cookies_to_query_string(self.url)
        if cookies:
            headers['Cookie'] = cookies
        return headers

    def _canonical_url(self) -> str:
        parsed = urlparse(self.url)
        return urlunparse(parsed._replace(query=''))

    def _base_url(self) -> str:
        parsed = urlparse(self.url)
        return f'{parsed.scheme}://{parsed.netloc}'

    def _resolve_page(self, context: SubscriptionSyncContext) -> int:
        page = (context.cursor_payload or {}).get('page', 1)
        try:
            return max(1, int(page))
        except (TypeError, ValueError):
            return 1

    def _build_page_url(self, page: int) -> str:
        if page <= 1:
            return self._canonical_url()

        parsed = urlparse(self.url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query['page'] = str(page)
        return urlunparse(parsed._replace(query=urlencode(query)))

    def _resolve_next_page(self, soup: BeautifulSoup, current_page: int) -> Optional[int]:
        next_pages: list[int] = []
        for element in soup.select('a.tm_pagination_link.pagination_number_link'):
            candidate = element.get('data-page-number')
            if candidate is None:
                href = element.get('href')
                if isinstance(href, str):
                    parsed = urlparse(href)
                    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
                    candidate = params.get('page')
            try:
                page_number = int(candidate)
            except (TypeError, ValueError):
                continue
            if page_number > current_page:
                next_pages.append(page_number)

        if not next_pages:
            return None
        return min(next_pages)

    def _extract_name(self, soup: BeautifulSoup) -> str:
        for selector in ('h1.title-text', 'h1.name-title'):
            element = soup.select_one(selector)
            if element and getattr(element, 'text', '').strip():
                return str(element.text).strip()
        raise ValueError(f'Cannot find subscription name in {self.url}')

    def _extract_channel_id(self, soup: BeautifulSoup) -> Optional[str]:
        for selector in (
            '.channel_subscription_button',
            '.pornstar_subscription_button',
            '.subscribeButton',
        ):
            element = soup.select_one(selector)
            if not element:
                continue
            for attr in ('data-entityId', 'data-id'):
                value = element.get(attr)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    def _extract_avatar(self, soup: BeautifulSoup) -> Optional[str]:
        for selector in (
            '.avatar-wrapper img',
            '.profile-avatar img',
        ):
            element = soup.select_one(selector)
            if not element:
                continue
            for attr in ('data-src', 'src'):
                value = element.get(attr)
                if isinstance(value, str) and value.strip() and not value.startswith('data:image/'):
                    return value.strip()
        return None

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()

        if netloc.endswith('.youporn.com') and netloc != 'www.youporn.com':
            parsed = parsed._replace(netloc='www.youporn.com')
        elif netloc == 'youporn.com':
            parsed = parsed._replace(netloc='www.youporn.com')

        path = parsed.path or '/'
        if not path.endswith('/'):
            path = f'{path}/'

        return urlunparse(parsed._replace(path=path))
