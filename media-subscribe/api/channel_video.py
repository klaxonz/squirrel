import asyncio
import logging
import os
import re
import stat
from email.utils import formatdate
from mimetypes import guess_type
from typing import Optional
from urllib.parse import quote

import httpx
import requests
from fastapi import Query, APIRouter, Request, HTTPException
from pydantic import BaseModel
from pytubefix import YouTube
from sqlalchemy import or_, func
from starlette.responses import StreamingResponse

import common.response as response
from common.cookie import filter_cookies_to_query_string
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

            video_url = f'https://api.bilibili.com/x/player/wbi/playurl?bvid={video_id}&cid={cid}&fnval=144'
            resp = requests.get(video_url, headers=headers)
            data = resp.json()['data']

            # Extract the best quality video URL
            video_urls = data['dash']['video']
            best_video_url = max(video_urls, key=lambda x: x['bandwidth'])['baseUrl']

            # Extract the best quality audio URL
            audio_urls = data['dash']['audio']
            best_audio_url = max(audio_urls, key=lambda x: x['bandwidth'])['baseUrl']

            return response.success({
                'video_url': "http://localhost:8000/api/channel-video/proxy?url=" + quote(best_video_url),
                'audio_url': "http://localhost:8000/api/channel-video/proxy?url=" + quote(best_audio_url),
            })
        elif domain == 'youtube.com':
            yt = YouTube(f'https://youtube.com/watch?v={video_id}', use_oauth=True, allow_oauth_cache=True)

            video_stream = yt.streams.filter(progressive=False, type="video").order_by('resolution').desc().first()
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()

            return response.success({
                'video_url': video_stream.url if video_stream else None,
                'audio_url': audio_stream.url if audio_stream else None,
            })


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


@router.get("/api/channel-video/proxy")
async def proxy_video(url: str, request: Request):
    """
    代理视频文件，用于解决跨域问题
    """
    max_retries = 3
    chunk_size = 1024  # 减小 chunk size

    headers = {
        "Referer": "https://www.bilibili.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    if "range" in request.headers:
        headers["Range"] = request.headers["range"]

    async def stream_with_retry():
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                    async with client.stream("GET", url, headers=headers) as resp:
                        resp.raise_for_status()
                        async for chunk in resp.aiter_bytes(chunk_size=chunk_size):
                            yield chunk
                return  # 如果成功完成，就退出函数
            except (httpx.NetworkError, httpx.TimeoutException, httpx.StreamClosed) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying: {str(e)}")
                await asyncio.sleep(1)  # 在重试之前等待一秒

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            async with client.stream("GET", url, headers=headers) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get('Content-Type', 'application/octet-stream')
                resp_headers = {
                    "Accept-Ranges": "bytes",
                    "Content-Type": content_type,
                }
                if 'Content-Range' in resp.headers:
                    resp_headers['Content-Range'] = resp.headers['Content-Range']

                return StreamingResponse(
                    stream_with_retry(),
                    status_code=resp.status_code,
                    headers=resp_headers
                )
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error occurred: {exc.response.status_code} {exc.response.reason_phrase}")
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.reason_phrase)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
