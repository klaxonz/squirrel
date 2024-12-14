import random
import time
from pytubefix import YouTube
from ..base import Video, Uploader

class YoutubeVideo(Video):
    DOMAIN = 'youtube.com'

    def __init__(self, url, base_info):
        super().__init__(url, base_info)

class YoutubeUploader(Uploader):
    DOMAIN = 'youtube.com'


    def __init__(self, url):
        super().__init__(url)
        self.init()

    def init(self):
        video = YouTube(self.url, use_oauth=False, allow_oauth_cache=False)
        self.id = video.channel_id
        self.name = video.author
        self.avatar = video.thumbnail_url
        self.tags = []
        time.sleep(random.uniform(3, 5)) 