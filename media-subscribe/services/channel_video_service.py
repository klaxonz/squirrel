import re
from typing import List, Tuple
from urllib.parse import quote

import cloudscraper
import phub
import requests
from bs4 import BeautifulSoup
from phub import Quality
from pytubefix import YouTube
from sqlalchemy import func
from sqlmodel import select, or_

from core.database import get_session
from model import Video, SubscriptionVideo, Subscription, VideoCreator, Creator
from model.channel import ChannelVideo
from services import download_service
from utils.cookie import filter_cookies_to_query_string
from utils.url_helper import extract_top_level_domain


class ChannelVideoService:
    def __init__(self):
        pass

    def get_video_url(self, video_id: int) -> dict:
        with get_session() as session:
            video = session.exec(select(Video).where(
                Video.video_id == video_id
            )).first()

            video_domain = extract_top_level_domain(video.video_url)

            if video_domain == 'bilibili.com':
                # Bilibili video URL fetching logic
                cookies = filter_cookies_to_query_string("https://www.bilibili.com")
                headers = {
                    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                    'Cookie': cookies
                }
                bv_id = video.video_url.split('/')[-1]
                req_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bv_id}'
                resp = requests.get(req_url, headers=headers)
                cid = resp.json()['data']['cid']
                video_url = f'https://api.bilibili.com/x/player/wbi/playurl?bvid={bv_id}&cid={cid}&fnval=144'
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
            elif video_domain == 'youtube.com':
                # YouTube video URL fetching logic
                yt = YouTube(video.video_url, use_oauth=False)
                video_stream = yt.streams.filter(progressive=False, type="video").order_by('resolution').desc().first()
                audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                return {
                    'video_url': video_stream.url if video_stream else None,
                    'audio_url': audio_stream.url if audio_stream else None,
                }
            elif video_domain == 'pornhub.com':
                client = phub.Client()
                video = client.get(video.video_url)
                video_url = video.get_direct_url(quality=Quality.BEST)
                return {
                    'video_url': video_url,
                    'audio_url': None,
                }
            elif video_domain == 'javdb.com':
                no = video.video_title.split(' ')[0]
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


    def list_channel_videos(self, query: str, subscription_id: str, category: str, sort_by: str, page: int, page_size: int) -> Tuple[
        List[dict], dict]:
        # Start with Video table and join with SubscriptionVideo
        base_query = select(Video, SubscriptionVideo).join(
            SubscriptionVideo, Video.video_id == SubscriptionVideo.video_id
        ).where(Video.video_id != '')
        
        if subscription_id:
            base_query = base_query.where(SubscriptionVideo.subscription_id == subscription_id)
        
        if query:
            base_query = base_query.where(or_(
                Video.video_title.like(f'%{query}%')
            ))
        
        # Sort by appropriate fields from Video table
        if sort_by == 'created_at':
            base_query = base_query.order_by(Video.created_at.desc())
        else:
            base_query = base_query.order_by(Video.publish_date.desc())
        
        offset = (page - 1) * page_size
        
        with get_session() as session:
            base_query = base_query.offset(offset).limit(page_size)
            results = session.exec(base_query).all()

            # Count query modifications
            s_query = select(func.count(Video.video_id)).join(
                SubscriptionVideo, Video.video_id == SubscriptionVideo.video_id
            )
            if subscription_id:
                s_query = s_query.where(SubscriptionVideo.subscription_id == subscription_id)
            if query:
                s_query = s_query.where(Video.video_title.like(f'%{query}%'))

            total_count = session.exec(s_query).one()
            # Note: Since we're using Video table now, we'll need to adjust these counts
            # or implement different logic for read/unread/liked status

            # get subscriptions
            subscription_ids = [subscription_video.subscription_id for _, subscription_video in results]
            subscriptions = session.exec(select(Subscription).where(Subscription.subscription_id.in_(subscription_ids))).all()

            # get video related creators
            video_ids = [video.video_id for video, subscription in results]
            creators = session.exec(select(Creator, VideoCreator).join(VideoCreator, Creator.creator_id == VideoCreator.creator_id).where(VideoCreator.video_id.in_(video_ids))).all()
            # group creators by video_id
            creators_dict = {}
            for creator, video_creator in creators:
                if video_creator.video_id not in creators_dict:
                    creators_dict[video_creator.video_id] = []
                creators_dict[video_creator.video_id].append(creator)

            video_list = []
            for video, subscription_video in results:
                subscription_info = next((sub for sub in subscriptions if sub.subscription_id == subscription_video.subscription_id), None)
                video_data = {
                    'id': video.video_id,
                    'video_id': video.video_id,
                    'title': video.video_title,
                    'url': video.video_url,
                    'thumbnail': video.thumbnail_url,
                    'duration': video.video_duration,
                    'uploaded_at': video.publish_date.strftime('%Y-%m-%d %H:%M:%S') if video.publish_date else None,
                    'created_at': video.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'subscriptions': [
                        {
                            'subscription_id': subscription_info.subscription_id,
                            'content_name': subscription_info.content_name,
                            'content_url': subscription_info.content_url,
                            'content_type': subscription_info.content_type,
                            "avatar_url": subscription_info.avatar_url
                        }
                    ] if subscription_info else [],
                    'actors': [creator.dict() for creator in creators_dict.get(video.video_id, [])]
                }
                video_list.append(video_data)

            counts = {
                "all": total_count,
                "read": 0,
                "unread": 0,
                "preview": 0,
                "liked": 0
            }

            return video_list, counts

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


    def download_channel_video(self, video_id: int):
        with get_session() as session:
            video = session.query(Video).filter(
                Video.video_id == video_id
            ).first()

        if not video:
            raise ValueError("Video not found")

        download_service.start(video.url, if_only_extract=False, if_subscribe=True, if_retry=False,
                               if_manual_retry=True)

    def get_video(self, id):
        with get_session() as session:
            # 获取视频基本信息
            video = session.exec(select(Video).where(Video.video_id == id)).first()
            if not video:
                return None

            # 获取订阅信息
            subscription_videos = session.exec(
                select(SubscriptionVideo).where(SubscriptionVideo.video_id == id)
            ).all()
            subscription_ids = [sv.subscription_id for sv in subscription_videos]
            
            subscriptions = session.exec(
                select(Subscription).where(Subscription.subscription_id.in_(subscription_ids))
            ).all()

            # 获取创作者信息
            creators = session.exec(
                select(Creator, VideoCreator)
                .join(VideoCreator, Creator.creator_id == VideoCreator.creator_id)
                .where(VideoCreator.video_id == id)
            ).all()

            video_data = {
                **video.dict(),
                'subscriptions': [subscription.dict() for subscription in subscriptions],
                'creators': [creator[0].dict() for creator in creators]  # creator[0] 因为查询返回的是元组 (Creator, VideoCreator)
            }

            return video_data
