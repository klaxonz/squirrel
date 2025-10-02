from __future__ import annotations

import logging
import re
from typing import List

from bs4 import BeautifulSoup

from crawl import (
    register_subscription,
    SubscriptionMeta,
    filter_cookies_to_query_string,
    request,
)
from .sign import sign


logger = logging.getLogger(__name__)


@register_subscription("bilibili", ["bilibili.com"])
class BilibiliSubscription:
    def __init__(self, url: str) -> None:
        self.url = url
        self.subscription_type = self._detect_type()
    
    def _detect_type(self) -> str:
        """检测订阅类型：space(空间), favlist(收藏夹), season(合集)"""
        if '/favlist' in self.url or 'fid=' in self.url:
            return 'favlist'
        elif '/season/' in self.url or 'season_id=' in self.url:
            return 'season'
        elif '/space.bilibili.com/' in self.url or 'space.bilibili.com' in self.url:
            return 'space'
        return 'space'

    def get_mid(self) -> str:
        match = re.search(r'/([0-9]+)(?:\?.*)?$', self.url)
        if not match:
            raise ValueError('Invalid bilibili space url')
        return match.group(1)
    
    def _extract_favlist_id(self) -> str:
        """提取收藏夹ID"""
        match = re.search(r'fid=(\d+)', self.url)
        if match:
            return match.group(1)
        match = re.search(r'/favlist\?fid=(\d+)', self.url)
        if match:
            return match.group(1)
        raise ValueError('Invalid bilibili favlist url')
    
    def _extract_season_id(self) -> str:
        """提取合集ID"""
        match = re.search(r'season_id=(\d+)', self.url)
        if match:
            return match.group(1)
        match = re.search(r'/season/(\d+)', self.url)
        if match:
            return match.group(1)
        raise ValueError('Invalid bilibili season url')

    def get_subscribe_info(self) -> SubscriptionMeta:
        if self.subscription_type == 'favlist':
            return self._get_favlist_info()
        elif self.subscription_type == 'season':
            return self._get_season_info()
        else:
            return self._get_space_info()
    
    def _get_space_info(self) -> SubscriptionMeta:
        """获取空间（用户）信息"""
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            "Referer": self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        resp = request('GET', self.url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        title_tag = soup.find('title')
        channel_name = title_tag.text.split('的个人空间')[0] if title_tag and title_tag.text else None

        avatar_link = soup.find('link', rel='apple-touch-icon')
        avatar_url = None
        if avatar_link:
            avatar_url = avatar_link.get('href')
            if avatar_url and avatar_url.startswith('//'):
                avatar_url = 'https:' + avatar_url

        return SubscriptionMeta(self.get_mid(), channel_name, avatar_url, self.url)
    
    def _get_favlist_info(self) -> SubscriptionMeta:
        """获取收藏夹信息"""
        fid = self._extract_favlist_id()
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            "Referer": self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        
        api_url = f'https://api.bilibili.com/x/v3/fav/folder/info?media_id={fid}'
        resp = request('GET', api_url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('code') == 0 and data.get('data'):
            info = data['data']
            return SubscriptionMeta(
                f"fav_{fid}",
                info.get('title', '收藏夹'),
                info.get('cover', None),
                self.url
            )
        raise ValueError('Failed to get favlist info')
    
    def _get_season_info(self) -> SubscriptionMeta:
        """获取合集信息"""
        season_id = self._extract_season_id()
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            "Referer": self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        
        api_url = f'https://api.bilibili.com/x/polymer/space/seasons_series_list?mid={self.get_mid()}&season_id={season_id}'
        resp = request('GET', api_url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('code') == 0 and data.get('data'):
            # 查找对应的合集
            items = data['data'].get('items_lists', {}).get('seasons_list', [])
            for item in items:
                if str(item.get('meta', {}).get('season_id')) == season_id:
                    meta = item.get('meta', {})
                    return SubscriptionMeta(
                        f"season_{season_id}",
                        meta.get('name', '合集'),
                        meta.get('cover', None),
                        self.url
                    )
        raise ValueError('Failed to get season info')

    def get_subscribe_videos(self, extract_all: bool) -> List[str]:
        if self.subscription_type == 'favlist':
            return self._get_favlist_videos(extract_all)
        elif self.subscription_type == 'season':
            return self._get_season_videos(extract_all)
        else:
            return self._get_space_videos(extract_all)
    
    def _get_space_videos(self, extract_all: bool) -> List[str]:
        """获取空间（用户）的视频列表"""
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }

        params = {
            'mid': self.get_mid(),
            'ps': '50',
            'pn': '1',
            'index': '1',
            'order': 'pubdate',
            'platform': 'web',
            'web_location': '1550101'
        }
        video_list: List[str] = []

        should_continue = True
        while should_continue:
            query = sign(params)
            req_url = f'https://api.bilibili.com/x/space/wbi/arc/search?{query}'
            resp = request('GET', req_url, headers=headers, timeout=15)
            if resp.status_code != 200:
                raise RuntimeError('Request failed')

            info = resp.json()
            page = info['data']['page']
            total_page = page['count'] / page['ps']

            for v in info['data']['list']['vlist']:
                if v.get('is_union_video') == 1:
                    continue
                video_list.append(f'https://www.bilibili.com/video/{v["bvid"]}')

            if int(params['pn']) < int(total_page) + 1:
                params['pn'] = str(int(params['pn']) + 1)
            else:
                should_continue = False

            if not extract_all:
                should_continue = False

        return video_list
    
    def _get_favlist_videos(self, extract_all: bool) -> List[str]:
        """获取收藏夹的视频列表"""
        fid = self._extract_favlist_id()
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        
        video_list: List[str] = []
        page = 1
        page_size = 20
        should_continue = True
        
        while should_continue:
            api_url = f'https://api.bilibili.com/x/v3/fav/resource/list?media_id={fid}&pn={page}&ps={page_size}'
            resp = request('GET', api_url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('code') == 0 and data.get('data'):
                medias = data['data'].get('medias', [])
                if not medias:
                    break
                
                for media in medias:
                    bvid = media.get('bvid')
                    if bvid:
                        video_list.append(f'https://www.bilibili.com/video/{bvid}')
                
                has_more = data['data'].get('has_more', False)
                if has_more and extract_all:
                    page += 1
                else:
                    should_continue = False
            else:
                should_continue = False
        
        logger.info(f"从收藏夹提取了 {len(video_list)} 个视频")
        return video_list
    
    def _get_season_videos(self, extract_all: bool) -> List[str]:
        """获取合集的视频列表"""
        season_id = self._extract_season_id()
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        
        video_list: List[str] = []
        page = 1
        page_size = 30
        should_continue = True
        
        while should_continue:
            api_url = f'https://api.bilibili.com/x/polymer/space/seasons_archives_list?mid={self.get_mid()}&season_id={season_id}&page_num={page}&page_size={page_size}'
            resp = request('GET', api_url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('code') == 0 and data.get('data'):
                archives = data['data'].get('archives', [])
                if not archives:
                    break
                
                for archive in archives:
                    bvid = archive.get('bvid')
                    if bvid:
                        video_list.append(f'https://www.bilibili.com/video/{bvid}')
                
                meta = data['data'].get('meta', {})
                total = meta.get('total', 0)
                if len(video_list) < total and extract_all:
                    page += 1
                else:
                    should_continue = False
            else:
                should_continue = False
        
        logger.info(f"从合集提取了 {len(video_list)} 个视频")
        return video_list


