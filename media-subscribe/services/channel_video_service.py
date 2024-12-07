import re
from datetime import datetime
from typing import List, Tuple
from urllib.parse import quote

import cloudscraper
import phub
import requests
from bs4 import BeautifulSoup
from phub import Quality
from pytubefix import YouTube
from sqlalchemy import func

from sqlmodel import select, or_, col

from core.database import get_session
from model.channel import ChannelVideo
from model.video_history import VideoHistory
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
                    'video_url': "/api/channel-video/proxy?domain=bilibili.com&url=" + quote(best_video_url),
                    'audio_url': "/api/channel-video/proxy?domain=bilibili.com&url=" + quote(best_audio_url),
                }
            elif channel_video.domain == 'youtube.com':
                # YouTube video URL fetching logic
                yt = YouTube(f'https://youtube.com/watch?v={video_id}', use_oauth=False)
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
            elif channel_video.domain == 'javdb.com':
                title = channel_video.title
                no = title.split(' ')[0]
                url = self.get_jav_video_url(no)
                return {
                    'video_url': "/api/channel-video/proxy?domain=javdb.com&url=" + quote(url),
                    'audio_url': None,
                }
            return {}


    def get_jav_video_url(self, no: str):
        url = f'https://missav.com/search/{no}'
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)
        bs4 = BeautifulSoup(response.text, 'html.parser')
        items = bs4.select('div.thumbnail')
        if len(items) > 0:
            target = items[0]
            target_url = target.select_one('a')['href']

            response = scraper.get(target_url)
            r = self.extract_parts_from_html_content(response.text)
            url_path = r.split("m3u8|")[1].split("|playlist|source")[0]
            url_words = url_path.split('|')
            video_index = url_words.index("video")
            protocol = url_words[video_index-1]
            video_format = url_words[video_index + 1]

            m3u8_url_path = "-".join((url_words[0:5])[::-1])
            base_url_path = ".".join((url_words[5:video_index-1])[::-1])

            formatted_url = "{0}://{1}/{2}/{3}/{4}.m3u8".format(protocol, base_url_path, m3u8_url_path, video_format, url_words[video_index])
            return formatted_url

    def extract_parts_from_html_content(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')

        # 查找所有script标签
        for script in soup.find_all('script'):
            if script.string and 'm3u8|' in script.string:
                # 找到包含目标字符串的部分
                pattern = r"'([^']*m3u8\|[^']*)'"
                match = re.search(pattern, script.string)
                if match:
                    parts = match.group(1)
                    return parts
        return None

    def list_channel_videos(self, query: str, channel_id: str, read_status: str, sort_by: str, page: int, page_size: int) -> Tuple[
        List[dict], dict]:
        base_query = select(ChannelVideo).where(ChannelVideo.title != '')
        
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
        if read_status == 'preview':
            base_query = base_query.where(ChannelVideo.uploaded_at > datetime.now())
        else:
            base_query = base_query.where(ChannelVideo.uploaded_at <= datetime.now())

        if read_status:
            if read_status == 'read':
                base_query = base_query.where(ChannelVideo.if_read == 1)
            elif read_status == 'unread':
                base_query = base_query.where(ChannelVideo.if_read == 0)
            elif read_status == 'liked':
                base_query = base_query.where(ChannelVideo.is_liked == 1)
            
        offset = (page - 1) * page_size
        
        # 根据排序字段进行排序
        if sort_by == 'created_at':
            base_query = base_query.order_by(col(ChannelVideo.created_at).desc())
        else:
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
            total_count = session.exec(s_query.where(ChannelVideo.uploaded_at <= datetime.now())).one()
            read_count = session.exec(s_query.where(ChannelVideo.if_read == 1, ChannelVideo.uploaded_at <= datetime.now())).one()
            unread_count = total_count - read_count
            preview_count = session.exec(s_query.where(ChannelVideo.uploaded_at > datetime.now())).one()
            liked_count = session.exec(s_query.where(ChannelVideo.is_liked == 1)).one()

            channel_video_convert_list = []

            video_ids = [cv.video_id for cv in results]
            history_list = session.exec(select(VideoHistory).where(VideoHistory.video_id.in_(video_ids))).all()
            history_dict = {h.video_id: h for h in history_list}

            for cv in results:
                history = history_dict.get(cv.video_id)
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
                    'is_liked': cv.is_liked,
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
                "unread": unread_count,
                "preview": preview_count,
                "liked": liked_count
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

    def toggle_like_video(self, channel_id: str, video_id: str, is_liked: bool):
        with get_session() as session:
            video = session.query(ChannelVideo).filter(
                ChannelVideo.channel_id == channel_id,
                ChannelVideo.video_id == video_id
            ).first()
            if video:
                video.is_liked = is_liked
                session.commit()


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

    def get_video(self, channel_id, video_id):
        with get_session() as session:
            video = session.query(ChannelVideo).filter(ChannelVideo.channel_id == channel_id, ChannelVideo.video_id == video_id)
            return video.first()
