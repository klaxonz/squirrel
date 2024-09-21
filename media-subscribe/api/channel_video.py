import logging
import os
import re
import stat
from email.utils import formatdate
from mimetypes import guess_type
from typing import Optional

from fastapi import Query, APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from pytubefix import YouTube
from sqlalchemy import or_, func, and_
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
def get_channel_videos(
        query: str = Query(None, description="搜索关键字"),
        channel_id: str = Query(None, description="频道ID"),
        read_status: str = Query(None, description="阅读状态: all, read, unread"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量")
):
    with get_session() as s:
        base_query = s.query(ChannelVideo).filter(ChannelVideo.title != '', ChannelVideo.is_disliked == 0)

        if channel_id:
            base_query = base_query.filter(ChannelVideo.channel_id == channel_id)
        if query:
            base_query = base_query.filter(or_(
                func.lower(ChannelVideo.channel_name).like(func.lower(f'%{query}%')),
                func.lower(ChannelVideo.title).like(func.lower(f'%{query}%'))
            ))
        if read_status:
            if read_status == 'read':
                base_query = base_query.filter(ChannelVideo.if_read == True)
            elif read_status == 'unread':
                base_query = base_query.filter(ChannelVideo.if_read == False)

        total = base_query.count()
        offset = (page - 1) * page_size
        channel_videos = base_query.order_by(ChannelVideo.uploaded_at.desc()).offset(offset).limit(page_size)

        # 计算总数、已读数和未读数
        s_query = s.query(ChannelVideo)
        if channel_id:
            s_query = s_query.filter(ChannelVideo.channel_id == channel_id)
        total_count = s_query.count()
        read_count = s_query.filter(ChannelVideo.if_read == True).count()
        unread_count = total_count - read_count

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
            "data": channel_video_convert_list,
            "counts": {
                "all": total_count,
                "read": read_count,
                "unread": unread_count
            }
        }

    return response.success(channel_video_page)


class MarkReadRequest(BaseModel):
    channel_id: str
    video_id: str
    is_read: bool


@router.post("/api/channel-video/mark-read")
def mark_video_read(req: MarkReadRequest):
    with get_session() as s:
        s.query(ChannelVideo).filter(
            ChannelVideo.channel_id == req.channel_id,
            ChannelVideo.video_id == req.video_id
        ).update({"if_read": req.is_read})
        s.commit()
    return response.success()


# 新增请求模型
class MarkReadRequest(BaseModel):
    channel_id: str
    video_id: str
    is_read: bool


class MarkReadBatchRequest(BaseModel):
    is_read: bool
    channel_id: Optional[str] = None
    direction: str  # 'above' or 'below'
    uploaded_at: str  # 改为使用 ID 而不是日期

@router.post("/api/channel-video/mark-read-batch")
def mark_videos_read_batch(req: MarkReadBatchRequest):
    with get_session() as s:
        query = s.query(ChannelVideo)
        if req.channel_id:
            query = query.filter(ChannelVideo.channel_id == req.channel_id)
        
        if req.direction == 'above':
            query = query.filter(ChannelVideo.uploaded_at >= req.uploaded_at)
        elif req.direction == 'below':
            query = query.filter(ChannelVideo.uploaded_at <= req.uploaded_at)
        
        query.update({"if_read": req.is_read})
        s.commit()
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


class DislikeRequest(BaseModel):
    channel_id: str
    video_id: str


@router.post("/api/channel-video/dislike")
def dislike_video(req: DislikeRequest):
    with get_session() as session:
        video = session.query(ChannelVideo).filter(
            ChannelVideo.channel_id == req.channel_id,
            ChannelVideo.video_id == req.video_id
        ).first()

        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        video.is_disliked = True
        session.commit()

    return response.success({"message": "Video marked as disliked"})
