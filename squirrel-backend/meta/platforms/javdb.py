import re
from bs4 import BeautifulSoup
from common.http_wrapper import session
from utils.cookie import filter_cookies_to_query_string
from ..base import Video, Actor


class JavVideo(Video):
    DOMAIN = 'javdb.com'

    def __init__(self, url, base_info):
        super().__init__(url, base_info)

    @property
    def actors(self):
        if len(self._actors) == 0:
            cookies = filter_cookies_to_query_string(self.url)

            headers = {
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/124.0.0.0 Safari/537.36',
                'Cookie': cookies
            }
            response = session.get(self.url, headers=headers, timeout=20)
            response.raise_for_status()
            bs4 = BeautifulSoup(response.text, 'html.parser')

            els = bs4.select('.movie-panel-info .panel-block')
            for el in els:
                if '演员' in el.text or '演員' in el.text:
                    actor_els = el.select('a')
                    for actor_el in actor_els:
                        actor_url = 'https://javdb.com' + actor_el.get('href')
                        response = session.get(actor_url, headers=headers, timeout=20)
                        response.raise_for_status()
                        bs4 = BeautifulSoup(response.text, 'html.parser')
                        username_el = bs4.select('.actor-section-name')
                        actor_name = username_el[0].text.strip().split(',')[0]
                        avatar_el = bs4.select('.avatar')
                        actor_avatar = None
                        if len(avatar_el) > 0:
                            actor_avatar = re.search(r'url\((.*?)\)',  avatar_el[0]['style']).group(1)
                        actor = Actor(actor_url)
                        actor.name = actor_name
                        actor.avatar = actor_avatar
                        self._actors.append(actor)
        return self._actors

