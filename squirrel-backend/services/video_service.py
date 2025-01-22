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
from sqlalchemy import func, select, or_

from core.database import get_session
from dto.video_dto import VideoExtractDto
from models.creator import Creator
from models.links import VideoCreator, SubscriptionVideo
from models.subscription import Subscription
from models.video import Video
from services import download_service, subscription_video_service
from utils import url_helper
from utils.cookie import filter_cookies_to_query_string
from utils.url_helper import extract_top_level_domain


def get_video_by_url(url: str) -> Video:
    with get_session() as session:
        video = session.scalars(select(Video).where(Video.url == url)).first()
        return video


def get_video_by_id(video_id: int) -> Video:
    with get_session() as session:
        video = session.get(Video, video_id)
        return video


def create_video(url: str, title: str, publish_date: datetime, thumbnail: str, duration: int) -> Video:
    with get_session() as session:
        video = Video()
        video.url = url
        video.title = title
        video.publish_date = publish_date
        video.thumbnail = thumbnail
        video.duration = duration
        session.add(video)
        session.commit()
        return video


def get_video_url(video_id: int) -> dict:
    with get_session() as session:
        video = session.get(Video, video_id)
        video_domain = extract_top_level_domain(video.url)

        if video_domain == 'bilibili.com':
            # Bilibili video URL fetching logic
            cookies = filter_cookies_to_query_string("https://www.bilibili.com")
            headers = {
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Cookie': cookies
            }
            bv_id = video.url.split('/')[-1]
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
                'video_url': "/api/video/proxy?domain=bilibili.com&url=" + quote(best_video_url),
                'audio_url': "/api/video/proxy?domain=bilibili.com&url=" + quote(best_audio_url),
            }
        elif video_domain == 'youtube.com':
            # YouTube video URL fetching logic
            yt = YouTube(video.url, use_oauth=False)
            video_stream = yt.streams.filter(progressive=False, type="video").order_by('resolution').desc().first()
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            return {
                'video_url': video_stream.url if video_stream else None,
                'audio_url': audio_stream.url if audio_stream else None,
            }
        elif video_domain == 'pornhub.com':
            client = phub.Client()
            video = client.get(video.url)
            video_url = video.get_direct_url(quality=Quality.BEST)
            return {
                'video_url': video_url,
                'audio_url': None,
            }
        elif video_domain == 'javdb.com':
            no = video.title.split(' ')[0]
            url = get_jav_video_url(no)
            return {
                'video_url': "/api/video/proxy?domain=javdb.com&url=" + quote(url),
                'audio_url': None,
            }
        return {}


def get_jav_video_url(no: str):
    url = f'https://missav.ai/search/{no}'
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url)
    bs4 = BeautifulSoup(response.text, 'html.parser')
    items = bs4.select('div.thumbnail')
    if len(items) > 0:
        target = items[0]
        target_url = target.select_one('a')['href']

        response = scraper.get(target_url)
        r = extract_parts_from_html_content(response.text)
        url_path = r.split("m3u8|")[1].split("|playlist|source")[0]
        url_words = url_path.split('|')
        video_index = url_words.index("video")
        protocol = url_words[video_index - 1]
        video_format = url_words[video_index + 1]

        m3u8_url_path = "-".join((url_words[0:5])[::-1])
        base_url_path = ".".join((url_words[5:video_index - 1])[::-1])

        formatted_url = "{0}://{1}/{2}/{3}/{4}.m3u8".format(protocol, base_url_path, m3u8_url_path, video_format,
                                                            url_words[video_index])
        return formatted_url


def extract_parts_from_html_content(html_content):
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


