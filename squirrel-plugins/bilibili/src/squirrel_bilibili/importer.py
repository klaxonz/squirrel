from __future__ import annotations

import logging
from typing import List

from bilibili_api import user

from crawl import IUserSubscriptionImporter, register_user_subscription_importer
from .api_client import build_credential, throttled_sync


logger = logging.getLogger(__name__)
SITE_SLUG = "bilibili"


@register_user_subscription_importer("bilibili")
class BilibiliUserSubscriptionImporter(IUserSubscriptionImporter):
    """
    从 Bilibili 导入用户的关注列表
    需要登录 cookies 才能获取
    """
    
    domain = 'bilibili.com'
    
    def _get_current_user_mid(self) -> str:
        """获取当前登录用户的 mid"""
        credential = build_credential(f'https://www.{self.domain}')
        info = throttled_sync(user.get_self_info(credential))
        mid = info.get('mid')
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
            credential = build_credential(f'https://www.{self.domain}')
            mid = self._get_current_user_mid()
            logger.info(f"Getting subscriptions for Bilibili user: {mid}")
            
            user_obj = user.User(int(mid), credential=credential)
            subscription_urls: List[str] = []
            page = 1
            page_size = 50
            
            while True:
                data = throttled_sync(user_obj.get_followings(pn=page, ps=page_size))
                followings = data.get('list') or []
                if not followings:
                    break
                
                for following in followings:
                    following_mid = following.get('mid')
                    if following_mid:
                        space_url = f'https://space.bilibili.com/{following_mid}'
                        subscription_urls.append(space_url)
                
                total = data.get('total', 0)
                if not total or len(subscription_urls) >= total or len(followings) < page_size:
                    break
                
                page += 1
            
            logger.info(f"Found {len(subscription_urls)} Bilibili subscriptions")
            return subscription_urls
            
        except Exception as e:
            logger.error(f"Failed to import Bilibili subscriptions: {e}", exc_info=True)
            raise

