from __future__ import annotations

import logging
import re
from typing import Any

from bs4 import BeautifulSoup
from crawl import (
    SubscriptionImportBatchResult,
    SubscriptionImportItem,
)

from .html_client import DEFAULT_JAVDB_TIMEOUT_SECONDS, fetch_javdb_html

logger = logging.getLogger(__name__)


def _detect_javdb_error_page(body: str) -> str | None:
    normalized_body = str(body or "").lower()
    if not normalized_body:
        return None
    if (
        "<title> sign in | javdb" in normalized_body
        or "this content requires login to view" in normalized_body
        or 'action="/user_sessions"' in normalized_body
    ):
        return "login"
    if "<title>just a moment" in normalized_body:
        return "challenge"
    if "cf-error-details" in normalized_body and (
        "bad gateway" in normalized_body or "error code 502" in normalized_body
    ):
        return "gateway"
    return None


class JavdbUserSubscriptionImporter:
    """
    Import a user's subscription list from JavDB.
    Requires login cookies to access.
    """

    domain = "javdb.com"
    page_fetch_timeout = DEFAULT_JAVDB_TIMEOUT_SECONDS

    def get_user_subscriptions(self) -> list[SubscriptionImportItem]:
        items: list[SubscriptionImportItem] = []
        cursor_payload: dict[str, Any] | None = None

        while True:
            batch = self.get_user_subscriptions_batch(cursor_payload=cursor_payload)
            items.extend(batch.items)
            if not batch.has_more:
                break
            cursor_payload = batch.cursor_payload

        return items

    def get_user_subscriptions_batch(
        self,
        cursor_payload: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> SubscriptionImportBatchResult:
        try:
            page = self._resolve_page(cursor_payload)
            soup = self._fetch_page_soup(page)
            items = self._extract_page_items(soup, page)
            total_pages = self._extract_total_pages(soup)
            has_more = self._has_more_pages(page, total_pages, soup)

            return SubscriptionImportBatchResult(
                items=self._apply_limit(items, limit),
                cursor_payload={"page": page + 1} if has_more else None,
                has_more=has_more,
                stop_reason="batch_exhausted" if has_more else "source_exhausted",
            )
        except Exception as exc:  # SDK boundary — top-level import batch operation
            logger.error("Failed to import JavDB subscriptions batch: %s", exc, exc_info=True)
            raise

    def _resolve_page(self, cursor_payload: dict[str, Any] | None) -> int:
        try:
            page = int((cursor_payload or {}).get("page", 1) or 1)
        except (TypeError, ValueError):
            page = 1
        return max(page, 1)

    def _fetch_page_soup(self, page: int) -> BeautifulSoup:
        response = fetch_javdb_html(
            self._build_page_url(page),
            timeout=self.page_fetch_timeout,
            use_rate_limit=False,
        )
        response.raise_for_status()
        error_type = _detect_javdb_error_page(response.text or "")
        if error_type == "login":
            raise RuntimeError("JavDB returned a login page while loading subscriptions")
        if error_type == "gateway":
            raise RuntimeError("JavDB returned a gateway error page while loading subscriptions")
        if error_type == "challenge":
            raise RuntimeError("JavDB returned a Cloudflare challenge page while loading subscriptions")
        return BeautifulSoup(response.text, "html.parser")

    def _build_page_url(self, page: int) -> str:
        return f"https://{self.domain}/users/collection_actors?page={page}"

    def _extract_page_items(self, soup: BeautifulSoup, page: int) -> list[SubscriptionImportItem]:
        items: list[SubscriptionImportItem] = []
        seen_urls: set[str] = set()

        for item in soup.select(".actor-box a:has(img.avatar)"):
            href = item.get("href")
            avatars = item.select("img")
            names = item.select("strong")
            if not avatars or not names:
                logger.debug("Skipping malformed JavDB actor item on page %s", page)
                continue
            if not href or "/actors/" not in href:
                continue

            full_url = f"https://{self.domain}{href}" if href.startswith("/") else href
            full_url = full_url.split("?")[0]
            if not full_url or full_url in seen_urls:
                continue

            seen_urls.add(full_url)
            items.append(SubscriptionImportItem(
                url=full_url,
                name=names[0].text.strip(),
                avatar=avatars[0].get("src"),
            ))

        return items

    def _extract_total_pages(self, soup: BeautifulSoup) -> int | None:
        page_numbers: list[int] = []
        for link in soup.select(".pagination a"):
            text = str(getattr(link, "text", "") or "").strip()
            if text.isdigit():
                page_numbers.append(int(text))

            href = link.get("href")
            if not href:
                continue
            match = re.search(r"[?&]page=(\d+)", href)
            if match:
                page_numbers.append(int(match.group(1)))

        return max(page_numbers) if page_numbers else None

    def _has_more_pages(self, page: int, total_pages: int | None, soup: BeautifulSoup) -> bool:
        if total_pages is not None:
            return page < total_pages

        next_page = soup.select(".pagination .pagination-next")
        return bool(next_page) and "disabled" not in next_page[0].get("class", [])

    def _apply_limit(
        self,
        items: list[SubscriptionImportItem],
        limit: int | None,
    ) -> list[SubscriptionImportItem]:
        if limit is None:
            return items
        try:
            normalized_limit = int(limit)
        except (TypeError, ValueError):
            return items
        if normalized_limit <= 0:
            return items
        return items[:normalized_limit]
