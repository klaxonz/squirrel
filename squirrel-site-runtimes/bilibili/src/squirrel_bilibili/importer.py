from __future__ import annotations

import logging

from crawl import SubscriptionImportItem

from .api_client import build_cookies
from .subscription_api import fetch_followings, fetch_nav

logger = logging.getLogger(__name__)
SITE_SLUG = "bilibili"


class BilibiliUserSubscriptionImporter:
    """
    从 Bilibili 导入用户的关注列表
    需要登录 cookies 才能获取
    """

    domain = "bilibili.com"

    def _get_current_user_mid(self, cookies: str) -> str:
        """获取当前登录用户的 mid"""
        nav = fetch_nav(cookies=cookies, throttled=False)
        mid = nav.get("mid")
        if not mid:
            raise ValueError("User not logged in or cookies expired")
        return str(mid)

    def get_user_subscriptions(self) -> list[SubscriptionImportItem]:
        """
        获取用户在 Bilibili 的关注列表

        Returns:
            订阅列表
        """
        cookies = build_cookies(f"https://www.{self.domain}")
        mid = self._get_current_user_mid(cookies)
        logger.info("Getting subscriptions for bilibili user: %s", mid)

        page = 1
        page_size = 50

        items: list[SubscriptionImportItem] = []
        while True:
            data = fetch_followings(
                int(mid),
                cookies=cookies,
                pn=page,
                ps=page_size,
                throttled=False,
            )
            followings = data.get("list") or []
            if not followings:
                break

            for following in followings:
                following_mid = following.get("mid")
                if following_mid:
                    space_url = f"https://space.bilibili.com/{following_mid}"
                    face = following.get("face")
                    name = following.get("uname")
                    items.append(SubscriptionImportItem(url=space_url, name=name, avatar=face))

            total = data.get("total", 0)
            if not total or len(items) >= total or len(followings) < page_size:
                break

            page += 1

        logger.info("Found %s bilibili subscriptions", len(items))
        return items
