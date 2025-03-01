import json
import re
import subprocess
from datetime import datetime
from typing import List, Tuple
from urllib.parse import quote

import cloudscraper
import phub
import requests
from bs4 import BeautifulSoup
from phub import Quality
from pytubefix import YouTube
from sqlalchemy import select, text

from core.database import get_session
from dto.video_dto import VideoExtractDto, VideoDto, VideoCountDto
from models.creator import Creator
from models.links import VideoCreator, SubscriptionVideo
from models.subscription import Subscription
from models.video import Video
from services import download_service, subscription_video_service, user_config_service, video_history_service, \
    video_interaction_service
from sqlfile.video_sql import get_videos_sql, count_videos_sql, count_like_videos_sql
from utils import url_helper, sql_parser
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

        proxy_prefix_path = f"/api/video/proxy?domain={video_domain}"

        if video_domain == 'bilibili.com':
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
            best_video_url = None
            best_audio_url = None
            if 'dash' in data:
                dash_data = data['dash']
                if 'video' in dash_data:
                    video_urls = dash_data['video']
                    best_video_url = max(video_urls, key=lambda x: x['bandwidth'])['baseUrl']
                if 'audio' in dash_data:
                    audio_urls = dash_data['audio']
                    best_audio_url = max(audio_urls, key=lambda x: x['bandwidth'])['baseUrl']
            elif 'durl' in data:
                video_urls = data['durl']
                best_video_url = video_urls[0]['url']
            return {
                'video_url': f"{proxy_prefix_path}&url=" + quote(best_video_url) if best_video_url else None,
                'audio_url': f"{proxy_prefix_path}&url=" + quote(best_audio_url) if best_audio_url else None,
            }
        elif video_domain == 'youtube.com':
            # YouTube video URL fetching logic with PoToken
            yt = YouTube(
                video.url,
                use_po_token=True,
                po_token_verifier=po_token_verifier
            )
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
            if url:
                return {
                    'video_url': f"{proxy_prefix_path}&url=" + quote(url) if url else None,
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
        if not target_url.startswith('https://'):
            return None
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


def list_videos(
        user_id: int,
        query: str,
        subscription_id: int,
        category: str,
        sort_by: str,
        page: int,
        page_size: int
) -> Tuple[List[dict], int, dict]:
    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)

    params = {
        'user_id': user_id,
        'query': query,
        'show_nsfw': show_nsfw,
        'category': category,
        'sort_by': sort_by,
        'limit': page_size,
        'offset': (page - 1) * page_size,
        'subscription_id': subscription_id
    }

    with get_session() as session:
        videos_sql = sql_parser.parse_dynamic_sql(get_videos_sql(), params)
        videos_count_sql = sql_parser.parse_dynamic_sql(count_videos_sql(), params)
        videos_count_like_sql = sql_parser.parse_dynamic_sql(count_like_videos_sql(), params)
        count_result = session.execute(text(videos_count_sql), params).first()
        like_video_count = session.execute(text(videos_count_like_sql), params).scalar()
        video_count = VideoCountDto.model_validate(count_result._mapping)
        results = session.execute(text(videos_sql), params).all()
        videos = [VideoDto.model_validate(row._mapping) for row in results]

        # get subscriptions
        subscription_ids = list(set(video.subscription_id for video in videos))
        subscriptions = session.query(Subscription).filter(Subscription.id.in_(subscription_ids)).all()

        # get video related creators
        video_ids = [video.id for video in videos]
        creators = session.execute(select(Creator, VideoCreator)
                                   .join(VideoCreator, Creator.id == VideoCreator.creator_id)
                                   .where(VideoCreator.video_id.in_(video_ids))).all()
        # group creators by id
        creators_dict = {}
        for creator, video_creator in creators:
            if video_creator.video_id not in creators_dict:
                creators_dict[video_creator.video_id] = []
            creators_dict[video_creator.video_id].append(creator)

        # get video history
        video_history = video_history_service.get_videos_by_ids(user_id, video_ids)
        video_history_dict = {video_history.video_id: video_history for video_history in video_history}

        video_list = []
        for video in videos:
            subscription_info = next((sub for sub in subscriptions if sub.id == video.subscription_id), None)
            video_data = {
                'id': video.id,
                'title': video.title,
                'url': video.url,
                'thumbnail': video.thumbnail,
                'duration': video.duration,
                'last_position': video_history_dict.get(video.id).last_position if video.id in video_history_dict else 0,
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
            "all": video_count.total,
            "read": video_count.read,
            "unread": video_count.unread,
            "preview": video_count.preview,
            "liked": like_video_count
        }

        return video_list, video_count.total, counts


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


def get_video(user_id, video_id):
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

        video_history = video_history_service.get_video_history(user_id, video_id)
        video_interaction = video_interaction_service.get_video_interaction(user_id, video_id)

        video_data = {
            **video.to_dict(),
            'interaction_type': video_interaction.interaction_type if video_interaction else None,
            'last_position': video_history.last_position if video_history else 0,
            'domain': url_helper.extract_top_level_domain(video.url),
            'subscriptions': [subscription.to_dict() for subscription in subscriptions],
            'creators': [creator.to_dict() for creator in creators]
        }

        return video_data


def po_token_verifier() -> Tuple[str, str]:
    token_object = generate_youtube_token()
    return token_object["visitorData"], token_object["poToken"]


def generate_youtube_token() -> dict:
    try:
        result = subprocess.run(
            ["node", "scripts/youtube-token-generator.js"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        raise Exception(f"Failed to generate YouTube token: ", e)
