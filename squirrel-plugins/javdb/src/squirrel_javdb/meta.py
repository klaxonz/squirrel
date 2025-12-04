from __future__ import annotations

import re

from bs4 import BeautifulSoup

from crawl import Video, Actor, register_meta
from .browser_utils import fetch_page_html


@register_meta
class JavdbVideo(Video):
    domain = 'javdb.com'

    @property
    def actors(self):
        if len(self._actors) == 0:
            html = fetch_page_html(self.url)  # type: ignore
            soup = BeautifulSoup(html, 'html.parser')

            blocks = soup.select('.movie-panel-info .panel-block')
            for block in blocks:
                if '演员' in block.text or '演員' in block.text:
                    for actor_el in block.select('a'):
                        actor_url = 'https://javdb.com' + actor_el.get('href')
                        actor_html = fetch_page_html(actor_url)  # type: ignore
                        actor_soup = BeautifulSoup(actor_html, 'html.parser')
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
