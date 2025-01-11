import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from common.http_wrapper import session
from meta.channel import SubscriptionMeta
from utils.cookie import filter_cookies_to_query_string
from ..base import BaseSubscription


class PornhubSubscription(BaseSubscription):
    DOMAIN = 'pornhub.com'

    def get_subscribe_info(self):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }
        response = session.get(self.url, headers=headers, timeout=15)
        response.raise_for_status()

        bs4 = BeautifulSoup(response.text, 'html.parser')
        channel_els = bs4.select('#channelsProfile .title > h1')

        if len(channel_els) > 0:
            name = channel_els[0].text.strip()
            subscribe_url = bs4.select('button[data-subscribe-url]')[0].get('data-subscribe-url')
            channel_id = re.search(r"id=([^&]+)", subscribe_url).group(1)
        else:
            channel_id = None
            name_el = bs4.select('.nameSubscribe .name h1')
            if len(name_el) == 0:
                raise Exception(f'Can not find channel name in {self.url}')

            name = name_el[0].text.strip()
            add_friend_btn = bs4.select('.addFriendButton button[data-friend-url]')
            if len(add_friend_btn) > 0:
                channel_id = add_friend_btn[0].get('data-id')
            if channel_id is None:
                subscribe_btn = bs4.select('.subscribeButton button[data-subscribe-url]')
                if len(subscribe_btn) > 0:
                    channel_id = re.search(r"id=([^&]+)", subscribe_btn[0].get('data-subscribe-url')).group(1)

        url = re.search(r"^(.*?)(\?.*)?$", self.url).group(1)
        avatar = None
        avatar_els = bs4.select('#getAvatar')
        if len(avatar_els) > 0:
            avatar = avatar_els[0].get('src')
        if avatar is None:
            avatar_els = bs4.select('.topProfileHeader .thumbImage img')
            if len(avatar_els) > 0:
                avatar = avatar_els[0].get('src')

        return SubscriptionMeta(channel_id, name, avatar, url)

    def get_subscribe_videos(self, extract_all: bool):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }

        if 'pornhub.com/model' in self.url or 'pornhub.com/pornstar' in self.url:
            self.url = self.url + '/videos'

        response = session.get(self.url, headers=headers, timeout=15)
        if response.status_code == 404:
            self.url = self.url.replace('/videos', '')
            response = session.get(self.url, headers=headers, timeout=15)
        response.raise_for_status()

        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        video_list = []
        bs4 = BeautifulSoup(response.text, 'html.parser')
        page_next_list = bs4.select('.page_next')
        page = int(bs4.select('.page_next')[0].find_previous().text) if len(page_next_list) > 0 else 1
        current_page = 1

        while True:
            response = session.get(self.url + f'?page={current_page}', headers=headers, timeout=15)
            response.raise_for_status()
            bs4 = BeautifulSoup(response.text, 'html.parser')
            video_els = []
            video_els.extend(bs4.select('#channelsProfile .videos a.videoPreviewBg'))
            video_els.extend(bs4.select('#profileContent .videos:not(#privateVideosSection) a.videoPreviewBg'))
            video_els.extend(bs4.select('#pornstarsVideoSection .videoPreviewBg'))
            for el in video_els:
                video_list.append(f'{base_url}{el["href"]}')

            new_page = int(bs4.select('.page_next')[0].find_previous().text) if len(page_next_list) > 0 else 1

            if new_page > page:
                page = new_page
            if current_page == page:
                break
            if not extract_all:
                break
            current_page += 1

        return video_list
