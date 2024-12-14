import random
import re
import time
from bs4 import BeautifulSoup
from common.http_wrapper import session
from utils.cookie import filter_cookies_to_query_string
from ..base import Video, Uploader

class JavVideo(Video):
    DOMAIN = 'javdb.com'
    def __init__(self, url, base_info):
        super().__init__(url, base_info)

class JavUploader(Uploader):
    DOMAIN = 'javdb.com'

    def __init__(self, url):
        super().__init__(url)
        self.init()

    def init(self):
        cookies = filter_cookies_to_query_string(self.url)

        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }
        response = session.get(self.url, headers=headers, timeout=20)
        response.raise_for_status()
        bs4 = BeautifulSoup(response.text, 'html.parser')

        if 'javdb.com/v/' in self.url:
            els = bs4.select('.movie-panel-info .panel-block')
            for el in els:
                if '演员' in el.text or '演員' in el.text:
                    self.url = 'https://javdb.com' + el.select('a:nth-of-type(1)')[0].get('href')
                    response = session.get(self.url, headers=headers, timeout=20)
                    response.raise_for_status()
                    bs4 = BeautifulSoup(response.text, 'html.parser')
                    break

        username_el = bs4.select('.actor-section-name')
        if len(username_el) > 0:
            self.name = username_el[0].text.strip().split(',')[0]
            avatar_el = bs4.select('.avatar')[0]
            style = avatar_el['style']
            self.avatar = re.search(r'url\((.*?)\)', style).group(1)
            self.id = self.url.split('/')[-1]
            self.tags = []