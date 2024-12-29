from bs4 import BeautifulSoup
from common.http_wrapper import session

from ..base import Video, Actor


class PornhubVideo(Video):
    DOMAIN = 'pornhub.com'

    def __init__(self, url, base_info):
        super().__init__(url, base_info)

    @property
    def actors(self):
        if len(self._actors) == 0:
            headers = {
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/124.0.0.0 Safari/537.36',
            }
            response = session.get(self.url, headers=headers, timeout=20)
            response.raise_for_status()
            bs4 = BeautifulSoup(response.text, 'html.parser')
            username_els = bs4.select('.userInfoBlock .usernameWrap')

            base_url = self.url.split('/')[2]
            if username_els is not None and len(username_els) > 0:
                username_el = username_els[0]
                actor_name = username_el.select('a')[0].text.strip()
                actor_avatar = bs4.select('.userInfoBlock .userAvatar img')[0].get('src')
                actor_url = f'https://{base_url}{username_el.select("a")[0].get("href")}'
                actor = Actor(actor_url)
                actor.name = actor_name
                actor.avatar = actor_avatar
                self._actors.append(actor)

            actor_els = bs4.select('.pornstarsWrapper a.pstar-list-btn')
            if len(actor_els) > 0:
                base_url = self.url.split('/')[2]
                for actor_el in actor_els:
                    actor_url = f'https://{base_url}{actor_el.get("href")}'
                    actor = Actor(actor_url)
                    actor.name = actor_el.text.strip()
                    actor.avatar = actor_el.select('img')[0].get('src')
                    self._actors.append(actor)

        return self._actors

