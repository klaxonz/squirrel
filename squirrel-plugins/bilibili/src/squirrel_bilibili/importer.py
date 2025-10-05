from __future__ import annotations

import logging
import re
from typing import List

from crawl import (
    IUserSubscriptionImporter,
    register_user_subscription_importer,
    filter_cookies_to_query_string,
    request_without_limit,
)


logger = logging.getLogger(__name__)


@register_user_subscription_importer("bilibili")
class BilibiliUserSubscriptionImporter(IUserSubscriptionImporter):
    """
    从 Bilibili 导入用户的关注列表
    需要登录 cookies 才能获取
    """
    
    domain = 'bilibili.com'
    
    def _get_current_user_mid(self) -> str:
        """获取当前登录用户的 mid"""
        base_url = f'https://www.{self.domain}'
        cookies = filter_cookies_to_query_string(base_url)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies,
        }
        
        # 获取用户信息
        api_url = 'https://api.bilibili.com/x/web-interface/nav'
        resp = request_without_limit('GET', api_url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('code') != 0:
            raise ValueError(f"Failed to get user info: {data.get('message', 'Unknown error')}")
        
        mid = data['data']['mid']
        if not mid:
            raise ValueError("User not logged in or cookies expired")
        
        return str(mid)
    
    def get_user_subscriptions(self) -> List[str]:
        """
        获取用户在 Bilibili 的关注列表
        
        Returns:
            关注的 UP 主空间 URL 列表
        """
        try:
            mid = self._get_current_user_mid()
            logger.info(f"Getting subscriptions for Bilibili user: {mid}")
            
            base_url = f'https://www.{self.domain}'
            cookies = filter_cookies_to_query_string(base_url)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
                'Cookie': cookies,
            }
            subscription_urls: List[str] = []
            page = 1
            page_size = 50
            
            while True:
                # 获取关注列表
                api_url = f'https://api.bilibili.com/x/relation/followings?vmid={mid}&pn={page}&ps={page_size}'
                resp = request_without_limit('GET', api_url, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                
                if data.get('code') != 0:
                    logger.error(f"Failed to get followings page {page}: {data.get('message')}")
                    break
                
                followings = data['data'].get('list', [])
                if not followings:
                    break
                
                for following in followings:
                    following_mid = following.get('mid')
                    if following_mid:
                        space_url = f'https://space.bilibili.com/{following_mid}'
                        subscription_urls.append(space_url)
                
                # 检查是否还有下一页
                total = data['data'].get('total', 0)
                if len(subscription_urls) >= total:
                    break
                
                page += 1
            
            logger.info(f"Found {len(subscription_urls)} Bilibili subscriptions")
            return subscription_urls
            
        except Exception as e:
            logger.error(f"Failed to import Bilibili subscriptions: {e}", exc_info=True)
            raise

