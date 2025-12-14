from __future__ import annotations

import logging
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from crawl import (
    UserSubscriptionImporter,
    register_user_subscription_importer,
    filter_cookies_to_query_string,
    request_without_limit,
    get_http_headers,
)


logger = logging.getLogger(__name__)


@register_user_subscription_importer("javdb")
class JavdbUserSubscriptionImporter:
    """
    从 JavDB 导入用户的订阅列表
    需要登录 cookies 才能获取
    """
    
    domain = 'javdb.com'
    
    def get_user_subscriptions(self) -> List[str]:
        """
        获取用户在 JavDB 的订阅列表
        
        Returns:
            订阅的演员 URL 列表
        """
        try:
            base_url = f'https://{self.domain}'
            cookies = filter_cookies_to_query_string(base_url)
            headers = get_http_headers('javdb', {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            })
            headers['Cookie'] = cookies
            
            subscription_urls: List[str] = []
            page = 1
            
            # JavDB 的订阅演员页面
            while True:
                # 访问订阅页面
                subscribed_url = f'{base_url}/users/collection_actors?page={page}'
                
                try:
                    resp = request_without_limit('GET', subscribed_url, headers=headers, timeout=15)
                    resp.raise_for_status()
                    
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    # 查找演员链接
                    actor_items = soup.select('.actor-box a')
                    
                    if not actor_items:
                        # 没有更多数据了
                        break
                    
                    for item in actor_items:
                        href = item.get('href')
                        if href and '/actors/' in href:
                            full_url = f'{base_url}{href}' if href.startswith('/') else href
                            # 去掉查询参数，只保留演员页面 URL
                            full_url = full_url.split('?')[0]
                            if full_url not in subscription_urls:
                                subscription_urls.append(full_url)
                    
                    # 检查是否有下一页
                    next_page = soup.select('.pagination .next_page')
                    if not next_page or 'disabled' in next_page[0].get('class', []):
                        break
                    
                    page += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to get JavDB page {page}: {e}")
                    break
            
            logger.info(f"Found {len(subscription_urls)} JavDB subscriptions")
            return subscription_urls
            
        except Exception as e:
            logger.error(f"Failed to import JavDB subscriptions: {e}", exc_info=True)
            raise

