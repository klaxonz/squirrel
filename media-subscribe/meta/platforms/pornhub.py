import random
import time
from bs4 import BeautifulSoup
from common.http_wrapper import session
from ..base import Video, Uploader

class PornhubVideo(Video):
    DOMAIN = 'pornhub.com'

    def __init__(self, url, base_info):
        super().__init__(url, base_info)

class PornhubUploader(Uploader):
    DOMAIN = 'pornhub.com'

    def __init__(self, url):
        super().__init__(url)
        self.init()

    def init(self):
        # cookies = filter_cookies_to_query_string(self.url)

        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
            # 'Cookie': cookies
        }
        req_url = self.url.replace('www', 'cn')
        response = session.get(req_url, headers=headers, timeout=20)
        response.raise_for_status()  # 检查请求是否成功
        bs4 = BeautifulSoup(response.text, 'html.parser')
        username_els = bs4.select('.userInfoBlock .usernameWrap')
        if username_els is not None and len(username_els) > 0:
            username_el = username_els[0]
            self.name = username_el.select('a')[0].text.strip()
            user_type = username_el.get('data-type')
            if user_type == 'user':
                self.id = username_el.get('data-userid')
            elif user_type == 'channel':
                self.id = username_el.get('data-channelid')
            else:
                raise Exception('Unknown user type')
            self.avatar = bs4.select('.userInfoBlock .userAvatar img')[0].get('src')
            self.tags = []
        actors = bs4.select('.pornstarsWrapper a.pstar-list-btn')
        if len(actors) > 0:
            base_url = self.url.split('/')[2]
            for actor in actors:
                self.actors.append(f'https://{base_url}{actor.get("href")}') 