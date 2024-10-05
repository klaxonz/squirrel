import asyncio
import logging
import os
import re
import stat
from email.utils import formatdate
from mimetypes import guess_type

import httpx
from fastapi import Query, APIRouter, Request, HTTPException, Depends
from sqlalchemy import and_
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

import common.response as response
from common.database import get_db, get_session
from downloader.downloader import Downloader
from meta.video import VideoFactory
from model.channel import ChannelVideo
from schemas.channel_video import MarkReadRequest, MarkReadBatchRequest, DownloadChannelVideoRequest, DislikeRequest
from services.channel_video_service import ChannelVideoService

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=['频道视频接口']
)


@router.get("/api/channel-video/video/url")
def get_video_url(
    channel_id: str = Query(None, description="频道名称"),
    video_id: str = Query(None, description="视频ID"),
    db: Session = Depends(get_db)
):
    channel_video_service = ChannelVideoService(db)
    video_urls = channel_video_service.get_video_url(channel_id, video_id)
    return response.success(video_urls)


@router.get("/api/channel-video/list")
def get_channel_videos(
    query: str = Query(None, description="搜索关键字"),
    channel_id: str = Query(None, description="频道ID"),
    read_status: str = Query(None, description="阅读状态: all, read, unread"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量"),
    db: Session = Depends(get_db)
):
    channel_video_service = ChannelVideoService(db)
    videos, counts = channel_video_service.list_channel_videos(query, channel_id, read_status, page, page_size)
    return response.success({
        "total": len(videos),
        "page": page,
        "pageSize": page_size,
        "data": videos,
        "counts": counts
    })


@router.post("/api/channel-video/mark-read")
def mark_video_read(req: MarkReadRequest, db: Session = Depends(get_db)):
    channel_video_service = ChannelVideoService(db)
    channel_video_service.mark_video_read(req.channel_id, req.video_id, req.is_read)
    return response.success()


@router.post("/api/channel-video/mark-read-batch")
def mark_videos_read_batch(req: MarkReadBatchRequest, db: Session = Depends(get_db)):
    channel_video_service = ChannelVideoService(db)
    channel_video_service.mark_videos_read_batch(req.channel_id, req.direction, req.uploaded_at, req.is_read)
    return response.success()


@router.post("/api/channel-video/download")
def download_channel_video(req: DownloadChannelVideoRequest, db: Session = Depends(get_db)):
    channel_video_service = ChannelVideoService(db)
    channel_video_service.download_channel_video(req.channel_id, req.video_id)
    return response.success()


@router.post("/api/channel-video/dislike")
def dislike_video(req: DislikeRequest, db: Session = Depends(get_db)):
    channel_video_service = ChannelVideoService(db)
    success = channel_video_service.dislike_video(req.channel_id, req.video_id)
    if success:
        return response.success({"message": "Video marked as disliked"})
    raise HTTPException(status_code=404, detail="Video not found")


@router.post("/api/channel-video/save-progress")
async def save_video_progress(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    channel_video_service = ChannelVideoService(db)
    channel_video_service.save_video_progress(data['channel_id'], data['video_id'], data['progress'])
    return response.success({"message": "Progress saved successfully"})


@router.get("/api/channel-video/get-progress")
def get_video_progress(channel_id: str, video_id: str, db: Session = Depends(get_db)):
    channel_video_service = ChannelVideoService(db)
    progress = channel_video_service.get_video_progress(channel_id, video_id)
    return response.success({"progress": progress})


@router.get("/api/channel/video/play/{channel_id}/{video_id}")
def play_video(request: Request, channel_id: str, video_id: str):
    with get_session() as s:
        channel_video = s.query(ChannelVideo).filter(
            and_(
                ChannelVideo.channel_id == channel_id,
                ChannelVideo.video_id == video_id
            )
        ).first()
        if channel_video:
            s.expunge(channel_video)
        else:
            raise HTTPException(status_code=404, detail="Video not found")

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
                if 'Content-Length' in resp.headers:
                    resp_headers['Content-Length'] = resp.headers['Content-Length']

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