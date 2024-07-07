import json
import logging
from datetime import datetime

from common.database import get_session
from consumer.base import BaseConsumerThread
from downloader.downloader import Downloader
from model.channel import ChannelVideo, Channel, ChannelVideoSchema
from service import download_service

logger = logging.getLogger(__name__)


class ExtractorChannelVideoConsumerThread(BaseConsumerThread):
    def run(self):
        while self.running:
            try:
                with get_session() as session:
                    message = self.mq.wait_and_dequeue(session=session, timeout=None)
                    if message:
                        self.handle_message(message, session)

                        channel_video = ChannelVideoSchema().load(json.loads(message.body), session=session)
                        channel = session.query(Channel).where(Channel.channel_id == channel_video.channel_id).first()

                        if channel.if_auto_download:
                            if channel_video.if_downloaded:
                                continue
                        else:
                            continue

                        video_info = Downloader.get_video_info(channel_video.url)
                        if video_info is None:
                            logger.info(f"{channel_video.url} is not a video, skip")
                            continue
                        if '_type' in video_info and video_info['_type'] == 'playlist':
                            logger.info(f"{channel_video.url} is a playlist, skip")
                            continue

                        uploaded_time = datetime.fromtimestamp(int(video_info['timestamp']))
                        thumbnail = video_info['thumbnail']

                        session.query(ChannelVideo).where(ChannelVideo.channel_id == channel_video.channel_id, ChannelVideo.video_id == channel_video.video_id).update({
                            ChannelVideo.title: video_info['title'],
                            ChannelVideo.thumbnail: thumbnail,
                            ChannelVideo.uploaded_at: uploaded_time
                        })
                        session.commit()

                        if channel.if_auto_download:
                            download_service.start_download(channel_video.url)
                            session.query(ChannelVideo).where(ChannelVideo.video_id == channel_video.video_id, ChannelVideo.channel_id == channel_video.channel_id).update({
                                ChannelVideo.if_downloaded: True
                            })
                            session.commit()

            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)
