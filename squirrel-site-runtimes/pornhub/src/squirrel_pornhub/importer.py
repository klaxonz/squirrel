from __future__ import annotations

import logging

from bs4 import BeautifulSoup
from crawl import (
    SubscriptionImportItem,
    filter_cookies_to_query_string,
    get_http_headers,
    request_without_limit,
)

logger = logging.getLogger(__name__)
SITE_SLUG = "pornhub"


class PornhubUserSubscriptionImporter:
    """
    从 Pornhub 导入用户的订阅列表
    需要登录 cookies 才能获取
    """

    domain = "pornhub.com"

    def get_user_subscriptions(self) -> list[SubscriptionImportItem]:
        """
        获取用户在 Pornhub 的订阅列表
        
        Returns:
            订阅列表
        """
        try:
            base_url = f"https://www.{self.domain}"
            cookies = filter_cookies_to_query_string(base_url)
            headers = get_http_headers(SITE_SLUG, {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            })
            headers["Cookie"] = cookies

            channel_items = []
            subscription_urls: list[str] = []

            # 优先使用新的 /users/<username>/subscriptions?page=N 页面结构
            try:
                # 通过带 Cookie 访问首页，从用户菜单中解析用户名
                logger.info("Requesting Pornhub main page to detect username: %s", base_url)
                profile_resp = request_without_limit("GET", base_url, headers=headers, timeout=15)
                profile_resp.raise_for_status()

                profile_soup = BeautifulSoup(profile_resp.text, "html.parser")

                # 示例结构（来自保存的 HTML）：
                # <div id="profileMenuWrapper"> ... <div class="profileData">
                #   <a class="username" href="/users/wudiliuye"> ...
                user_link = profile_soup.select_one('#profileMenuWrapper .profileData a.username[href^="/users/"]')

                username = None
                if user_link:
                    href = user_link.get("href") or ""
                    parts = [p for p in href.split("/") if p]
                    # ['users', '<username>']
                    if len(parts) >= 2 and parts[0] == "users":
                        username = parts[1]

                if not username:
                    logger.warning("Unable to detect Pornhub username from profile menu; skip new subscriptions page parsing")
                else:
                    logger.info("Detected Pornhub username from profile menu: %s", username)

                    # 分页抓取 /users/<username>/subscriptions?page=N
                    # 使用一个足够大的上限，主要依靠“当前页无新增订阅即停止”来终止循环
                    max_pages = 10000
                    page = 1
                    while page <= max_pages:
                        page_url = f"{base_url}/users/{username}/subscriptions?page={page}"
                        logger.info("Fetching Pornhub subscriptions page %s: %s", page, page_url)
                        page_resp = request_without_limit("GET", page_url, headers=headers, timeout=15)
                        if page_resp.status_code == 404:
                            logger.info("Pornhub subscriptions page %s returned 404, stop pagination", page)
                            break
                        page_resp.raise_for_status()

                        soup = BeautifulSoup(page_resp.text, "html.parser")

                        # 每个订阅在 ul#moreData 下的 li 中：
                        #   <div class="usernameWrap ...">
                        #       <span class="usernameBadgesWrapper">
                        #           <a class="usernameLink" href="/model/...">...
                        # 只选择这些用户名链接，再用 href 前缀判断类型
                        items = soup.select("ul#moreData li")
                        logger.info("Page %s: found %s subscription username anchors", page, len(items))

                        new_count = 0
                        for item in items:
                            user_links = item.select(".usernameWrap .usernameBadgesWrapper a.usernameLink")
                            avatars = item.select(".userLink .avatar")
                            if not user_links or not avatars:
                                logger.debug("Skipping malformed Pornhub subscription item on page %s", page)
                                continue

                            href = user_links[0].get("href")
                            name = user_links[0].get("title")
                            avatar = avatars[0].get("src")
                            if not href:
                                continue

                            # 只关心作者主页相关链接
                            if not (href.startswith("/model/") or href.startswith("/pornstar/") or href.startswith("/channels/")):
                                continue

                            full_url = f"{base_url}{href}" if href.startswith("/") else href
                            if full_url not in subscription_urls:
                                subscription_urls.append(full_url)
                                new_count += 1
                                channel_items.append(SubscriptionImportItem(url=full_url, name=name, avatar=avatar))

                        logger.info("Page %s: added %s new Pornhub subscriptions, total=%s", page, new_count, len(subscription_urls))

                        # 如果这一页没有新增订阅，认为到尾页了
                        if new_count == 0:
                            break

                        page += 1

            except Exception as e:  # inner boundary — non-fatal if username-based pages fail
                logger.warning("Failed to fetch Pornhub subscriptions via username-based pages: %s", e)

            return channel_items

        except Exception as e:  # SDK boundary — top-level import operation
            logger.error(f"Failed to import Pornhub subscriptions: {e}", exc_info=True)
            raise
