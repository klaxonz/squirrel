from __future__ import annotations

import logging
from typing import List

from bs4 import BeautifulSoup

from crawl import (
    SubscriptionImportItem,
)

from .html_client import fetch_javdb_html


logger = logging.getLogger(__name__)


class JavdbUserSubscriptionImporter:
    """
    从 JavDB 导入用户的订阅列表
    需要登录 cookies 才能获取
    """
    
    domain = 'javdb.com'
    
    def get_user_subscriptions(self) -> List[SubscriptionImportItem]:
        """
        获取用户在 JavDB 的订阅列表
        
        Returns:
            订阅列表
        """
        try:
            base_url = f'https://{self.domain}'
            items = []
            subscription_urls: List[str] = []
            page = 1
            
            # JavDB 的订阅演员页面
            while True:
                # 访问订阅页面
                subscribed_url = f'{base_url}/users/collection_actors?page={page}'
                
                try:
                    resp = fetch_javdb_html(
                        subscribed_url,
                        timeout=15,
                        use_rate_limit=False,
                    )
                    resp.raise_for_status()
                    
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    # 查找演员链接
                    actor_items = soup.select('.actor-box a:has(img.avatar)')
                    
                    if not actor_items:
                        # 没有更多数据了
                        break
                    
                    for item in actor_items:
                        href = item.get('href')
                        avatar = item.select('img')[0].get('src')
                        name = item.select('strong')[0].text.strip()
                        if href and '/actors/' in href:
                            full_url = f'{base_url}{href}' if href.startswith('/') else href
                            # 去掉查询参数，只保留演员页面 URL
                            full_url = full_url.split('?')[0]
                            if full_url not in subscription_urls:
                                subscription_urls.append(full_url)
                                items.append(SubscriptionImportItem(url=full_url, name=name, avatar=avatar))
                    
                    # 检查是否有下一页
                    next_page = soup.select('.pagination .pagination-next')
                    if not next_page or 'disabled' in next_page[0].get('class', []):
                        break
                    
                    page += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to get JavDB page {page}: {e}")
                    break
            
            logger.info(f"Found {len(subscription_urls)} JavDB subscriptions")
            return items
            
        except Exception as e:
            logger.error(f"Failed to import JavDB subscriptions: {e}", exc_info=True)
            raise

