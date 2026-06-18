"""Subscription importer utilities and base classes."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from bs4 import BeautifulSoup

from .config import get_http_headers
from .core import SubscriptionImportItem
from .http import request_without_limit
from .utils import filter_cookies_to_query_string

logger = logging.getLogger(__name__)


class BaseImporter(ABC):
    """Base class for subscription importers with common utilities.

    Provides helper methods for common operations like fetching pages,
    parsing HTML, and handling cookies. Subclasses implement the actual
    import logic in `get_user_subscriptions()`.

    Example:
        class MySiteImporter(BaseImporter):
            domain = 'mysite.com'
            site_slug = 'mysite'

            def get_user_subscriptions(self) -> List[SubscriptionImportItem]:
                soup = self._fetch_page('/subscriptions')
                items = soup.select('a.subscription-link')
                return [
                    SubscriptionImportItem(url=self._to_full_url(item.get('href')))
                    for item in items
                    if item.get('href')
                ]
    """

    domain: str = ""
    site_slug: str = ""
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    timeout: int = 15

    @property
    def base_url(self) -> str:
        return f"https://www.{self.domain}"

    def _get_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Get HTTP headers with cookies."""
        base = {"User-Agent": self.user_agent}
        if extra:
            base.update(extra)
        headers = get_http_headers(self.site_slug, base)
        cookies = filter_cookies_to_query_string(self.base_url)
        if cookies:
            headers["Cookie"] = cookies
        return headers

    def _fetch_page(self, path: str, headers: dict[str, str] | None = None) -> BeautifulSoup:
        """Fetch a page and return parsed BeautifulSoup."""
        url = self._to_full_url(path)
        hdrs = headers or self._get_headers()
        resp = request_without_limit("GET", url, headers=hdrs, timeout=self.timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    def _fetch_page_raw(self, path: str, headers: dict[str, str] | None = None) -> str:
        """Fetch a page and return raw HTML text."""
        url = self._to_full_url(path)
        hdrs = headers or self._get_headers()
        resp = request_without_limit("GET", url, headers=hdrs, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def _to_full_url(self, path: str) -> str:
        """Convert a path to full URL."""
        if not path:
            return ""
        if path.startswith("http"):
            return path
        if path.startswith("/"):
            return f"{self.base_url}{path}"
        return f"{self.base_url}/{path}"

    def _extract_links(
        self,
        soup: BeautifulSoup,
        selector: str,
        url_filter: str | None = None
    ) -> list[str]:
        """Extract links from soup using CSS selector.

        Args:
            soup: BeautifulSoup object
            selector: CSS selector for link elements
            url_filter: Optional substring that href must contain

        Returns:
            List of full URLs
        """
        urls: list[str] = []
        items = soup.select(selector)
        for item in items:
            href = item.get("href")
            if not href:
                continue
            if url_filter and url_filter not in href:
                continue
            full_url = self._to_full_url(href)
            if full_url and full_url not in urls:
                urls.append(full_url)
        return urls

    @abstractmethod
    def get_user_subscriptions(self) -> list[SubscriptionImportItem]:
        """Get user's subscriptions. Must be implemented by subclasses."""
        pass


class PaginatedImporter(BaseImporter):
    """Base class for importers that use simple pagination.

    For sites with straightforward pagination (page=1, page=2, etc.),
    subclasses only need to implement a few methods:

    Example:
        class MySiteImporter(PaginatedImporter):
            domain = 'mysite.com'
            site_slug = 'mysite'
            subscriptions_path = '/user/subscriptions'
            item_selector = 'a.subscription-link'
            max_pages = 100

            def _extract_url_from_item(self, item) -> Optional[str]:
                href = item.get('href')
                if href and '/channel/' in href:
                    return self._to_full_url(href)
                return None
    """

    subscriptions_path: str = "/subscriptions"
    item_selector: str = "a"
    max_pages: int = 100
    page_param: str = "page"

    def get_user_subscriptions(self) -> list[SubscriptionImportItem]:
        """Paginated subscription fetching."""
        subscription_urls: list[str] = []
        headers = self._get_headers()

        for page in range(1, self.max_pages + 1):
            try:
                page_url = self._build_page_url(page)
                logger.info("Fetching %s subscriptions page %s: %s", self.domain, page, page_url)

                resp = request_without_limit("GET", page_url, headers=headers, timeout=self.timeout)

                if resp.status_code == 404:
                    logger.info("Page %s returned 404, stopping pagination", page)
                    break

                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                items = soup.select(self.item_selector)
                if not items:
                    logger.info("No items found on page %s, stopping pagination", page)
                    break

                new_count = 0
                for item in items:
                    url = self._extract_url_from_item(item)
                    if url and url not in subscription_urls:
                        subscription_urls.append(url)
                        new_count += 1

                logger.info(
                    "Page %s: added %s new subscriptions, total=%s",
                    page,
                    new_count,
                    len(subscription_urls),
                )

                if new_count == 0:
                    break

                if not self._has_next_page(soup, page):
                    break

            except (OSError, ValueError, TypeError) as e:
                logger.warning("Error fetching page %s: %s", page, e)
                break

        return [SubscriptionImportItem(url=url) for url in subscription_urls]

    def _build_page_url(self, page: int) -> str:
        """Build URL for a specific page."""
        base = self._to_full_url(self.subscriptions_path)
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}{self.page_param}={page}"

    def _extract_url_from_item(self, item: Any) -> str | None:
        """Extract URL from a single item. Override in subclass."""
        href = item.get("href")
        return self._to_full_url(href) if href else None

    def _has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
        """Check if there's a next page. Override for custom logic."""
        return True
