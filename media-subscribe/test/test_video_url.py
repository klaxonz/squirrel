import json

import requests
from pytubefix import YouTube, Channel as YouTubeChannel

from common.cookie import filter_cookies_to_query_string
from downloader.downloader import Downloader
from model.channel import Channel
from subscribe.subscribe import SubscribeChannelFactory

# yt = YouTube('https://youtube.com/watch?v=GxQC3pqoA9Y', use_oauth=True, allow_oauth_cache=True,)
# print(yt.title)
# print(yt.streaming_data)

# c = Channel('https://www.youtube.com/channel/UCsRM0YB_dabtEPGPTKo-gcw')
# for url in c.video_urls:
#     print(url)

# url = 'https://www.bilibili.com/video/BV1nBWeeEEiB'
# cookies = filter_cookies_to_query_string(url)
# headers = {
#     'Referer': url,
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
#                   'Chrome/58.0.3029.110 Safari/537.3',
#     'Cookie': cookies
# }
#
# response = requests.get(url, headers=headers)
# print(response.text)

url = 'https://space.bilibili.com/416878454'
subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(url)
channel_info = subscribe_channel.get_channel_info()

channel = Channel()
channel.channel_id = channel_info.id
channel.name = channel_info.name
channel.url = channel_info.url
channel.avatar = channel_info.avatar
channel.if_extract_all = 1
videos = subscribe_channel.get_channel_videos(channel, update_all=True)
channel.total_videos = len(videos)
print(videos)