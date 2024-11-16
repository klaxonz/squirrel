from typing import List, Tuple
from urllib.parse import quote

import phub
import requests
from phub import Quality
from pytubefix import YouTube
from sqlalchemy import func

from sqlmodel import select, or_, col

from core.database import get_session
from model.channel import ChannelVideo
from model.video_history import VideoHistory
from model.video_progress import VideoProgress
from services import download_service
from utils.cookie import filter_cookies_to_query_string


class ChannelVideoService:
    def __init__(self):
        pass

    def get_video_url(self, channel_id: str, video_id: str) -> dict:
        with get_session() as session:
            channel_video = session.exec(select(ChannelVideo).where(
                ChannelVideo.channel_id == channel_id,
                ChannelVideo.video_id == video_id
            )).first()

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
                yt = YouTube(f'https://youtube.com/watch?v={video_id}', use_oauth=False, allow_oauth_cache=True, use_po_token=True)
                video_stream = yt.streams.filter(progressive=False, type="video").order_by('resolution').desc().first()
                audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                return {
                    'video_url': video_stream.url if video_stream else None,
                    'audio_url': audio_stream.url if audio_stream else None,
                }
            elif channel_video.domain == 'pornhub.com':
                client = phub.Client()
                video = client.get(channel_video.url)
                video_url = video.get_direct_url(quality=Quality.BEST)
                return {
                    'video_url': video_url,
                    'audio_url': None,
                }
            return {}

    def list_channel_videos(self, query: str, channel_id: str, read_status: str, sort_by: str, page: int, page_size: int) -> Tuple[
        List[dict], dict]:
        base_query = (
            select(ChannelVideo, VideoHistory)
            .outerjoin(VideoHistory, ChannelVideo.video_id == VideoHistory.video_id)
            .where(ChannelVideo.title != '', ChannelVideo.is_disliked == 0)
        )
        
        if channel_id:
            base_query = base_query.where(or_(
                ChannelVideo.channel_id == channel_id,
                col(ChannelVideo.channel_id).like(f"{channel_id},%"),
                col(ChannelVideo.channel_id).like(f"%,{channel_id}"),
                col(ChannelVideo.channel_id).like(f"%,{channel_id},%")
            ))
        if query:
            base_query = base_query.where(or_(
                col(ChannelVideo.channel_name).like(f'%{query}%'),
                col(ChannelVideo.title).like(f'%{query}%')
            ))
        if read_status:
            if read_status == 'read':
                base_query = base_query.where(ChannelVideo.if_read == 1)
            elif read_status == 'unread':
                base_query = base_query.where(ChannelVideo.if_read == 0)

        offset = (page - 1) * page_size
        
        # 根据排序字段进行排序
        if sort_by == 'created_at':
            base_query = base_query.order_by(col(ChannelVideo.created_at).desc())
        else:  # default: uploaded_at
            base_query = base_query.order_by(col(ChannelVideo.uploaded_at).desc())
        
        with get_session() as session:
            base_query = base_query.offset(offset).limit(page_size)
            results = session.exec(base_query).all()

            s_query = select(func.count(ChannelVideo.id))
            if query:
                s_query = s_query.where(or_(
                    col(ChannelVideo.channel_name).like(f'%{query}%'),
                    col(ChannelVideo.title).like(f'%{query}%')
                ))
            if channel_id:
                s_query = s_query.where(or_(
                    ChannelVideo.channel_id == channel_id,
                    col(ChannelVideo.channel_id).like(f"{channel_id},%"),
                    col(ChannelVideo.channel_id).like(f"%,{channel_id}"),
                    col(ChannelVideo.channel_id).like(f"%,{channel_id},%")
                ))
            total_count = session.exec(s_query).one()
            read_count = session.exec(s_query.where(ChannelVideo.if_read == 1)).one()
            unread_count = total_count - read_count

            channel_video_convert_list = []
            for cv, history in results:
                video_data = {
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
                    'created_at': cv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'last_position': history.last_position if history else 0,
                    'total_duration': history.total_duration if history else cv.duration,
                    'watch_duration': history.watch_duration if history else 0,
                }
                channel_video_convert_list.append(video_data)

            counts = {
                "all": total_count,
                "read": read_count,
                "unread": unread_count
            }

            return channel_video_convert_list, counts

    def mark_video_read(self, channel_id: str, video_id: str, is_read: bool):
        with get_session() as session:
            session.query(ChannelVideo).filter(
                ChannelVideo.channel_id == channel_id,
                ChannelVideo.video_id == video_id
            ).update({"if_read": is_read})
            session.commit()

    def mark_videos_read_batch(self, channel_id: str, direction: str, uploaded_at: str, is_read: bool):
        with get_session() as session:
            query = session.query(ChannelVideo)
            if channel_id:
                query = query.filter(ChannelVideo.channel_id == channel_id)
            if direction == 'above':
                query = query.filter(ChannelVideo.uploaded_at >= uploaded_at)
            elif direction == 'below':
                query = query.filter(ChannelVideo.uploaded_at <= uploaded_at)
            query.update({"if_read": is_read})
            session.commit()

    def save_video_progress(self, channel_id: str, video_id: str, progress: float):
        with get_session() as session:
            video_progress = session.query(VideoProgress).filter_by(
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
                session.add(video_progress)
            session.commit()

    def get_video_progress(self, channel_id: str, video_id: str) -> float:
        with get_session() as session:
            video_progress = session.query(VideoProgress).filter_by(
                channel_id=channel_id, video_id=video_id
            ).first()
            return video_progress.progress if video_progress else 0

    def dislike_video(self, channel_id: str, video_id: str):
        with get_session() as session:
            video = session.query(ChannelVideo).filter(
                ChannelVideo.channel_id == channel_id,
                ChannelVideo.video_id == video_id
            ).first()
            if video:
                video.is_disliked = True
                session.commit()
                return True
            return False

    def download_channel_video(self, channel_id: str, video_id: str):
        with get_session() as session:
            channel_video = session.query(ChannelVideo).filter(
                ChannelVideo.channel_id == channel_id,
                ChannelVideo.video_id == video_id
            ).first()

        if not channel_video:
            raise ValueError("Channel video not found")

        download_service.start(channel_video.url, if_only_extract=False, if_subscribe=True, if_retry=False,
                               if_manual_retry=True)
