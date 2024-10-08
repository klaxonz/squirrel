from typing import List, Tuple
from urllib.parse import quote

import requests
from pytubefix import YouTube
from sqlalchemy import or_, func, Column
from sqlalchemy.orm import Session

from common.cookie import filter_cookies_to_query_string
from model.channel import ChannelVideo
from model.video_progress import VideoProgress
from service import download_service


class ChannelVideoService:
    def __init__(self, db: Session):
        self.db = db

    def get_video_url(self, channel_id: str, video_id: str) -> dict:
        channel_video = self.db.query(ChannelVideo).filter(
            ChannelVideo.channel_id == channel_id,
            ChannelVideo.video_id == video_id
        ).first()

        if channel_video.domain == 'bilibili.com':
            # Bilibili video URL fetching logic
            cookies = filter_cookies_to_query_string("https://www.bilibili.com")
            headers = {
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Cookie': cookies
            }
            req_url = f'https://api.bilibili.com/x/web-interface/view?bvid={video_id}'
            resp = requests.get(req_url, headers=headers)
            cid = resp.json()['data']['cid']
            video_url = f'https://api.bilibili.com/x/player/wbi/playurl?bvid={video_id}&cid={cid}&fnval=144'
            resp = requests.get(video_url, headers=headers)
            data = resp.json()['data']
            video_urls = data['dash']['video']
            best_video_url = max(video_urls, key=lambda x: x['bandwidth'])['baseUrl']
            audio_urls = data['dash']['audio']
            best_audio_url = max(audio_urls, key=lambda x: x['bandwidth'])['baseUrl']
            return {
                'video_url': "http://localhost:8000/api/channel-video/proxy?url=" + quote(best_video_url),
                'audio_url': "http://localhost:8000/api/channel-video/proxy?url=" + quote(best_audio_url),
            }
        elif channel_video.domain == 'youtube.com':
            # YouTube video URL fetching logic
            yt = YouTube(f'https://youtube.com/watch?v={video_id}', use_oauth=True, allow_oauth_cache=True)
            video_stream = yt.streams.filter(progressive=False, type="video").order_by('resolution').desc().first()
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            return {
                'video_url': video_stream.url if video_stream else None,
                'audio_url': audio_stream.url if audio_stream else None,
            }
        return {}

    def list_channel_videos(self, query: str, channel_id: str, read_status: str, page: int, page_size: int) -> Tuple[
        List[dict], dict]:
        base_query = self.db.query(ChannelVideo).filter(ChannelVideo.title != '', ChannelVideo.is_disliked == 0)
        if channel_id:
            base_query = base_query.filter(ChannelVideo.channel_id == channel_id)
        if query:
            base_query = base_query.filter(or_(
                func.lower(ChannelVideo.channel_name).like(func.lower(f'%{query}%')),
                func.lower(ChannelVideo.title).like(func.lower(f'%{query}%'))
            ))
        if read_status:
            if read_status == 'read':
                base_query = base_query.filter(ChannelVideo.if_read is True)
            elif read_status == 'unread':
                base_query = base_query.filter(ChannelVideo.if_read is False)

        offset = (page - 1) * page_size
        channel_videos = base_query.order_by(Column(ChannelVideo.uploaded_at).desc()).offset(offset).limit(page_size)

        s_query = self.db.query(ChannelVideo)
        if channel_id:
            s_query = s_query.filter(ChannelVideo.channel_id == channel_id)
        total_count = s_query.count()
        read_count = s_query.filter(ChannelVideo.if_read is True).count()
        unread_count = total_count - read_count

        channel_video_convert_list = [{
            'id': cv.id,
            'channel_id': cv.channel_id,
            'channel_name': cv.channel_name,
            'channel_avatar': cv.channel_avatar,
            'video_id': cv.video_id,
            'title': cv.title,
            'domain': cv.domain,
            'url': cv.url,
            'thumbnail': cv.thumbnail,
            'duration': cv.duration,
            'if_downloaded': cv.if_downloaded,
            'if_read': cv.if_read,
            'uploaded_at': cv.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
            'created_at': cv.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for cv in channel_videos]

        counts = {
            "all": total_count,
            "read": read_count,
            "unread": unread_count
        }

        return channel_video_convert_list, counts

    def mark_video_read(self, channel_id: str, video_id: str, is_read: bool):
        self.db.query(ChannelVideo).filter(
            ChannelVideo.channel_id == channel_id,
            ChannelVideo.video_id == video_id
        ).update({"if_read": is_read})
        self.db.commit()

    def mark_videos_read_batch(self, channel_id: str, direction: str, uploaded_at: str, is_read: bool):
        query = self.db.query(ChannelVideo)
        if channel_id:
            query = query.filter(ChannelVideo.channel_id == channel_id)
        if direction == 'above':
            query = query.filter(ChannelVideo.uploaded_at >= uploaded_at)
        elif direction == 'below':
            query = query.filter(ChannelVideo.uploaded_at <= uploaded_at)
        query.update({"if_read": is_read})
        self.db.commit()

    def save_video_progress(self, channel_id: str, video_id: str, progress: float):
        video_progress = self.db.query(VideoProgress).filter_by(
            channel_id=channel_id, video_id=video_id
        ).first()
        if video_progress:
            video_progress.progress = progress
        else:
            video_progress = VideoProgress(
                channel_id=channel_id,
                video_id=video_id,
                progress=progress
            )
            self.db.add(video_progress)
        self.db.commit()

    def get_video_progress(self, channel_id: str, video_id: str) -> float:
        video_progress = self.db.query(VideoProgress).filter_by(
            channel_id=channel_id, video_id=video_id
        ).first()
        return video_progress.progress if video_progress else 0

    def dislike_video(self, channel_id: str, video_id: str):
        video = self.db.query(ChannelVideo).filter(
            ChannelVideo.channel_id == channel_id,
            ChannelVideo.video_id == video_id
        ).first()
        if video:
            video.is_disliked = True
            self.db.commit()
            return True
        return False

    def download_channel_video(self, channel_id: str, video_id: str):
        channel_video = self.db.query(ChannelVideo).filter(
            ChannelVideo.channel_id == channel_id,
            ChannelVideo.video_id == video_id
        ).first()

        if not channel_video:
            raise ValueError("Channel video not found")

        download_service.start(channel_video.url, if_only_extract=False, if_subscribe=True, if_retry=False,
                               if_manual_retry=True)
