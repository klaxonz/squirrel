from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from crawl import (
    SubscriptionImportItem,
    filter_cookies_to_query_string,
    get_http_headers,
    request_without_limit,
)

logger = logging.getLogger(__name__)
SITE_SLUG = "youporn"
BASE_URL = "https://www.youporn.com"
USER_ID_PATTERN = re.compile(r"/user/(\d+)/", re.IGNORECASE)
PAGE_USER_ID_PATTERN = re.compile(r'(?:"userId"|userId|liu_user_id)\s*[:=]\s*(\d+)', re.IGNORECASE)
SUPPORTED_SUBSCRIPTION_PREFIXES = ("/channel/", "/pornstar/", "/amateur/")


class YouPornUserSubscriptionImporter:
    """Import followed YouPorn channels and pornstars for the current account."""

    domain = "youporn.com"

    def get_user_subscriptions(self) -> list[SubscriptionImportItem]:
        cookies = filter_cookies_to_query_string(BASE_URL)
        headers = get_http_headers(SITE_SLUG, {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })
        headers["Cookie"] = cookies

        profile_resp = request_without_limit("GET", BASE_URL, headers=headers, timeout=15)
        profile_resp.raise_for_status()

        profile_soup = BeautifulSoup(profile_resp.text, "html.parser")
        user_id = self._extract_user_id(profile_resp.text, profile_soup)
        if not user_id:
            logger.warning("Unable to detect YouPorn user id from profile page")
            return []

        items: list[SubscriptionImportItem] = []
        seen_urls: set[str] = set()
        for tab_name in ("pornstars", "channels"):
            next_page_url = f"{BASE_URL}/user/{user_id}/{tab_name}-data/"
            tab_headers = dict(headers)
            tab_headers["Referer"] = f"{BASE_URL}/user/{user_id}/?tab={tab_name}&filter=recent"
            tab_headers["X-Requested-With"] = "XMLHttpRequest"

            while next_page_url:
                logger.info("Fetching YouPorn %s import page: %s", tab_name, next_page_url)
                response = request_without_limit("GET", next_page_url, headers=tab_headers, timeout=15)
                response.raise_for_status()

                payload = self._parse_data_payload(response.text, next_page_url)
                new_count = self._collect_payload_items(payload, items, seen_urls)
                next_page_url = self._resolve_next_page_url(payload)
                if new_count == 0 and not next_page_url:
                    break

        return items

    def _extract_user_id(self, html: str, soup: BeautifulSoup) -> str | None:
        for selector in ('a[href*="/user/"]', 'a[href*="/settings/?username="]'):
            link = soup.select_one(selector)
            if not link:
                continue
            href = str(link.get("href") or "")
            match = USER_ID_PATTERN.search(href)
            if match:
                return match.group(1)

        match = PAGE_USER_ID_PATTERN.search(html)
        if match:
            return match.group(1)
        return None

    def _parse_data_payload(self, text: str, page_url: str) -> dict[str, Any]:
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError(f"Unexpected YouPorn payload for {page_url}")
        return payload

    def _collect_payload_items(
        self,
        payload: dict[str, Any],
        items: list[SubscriptionImportItem],
        seen_urls: set[str],
    ) -> int:
        new_count = 0
        entries = ((payload.get("data") or {}).get("data") or [])
        if not isinstance(entries, list):
            return 0

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            href = str(entry.get("url") or "").strip()
            if not href or not href.startswith(SUPPORTED_SUBSCRIPTION_PREFIXES):
                continue
            name = str(entry.get("name") or "").strip() or None
            avatar = str(entry.get("thumbnail") or "").strip() or None

            full_url = urljoin(BASE_URL, href)
            if full_url in seen_urls:
                continue

            seen_urls.add(full_url)
            items.append(SubscriptionImportItem(url=full_url, name=name, avatar=avatar))
            new_count += 1

        return new_count

    def _resolve_next_page_url(self, payload: dict[str, Any]) -> str | None:
        pagination = (payload.get("data") or {}).get("pagination") or {}
        if not isinstance(pagination, dict):
            return None
        next_page = str(pagination.get("nextPage") or "").strip()
        if not next_page:
            return None
        return urljoin(BASE_URL, next_page)
