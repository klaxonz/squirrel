from __future__ import annotations

import logging
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from crawl import (
    IUserSubscriptionImporter,
    register_user_subscription_importer,
    filter_cookies_to_query_string,
    request_without_limit,
)


logger = logging.getLogger(__name__)


@register_user_subscription_importer("pornhub")
class PornhubUserSubscriptionImporter(IUserSubscriptionImporter):
    """
    从 Pornhub 导入用户的订阅列表
    需要登录 cookies 才能获取
    """
    
    domain = 'pornhub.com'
    
    def get_user_subscriptions(self) -> List[str]:
        """
        获取用户在 Pornhub 的订阅列表
        
        Returns:
            订阅的频道/用户 URL 列表
        """
        try:
            base_url = f'https://www.{self.domain}'
            cookies = filter_cookies_to_query_string(base_url)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Cookie': cookies
            }
            
            subscription_urls: List[str] = []
            
            # Pornhub 的订阅页面
            # 1. 订阅的频道
            channels_url = f'{base_url}/channels/subscribed'
            try:
                resp = request_without_limit('GET', channels_url, headers=headers, timeout=15)
                resp.raise_for_status()
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 查找频道链接
                channel_items = soup.select('.channelsWrapper .channelsProfileContainer a')
                for item in channel_items:
                    href = item.get('href')
                    if href and '/channels/' in href:
                        full_url = f'{base_url}{href}' if href.startswith('/') else href
                        subscription_urls.append(full_url)
                
                logger.info(f"Found {len(subscription_urls)} Pornhub channels")
            except Exception as e:
                logger.warning(f"Failed to get Pornhub channels: {e}")
            
            # 2. 订阅的 Models
            models_url = f'{base_url}/model/subscribed'
            try:
                resp = request_without_limit('GET', models_url, headers=headers, timeout=15)
                resp.raise_for_status()
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 查找 model 链接
                model_items = soup.select('.channelsWrapper .modelProfileContainer a, .profileUserName a')
                for item in model_items:
                    href = item.get('href')
                    if href and ('/model/' in href or '/pornstar/' in href):
                        full_url = f'{base_url}{href}' if href.startswith('/') else href
                        if full_url not in subscription_urls:
                            subscription_urls.append(full_url)
                
                logger.info(f"Total: Found {len(subscription_urls)} Pornhub subscriptions")
            except Exception as e:
                logger.warning(f"Failed to get Pornhub models: {e}")
            
            # 3. 订阅的 Pornstars
            pornstars_url = f'{base_url}/pornstars/subscribed'
            try:
                resp = request_without_limit('GET', pornstars_url, headers=headers, timeout=15)
                resp.raise_for_status()
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 查找 pornstar 链接
                pornstar_items = soup.select('.pornstarsWrapper .pornstarProfileContainer a, .pornstarName a')
                for item in pornstar_items:
                    href = item.get('href')
                    if href and '/pornstar/' in href:
                        full_url = f'{base_url}{href}' if href.startswith('/') else href
                        if full_url not in subscription_urls:
                            subscription_urls.append(full_url)
                
                logger.info(f"Final: Found {len(subscription_urls)} Pornhub subscriptions")
            except Exception as e:
                logger.warning(f"Failed to get Pornhub pornstars: {e}")
            
            return subscription_urls
            
        except Exception as e:
            logger.error(f"Failed to import Pornhub subscriptions: {e}", exc_info=True)
            raise

