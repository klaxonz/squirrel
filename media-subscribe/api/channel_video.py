import logging
import os
import re
import stat
from email.utils import formatdate
from mimetypes import guess_type

from fastapi import Query, APIRouter, Request, Depends
from pydantic import BaseModel
from pytubefix import YouTube
from sqlalchemy import or_, func
from starlette.responses import StreamingResponse
import requests

from common.cookie import filter_cookies_to_query_string
import common.response as response
from common.database import get_session
from downloader.downloader import Downloader
from meta.video import VideoFactory
from model.channel import ChannelVideo
from service import download_service

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=['频道视频接口']
)


@router.get("/api/channel-video/video/url")
def subscribe_channel(
        channel_id: str = Query(None, description="频道名称"),
        video_id: str = Query(None, description="视频ID"),
):
    with get_session() as s:
        channel_video = s.query(ChannelVideo).where(ChannelVideo.channel_id == channel_id,
                                                    ChannelVideo.video_id == video_id).first()
        domain = channel_video.domain
        if domain == 'bilibili.com':

            cookies = filter_cookies_to_query_string("https://www.bilibili.com")
            headers = {
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/124.0.0.0 Safari/537.36',
                'Cookie': cookies
            }

            req_url = f'https://api.bilibili.com/x/web-interface/view?bvid={video_id}'
            resp = requests.get(req_url, headers=headers)
            cid = resp.json()['data']['cid']

            video_url = f'https://api.bilibili.com/x/player/wbi/playurl?bvid={video_id}&cid={cid}&platform=html5'
            resp = requests.get(video_url, headers=headers)
            url_ = resp.json()['data']['durl'][0]['url']

            return response.success(url_)
        elif domain == 'youtube.com':
            yt = YouTube(f'https://youtube.com/watch?v={video_id}', use_oauth=True, allow_oauth_cache=True)
            sd = yt.streams.filter(progressive=True).all()
            return response.success(sd[0].url)


@router.get("/api/channel-video/list")
def subscribe_channel(
        query: str = Query(None, description="搜索关键字"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    with get_session() as s:
        base_query = s.query(ChannelVideo).filter(ChannelVideo.title != '', ChannelVideo.if_read == 0)
        if query:
            base_query = base_query.filter(or_(
                func.lower(ChannelVideo.channel_name).like(func.lower(f'%{query}%')),
                func.lower(ChannelVideo.title).like(func.lower(f'%{query}%'))
            ))

        total = base_query.count()

        offset = (page - 1) * page_size
        channel_videos = (base_query
                          .order_by(ChannelVideo.uploaded_at.desc())
                          .offset(offset)
                          .limit(page_size))

        channel_video_convert_list = [
            {
                'id': chanel_video.id,
                'channel_id': chanel_video.channel_id,
                'channel_name': chanel_video.channel_name,
                'channel_avatar': chanel_video.channel_avatar,
                'video_id': chanel_video.video_id,
                'title': chanel_video.title,
                'domain': chanel_video.domain,
                'url': chanel_video.url,
                'thumbnail': chanel_video.thumbnail,
                'duration': chanel_video.duration,
                'if_downloaded': chanel_video.if_downloaded,
                'if_read': chanel_video.if_read,
                'uploaded_at': chanel_video.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                'created_at': chanel_video.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for chanel_video in channel_videos
        ]

        channel_video_page = {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "data": channel_video_convert_list
        }

    return response.success(channel_video_page)


class MarkReadRequest(BaseModel):
    channel_id: str
    video_id: str


@router.post("/api/channel-video/mark-read")
def subscribe_channel(req: MarkReadRequest):
    with get_session() as s:
        s.query(ChannelVideo).where(ChannelVideo.channel_id == req.channel_id,
                                    ChannelVideo.video_id == req.video_id).update({
            'if_read': True
        })

    return response.success()


class DownloadChannelVideoRequest(BaseModel):
    channel_id: str
    video_id: str


@router.post("/api/channel-video/download")
def download_channel_video(req: DownloadChannelVideoRequest):
    with get_session() as s:
        channel_video = s.query(ChannelVideo).filter(ChannelVideo.channel_id == req.channel_id,
                                                     ChannelVideo.video_id == req.video_id).first()

        download_service.start(channel_video.url, if_only_extract=False, if_subscribe=True, if_retry=False,
                               if_manual_retry=True)

    return response.success()


@router.get("/api/channel/video/play/{channel_id}/{video_id}")
def play_video(request: Request, channel_id: str, video_id: str):
    with get_session() as s:
        channel_video = s.query(ChannelVideo).filter(ChannelVideo.channel_id == channel_id,
                                                     ChannelVideo.video_id == video_id).first()
        s.expunge(channel_video)

    base_info = Downloader.get_video_info(channel_video.url)
    video = VideoFactory.create_video(channel_video.url, base_info)
    output_dir = video.get_download_full_path()
    filename = video.get_valid_filename() + ".mp4"
    video_path = os.path.join(output_dir, filename)

    stat_result = os.stat(video_path)
    content_type, encoding = guess_type(video_path)
    content_type = content_type or 'application/octet-stream'
    range_str = request.headers.get('range', '')
    range_match = re.search(r'bytes=(\d+)-(\d+)', range_str, re.S) or re.search(r'bytes=(\d+)-', range_str, re.S)
    if range_match:
        start_bytes = int(range_match.group(1))
        end_bytes = int(range_match.group(2)) if range_match.lastindex == 2 else stat_result.st_size - 1
    else:
        start_bytes = 0
        end_bytes = stat_result.st_size - 1

    content_length = stat_result.st_size - start_bytes if stat.S_ISREG(stat_result.st_mode) else stat_result.st_size
    # 打开文件从起始位置开始分片读取文件
    return StreamingResponse(
        file_iterator(video_path, start_bytes, 1024 * 1024 * 1),  # 每次读取 1M
        media_type=content_type,
        headers={
            'accept-ranges': 'bytes',
            'connection': 'keep-alive',
            'content-length': str(content_length),
            'content-range': f'bytes {start_bytes}-{end_bytes}/{stat_result.st_size}',
            'last-modified': formatdate(stat_result.st_mtime, usegmt=True),
        },
        status_code=206 if start_bytes > 0 else 200
    )


def file_iterator(file_path, offset, chunk_size):
    """
    文件生成器
    :param file_path: 文件绝对路径
    :param offset: 文件读取的起始位置
    :param chunk_size: 文件读取的块大小
    :return: yield
    """
    with open(file_path, 'rb') as f:
        f.seek(offset, os.SEEK_SET)
        while True:
            data = f.read(chunk_size)
            if data:
                yield data
            else:
                break
