from __future__ import annotations

import re

from bs4 import BeautifulSoup

from crawl import Video, Actor, register_meta, filter_cookies_to_query_string, request


@register_meta
class JavdbVideo(Video):
    domain = 'javdb.com'

    @property
    def actors(self):
        if len(self._actors) == 0:
            cookies = filter_cookies_to_query_string(self.url)
            headers = {
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Cookie': cookies,
            }
            response = request('GET', self.url, headers=headers, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            blocks = soup.select('.movie-panel-info .panel-block')
            for block in blocks:
                if '演员' in block.text or '演員' in block.text:
                    for actor_el in block.select('a'):
                        actor_url = 'https://javdb.com' + actor_el.get('href')
                        actor_resp = request('GET', actor_url, headers=headers, timeout=20)
                        actor_resp.raise_for_status()
                        actor_soup = BeautifulSoup(actor_resp.text, 'html.parser')
                        name_el = actor_soup.select('.actor-section-name')
                        actor_name = name_el[0].text.strip().split(',')[0]
                        avatar_el = actor_soup.select('.avatar')
                        actor_avatar = None
                        if avatar_el:
                            match = re.search(r'url\((.*?)\)', avatar_el[0]['style'])
                            actor_avatar = match.group(1) if match else None
                        actor = Actor(actor_url)
                        actor.name = actor_name
                        actor.avatar = actor_avatar
                        self._actors.append(actor)
        return self._actors
