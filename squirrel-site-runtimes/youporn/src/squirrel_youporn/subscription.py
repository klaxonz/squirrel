from __future__ import annotations

from urllib.parse import parse_qsl, urljoin, urlparse, urlunparse

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

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


class YouPornSubscription:
    def __init__(self, url: str) -> None:
        self.url = self._normalize_url(url)

    def get_subscribe_info(self) -> SubscriptionMeta:
        response = request("GET", self.url, headers=self._build_headers(), timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
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
        page = resolve_page(context)
        count_offset = resolve_count_offset(context)
        previous_page_urls = resolve_previous_page_urls(context)
        response = request("GET", build_page_url(self._canonical_url(), page), headers=self._build_headers(), timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        base_url = self._base_url()
        limit = resolve_subscription_limit(context)
        latest_video_url: str | None = None
        video_urls: list[str] = []
        seen_urls: set[str] = set()
        head_sample_urls: list[str] = []
        page_video_urls: list[str] = []

        for selector in ('a[data-testid="plw_video_thumbnail_link"]', 'a.video-box-image[href^="/watch/"]'):
            for element in soup.select(selector):
                href = element.get("href")
                if not isinstance(href, str) or not href.startswith("/watch/"):
                    continue

                video_url = urljoin(base_url, href)
                if video_url not in page_video_urls:
                    page_video_urls.append(video_url)
                if video_url not in head_sample_urls and len(head_sample_urls) < HEAD_SAMPLE_LIMIT:
                    head_sample_urls.append(video_url)
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
                        head_sample_urls=head_sample_urls if context.mode != "full" else None,
                        anchor_found=True if stop_reason == "cursor_hit" and context.mode != "full" else None,
                    )

        page_unique_count = count_page_unique_videos(page_video_urls, previous_page_urls)
        if context.mode == "full":
            next_page = self._resolve_next_page(soup, page)
            if next_page is not None:
                return build_subscription_sync_result(
                    video_urls=video_urls,
                    latest_video_url=latest_video_url,
                    context=context,
                    stop_reason="batch_exhausted",
                    cursor_payload={
                        "page": next_page,
                        "count_offset": count_offset + page_unique_count,
                        "previous_page_urls": page_video_urls,
                    },
                    has_more=True,
                )

        return build_subscription_sync_result(
            video_urls=video_urls,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason="source_exhausted",
            total_available=count_offset + page_unique_count if context.mode == "full" else None,
            head_sample_urls=head_sample_urls if context.mode != "full" else None,
            anchor_found=False if context.mode != "full" and context.last_seen_video_url else None,
        )

    def _build_headers(self) -> dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        cookies = filter_cookies_to_query_string(self.url)
        if cookies:
            headers["Cookie"] = cookies
        return headers

    def _canonical_url(self) -> str:
        parsed = urlparse(self.url)
        return urlunparse(parsed._replace(query=""))

    def _base_url(self) -> str:
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _resolve_next_page(self, soup: BeautifulSoup, current_page: int) -> int | None:
        next_pages: list[int] = []
        for element in soup.select("a.tm_pagination_link.pagination_number_link"):
            candidate = element.get("data-page-number")
            if candidate is None:
                href = element.get("href")
                if isinstance(href, str):
                    parsed = urlparse(href)
                    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
                    candidate = params.get("page")
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
        for selector in ("h1.title-text", "h1.name-title"):
            element = soup.select_one(selector)
            if element and getattr(element, "text", "").strip():
                return str(element.text).strip()
        raise ValueError(f"Cannot find subscription name in {self.url}")

    def _extract_channel_id(self, soup: BeautifulSoup) -> str | None:
        for selector in (
            ".channel_subscription_button",
            ".pornstar_subscription_button",
            ".subscribeButton",
        ):
            element = soup.select_one(selector)
            if not element:
                continue
            for attr in ("data-entityId", "data-id"):
                value = element.get(attr)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    def _extract_avatar(self, soup: BeautifulSoup) -> str | None:
        for selector in (
            ".avatar-wrapper img",
            ".profile-avatar img",
        ):
            element = soup.select_one(selector)
            if not element:
                continue
            for attr in ("data-src", "src"):
                value = element.get(attr)
                if isinstance(value, str) and value.strip() and not value.startswith("data:image/"):
                    return value.strip()
        return None

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()

        if netloc.endswith(".youporn.com") and netloc != "www.youporn.com":
            parsed = parsed._replace(netloc="www.youporn.com")
        elif netloc == "youporn.com":
            parsed = parsed._replace(netloc="www.youporn.com")

        path = parsed.path or "/"
        if not path.endswith("/"):
            path = f"{path}/"

        return urlunparse(parsed._replace(path=path))
