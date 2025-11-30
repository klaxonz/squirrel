from __future__ import annotations

import logging
import re
from typing import List

from bs4 import BeautifulSoup

from crawl import (
    IUserSubscriptionImporter,
    register_user_subscription_importer,
    filter_cookies_to_query_string,
    request_without_limit,
    get_http_headers,
)


logger = logging.getLogger(__name__)


@register_user_subscription_importer("youtube")
class YoutubeUserSubscriptionImporter(IUserSubscriptionImporter):
    """
    从 YouTube 导入用户的订阅列表
    需要登录 cookies 才能获取
    """
    
    domain = 'youtube.com'
    
    def get_user_subscriptions(self) -> List[str]:
        """
        获取用户在 YouTube 的订阅列表
        
        Returns:
            订阅的频道 URL 列表
        """
        try:
            base_url = f'https://www.{self.domain}'
            cookies = filter_cookies_to_query_string(base_url)
            headers = get_http_headers('youtube', {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            })
            headers['Cookie'] = cookies
            
            # 访问订阅页面
            subscriptions_url = f'{base_url}/feed/channels'
            resp = request_without_limit('GET', subscriptions_url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            # 解析页面获取频道链接
            subscription_urls: List[str] = []
            
            # YouTube 的订阅页面需要解析 JavaScript 数据
            # 寻找包含频道信息的数据
            html_content = resp.text
            
            # 尝试从 HTML 中提取频道链接
            # YouTube 使用动态加载，频道链接在 ytInitialData 中
            pattern = r'"channelId":"([^"]+)"'
            channel_ids = re.findall(pattern, html_content)
            
            # 去重
            channel_ids = list(set(channel_ids))
            
            for channel_id in channel_ids:
                # 过滤掉一些系统频道
                if not channel_id.startswith('UC'):
                    continue
                channel_url = f'https://www.youtube.com/channel/{channel_id}'
                subscription_urls.append(channel_url)
            
            logger.info(f"Found {len(subscription_urls)} YouTube subscriptions")
            
            # 如果没有找到任何频道，尝试使用 BeautifulSoup 解析
            if len(subscription_urls) == 0:
                soup = BeautifulSoup(html_content, 'html.parser')
                links = soup.find_all('a', href=re.compile(r'/channel/'))
                
                for link in links:
                    href = link.get('href')
                    if href and '/channel/' in href:
                        channel_id = href.split('/channel/')[-1].split('?')[0]
                        if channel_id.startswith('UC'):
                            channel_url = f'https://www.youtube.com/channel/{channel_id}'
                            if channel_url not in subscription_urls:
                                subscription_urls.append(channel_url)
            
            logger.info(f"Final: Found {len(subscription_urls)} YouTube subscriptions")
            return subscription_urls
            
        except Exception as e:
            logger.error(f"Failed to import YouTube subscriptions: {e}", exc_info=True)
            raise

