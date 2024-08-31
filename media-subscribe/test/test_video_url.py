import json

from pytubefix import YouTube, Channel

from downloader.downloader import Downloader

# yt = YouTube('https://youtube.com/watch?v=GxQC3pqoA9Y', use_oauth=True, allow_oauth_cache=True,)
# print(yt.title)
# print(yt.streaming_data)

# c = Channel('https://www.youtube.com/@ClubZeroMedia/videos')
# for url in c.video_urls:
#     print(url)

info = Downloader.get_video_info('https://youtube.com/watch?v=GxQC3pqoA9Y')
print(json.dumps(info, indent=4))