def list_videos(query: str, subscription_id: int, category: str, sort_by: str, page: int, page_size: int) -> \
        Tuple[
            List[dict], int, dict]:
    base_query = (
        select(Video, SubscriptionVideo)
        .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
        .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
        .where(Subscription.is_deleted == 0)
    )
    if category == 'preview':
        base_query = base_query.where(Video.publish_date > datetime.now())
    else:
        base_query = base_query.where(Video.publish_date <= datetime.now())
    if subscription_id:
        base_query = base_query.where(SubscriptionVideo.subscription_id == subscription_id)
    if query:
        base_query = base_query.where(or_(Video.title.like(f'%{query}%')))
    # Sort by appropriate fields from Video table
    if sort_by == 'created_at':
        base_query = base_query.order_by(Video.created_at.desc())
    else:
        base_query = base_query.order_by(Video.publish_date.desc())

    offset = (page - 1) * page_size

    with (get_session() as session):
        base_query = base_query.offset(offset).limit(page_size)
        results = session.execute(base_query).all()
        # Count query modifications
        total_count_query = (
            select(func.count(Video.id))
            .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
            .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
            .where(Subscription.is_deleted == 0)
        )
        preview_query = total_count_query.where(Video.publish_date > datetime.now())
        if subscription_id:
            total_count_query = total_count_query.where(SubscriptionVideo.subscription_id == subscription_id)
            preview_query = preview_query.where(SubscriptionVideo.subscription_id == subscription_id)
        if query:
            total_count_query = total_count_query.where(Video.title.like(f'%{query}%'))

        total_count = session.scalar(total_count_query)
        total_preview_count = session.scalar(preview_query)
        # Note: Since we're using Video table now, we'll need to adjust these counts
        # or implement different logic for read/unread/liked status

        # get subscriptions
        subscription_ids = list(set(subscription_video.subscription_id for _, subscription_video in results))
        subscriptions = session.query(Subscription).filter(Subscription.id.in_(subscription_ids)).all()

        # get video related creators
        video_ids = [video.id for video, subscription in results]
        creators = session.execute(select(Creator, VideoCreator)
                                   .join(VideoCreator, Creator.id == VideoCreator.creator_id)
                                   .where(VideoCreator.video_id.in_(video_ids))).all()
        # group creators by id
        creators_dict = {}
        for creator, video_creator in creators:
            if video_creator.video_id not in creators_dict:
                creators_dict[video_creator.video_id] = []
            creators_dict[video_creator.video_id].append(creator)

        video_list = []
        for video, subscription_video in results:
            subscription_info = next((sub for sub in subscriptions if sub.id == subscription_video.subscription_id),
                                     None)
            video_data = {
                'id': video.id,
                'title': video.title,
                'url': video.url,
                'thumbnail': video.thumbnail,
                'duration': video.duration,
                'uploaded_at': video.publish_date.strftime('%Y-%m-%d %H:%M:%S') if video.publish_date else None,
                'created_at': video.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'subscriptions': [
                    {
                        'id': subscription_info.id,
                        'name': subscription_info.name,
                        'url': subscription_info.url,
                        'type': subscription_info.type,
                        "avatar": subscription_info.avatar
                    }
                ] if subscription_info else [],
                'actors': [creator.to_dict() for creator in creators_dict.get(video.id, [])]
            }
            video_list.append(video_data)

        counts = {
            "all": total_count,
            "read": 0,
            "unread": 0,
            "preview": total_preview_count,
            "liked": 0
        }

        return video_list, total_count, counts


def download_video(video_id: int):
    video = get_video_by_id(video_id)
    subscription_video = subscription_video_service.get_subscription_video_by_video_id(video_id)
    if not video:
        raise ValueError("Video not found")
    params = VideoExtractDto(
        url=video.url,
        only_extract=False,
        subscribed=True,
        subscription_id=subscription_video.subscription_id
    )
    download_service.start(params)


def get_video(video_id):
    with get_session() as session:
        video = session.scalars(select(Video).where(Video.id == video_id)).first()
        if not video:
            return None

        subscription_videos = session.scalars(
            select(SubscriptionVideo).where(SubscriptionVideo.video_id == video_id)
        ).all()
        subscriptions = session.scalars(
            select(Subscription).where(Subscription.id.in_([sv.subscription_id for sv in subscription_videos]))
        ).all()

        creators = session.scalars(
            select(Creator, VideoCreator)
            .join(VideoCreator, Creator.id == VideoCreator.creator_id)
            .where(VideoCreator.video_id == video_id)
        ).all()

        video_data = {
            **video.to_dict(),
            'domain': url_helper.extract_top_level_domain(video.url),
            'subscriptions': [subscription.to_dict() for subscription in subscriptions],
            'creators': [creator.to_dict() for creator in creators]
        }

        return video_data
