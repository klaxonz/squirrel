from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup

from crawl import (
    SubscriptionImportItem,
    filter_cookies_to_query_string,
    request_without_limit,
    get_http_headers,
)


logger = logging.getLogger(__name__)


class YoutubeUserSubscriptionImporter:
    """
    从 YouTube 导入用户的订阅列表
    需要登录 cookies 才能获取
    """
    
    domain = 'youtube.com'
    
    def get_user_subscriptions(self) -> List[SubscriptionImportItem]:
        """
        获取用户在 YouTube 的订阅列表
        
        Returns:
            订阅列表
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
            
            # 解析页面获取频道信息
            subscriptions: List[SubscriptionImportItem] = []

            # YouTube 的订阅页面需要解析 JavaScript 数据
            # 寻找包含频道信息的数据
            html_content = resp.text

            # 尝试从 ytInitialData 中提取完整的频道信息
            yt_initial_data = self._extract_yt_initial_data(html_content)
            if yt_initial_data:
                subscriptions = self._parse_subscriptions_from_yt_data(yt_initial_data)

            # 如果 ytInitialData 解析失败，回退到正则表达式方法
            if not subscriptions:
                logger.info("Falling back to regex parsing for YouTube subscriptions")
                pattern = r'"channelId":"([^"]+)"'
                channel_ids = re.findall(pattern, html_content)

                # 去重
                channel_ids = list(dict.fromkeys(channel_ids))

                for channel_id in channel_ids:
                    # 过滤掉一些系统频道
                    if not channel_id.startswith('UC'):
                        continue
                    channel_url = f'https://www.youtube.com/channel/{channel_id}'
                    subscriptions.append(SubscriptionImportItem(url=channel_url))
            
            logger.info(f"Found {len(subscriptions)} YouTube subscriptions")

            # 如果没有找到任何频道，尝试使用 BeautifulSoup 解析
            if len(subscriptions) == 0:
                soup = BeautifulSoup(html_content, 'html.parser')
                links = soup.find_all('a', href=re.compile(r'/channel/'))

                for link in links:
                    href = link.get('href')
                    if href and '/channel/' in href:
                        channel_id = href.split('/channel/')[-1].split('?')[0]
                        if channel_id.startswith('UC'):
                            channel_url = f'https://www.youtube.com/channel/{channel_id}'
                            # 检查是否已存在
                            if not any(sub.url == channel_url for sub in subscriptions):
                                subscriptions.append(SubscriptionImportItem(url=channel_url))

            logger.info(f"Final: Found {len(subscriptions)} YouTube subscriptions")
            return subscriptions
            
        except Exception as e:  # SDK boundary — top-level import operation
            logger.error(f"Failed to import YouTube subscriptions: {e}", exc_info=True)
            raise

    def _extract_yt_initial_data(self, html_content: str) -> Optional[dict]:
        """从 HTML 中提取 ytInitialData"""
        try:
            # 寻找 ytInitialData 的定义
            pattern = r'var ytInitialData\s*=\s*({.+?});'
            match = re.search(pattern, html_content, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse ytInitialData: {e}")
        except (TypeError, AttributeError) as e:
            logger.warning(f"Error extracting ytInitialData: {e}")

        return None

    def _parse_subscriptions_from_yt_data(self, yt_data: dict) -> List[SubscriptionImportItem]:
        """从 ytInitialData 中解析订阅信息"""
        subscriptions = []

        try:
            # YouTube 的订阅数据结构可能有多种形式，我们需要尝试不同的路径
            contents = yt_data.get('contents', {})

            # 尝试多种可能的路径来找到频道数据
            channel_renderers = []

            # 路径1: twoColumnBrowseResultsRenderer -> tabs -> 选中tab -> sectionListRenderer
            tabs = contents.get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
            for tab in tabs:
                if tab.get('tabRenderer', {}).get('selected', False):
                    tab_contents = tab.get('tabRenderer', {}).get('content', {}).get('sectionListRenderer', {}).get('contents', [])
                    for content in tab_contents:
                        items = content.get('itemSectionRenderer', {}).get('contents', [])
                        for item in items:
                            shelf_items = item.get('shelfRenderer', {}).get('content', {}).get('expandedShelfContentsRenderer', {}).get('items', [])
                            channel_renderers.extend(shelf_items)

            # 路径2: 直接在 contents 中查找 gridRenderer 或其他容器
            if not channel_renderers:
                for key, value in contents.items():
                    if isinstance(value, dict):
                        # 查找所有可能的频道渲染器
                        if 'gridRenderer' in value:
                            channel_renderers.extend(value['gridRenderer'].get('items', []))
                        elif 'itemSectionRenderer' in value:
                            channel_renderers.extend(value['itemSectionRenderer'].get('contents', []))

            # 路径3: 递归查找所有 channelRenderer
            if not channel_renderers:
                channel_renderers = self._find_channel_renderers(yt_data)

            logger.info(f"Found {len(channel_renderers)} potential channel renderers")

            # 解析频道信息
            for channel_item in channel_renderers:
                try:
                    channel_info = channel_item.get('channelRenderer') or channel_item.get('gridChannelRenderer')
                    if not channel_info:
                        continue

                    channel_id = channel_info.get('channelId')
                    title = channel_info.get('title', {}).get('simpleText', '')
                    thumbnail_url = None

                    # 获取头像
                    thumbnails = channel_info.get('thumbnail', {}).get('thumbnails', [])
                    if thumbnails:
                        valid_thumbnails = [
                            thumb for thumb in thumbnails
                            if isinstance(thumb, dict) and thumb.get('url')
                        ]
                        if not valid_thumbnails:
                            logger.debug('Skipping malformed YouTube channel renderer without valid thumbnails')
                            continue

                        # 选择中等大小的缩略图
                        for thumb in valid_thumbnails:
                            if thumb.get('width', 0) >= 88:
                                thumbnail_url = thumb.get('url')
                                break
                        if not thumbnail_url:
                            thumbnail_url = valid_thumbnails[0].get('url')

                    if channel_id and channel_id.startswith('UC') and title:
                        channel_url = f'https://www.youtube.com/channel/{channel_id}'
                        subscriptions.append(SubscriptionImportItem(
                            url=channel_url,
                            name=title,
                            avatar=thumbnail_url
                        ))
                except (ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
                    logger.debug('Skipping malformed YouTube channel renderer: %s', exc, exc_info=True)

            # 去重
            seen_urls = set()
            unique_subscriptions = []
            for sub in subscriptions:
                if sub.url not in seen_urls:
                    seen_urls.add(sub.url)
                    unique_subscriptions.append(sub)

            subscriptions = unique_subscriptions

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.warning(f"Error parsing subscriptions from ytInitialData: {e}", exc_info=True)

        return subscriptions

    def _find_channel_renderers(self, data: dict) -> List[dict]:
        """递归查找所有包含 channelRenderer 的项目"""
        renderers = []

        if isinstance(data, dict):
            if 'channelRenderer' in data or 'gridChannelRenderer' in data:
                renderers.append(data)
            else:
                for value in data.values():
                    renderers.extend(self._find_channel_renderers(value))
        elif isinstance(data, list):
            for item in data:
                renderers.extend(self._find_channel_renderers(item))

        return renderers

