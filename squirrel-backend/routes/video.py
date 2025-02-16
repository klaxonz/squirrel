import logging

from fastapi import Query, APIRouter, Request, HTTPException, Depends

import common.response as response
from common.video_stream import VideoStreamHandler
from core import download_config
from downloader.factory import DownloaderFactory
from meta.factory import VideoFactory
from models.user import User
from proxy.bilibili import BilibiliProxy
from proxy.javdb import JavdbProxy
from schemas.video import DownloadVideoRequest, SortBy
from services import video_service, subscription_video_service, subscription_service
from utils.jwt_helper import get_current_user

logger = logging.getLogger()

router = APIRouter(tags=['频道视频接口'])


@router.get("/api/video/url")
def get_video_url(
        video_id: int = Query(None, description="视频ID")
):
    video_urls = video_service.get_video_url(video_id)
    return response.success(video_urls)


@router.get("/api/video/detail")
def get_video(
        video_id: int = Query(None, description="视频ID")
):
    video = video_service.get_video(video_id)
    return response.success(video)


@router.get("/api/video/list")
def get_videos(
        query: str = Query(None, description="搜索关键字"),
        subscription_id: int = Query(None, description="订阅ID"),
        category: str = Query(None, description="阅读状态: all, read, unread, preview, like"),
        sort_by: SortBy = Query(SortBy.UPLOADED_AT, description="排序字段"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量"),
        current_user: User = Depends(get_current_user)
):
    videos, total_counts, counts = video_service.list_videos(current_user.id, query, subscription_id, category, sort_by, page, page_size)
    return response.success({
        "total": total_counts,
        "page": page,
        "pageSize": page_size,
        "data": videos,
        "counts": counts
    })


@router.post("/api/video/download")
def download_video(req: DownloadVideoRequest):
    video_service.download_video(req.video_id)
    return response.success()


@router.get("/api/video/play/{video_id}")
def play_video(request: Request, video_id: int):
    video = video_service.get_video_by_id(video_id)
    downloader = DownloaderFactory.create_downloader(video.url)
    video_info = downloader.get_video_info(video.url)
    video = VideoFactory.create_video(video.url, video_info)
    subscription_video = subscription_video_service.get_subscription_video_by_video_id(video.id)
    subscription = subscription_service.get_subscription_by_id(subscription_video.subscription_id)
    output_dir = download_config.get_download_full_path(subscription.name, video.season)
    filename = download_config.get_valid_filename(video.title)
    video_path = VideoStreamHandler.find_video_file(output_dir, filename)
    if not video_path:
        raise HTTPException(status_code=404, detail="Video file not found")
    return VideoStreamHandler.create_stream_response(request, video_path)


@router.get("/api/video/proxy")
async def proxy_video(domain: str, url: str, request: Request):
    """代理视频文件，用于解决跨域问题"""
    proxy_map = {
        "bilibili.com": BilibiliProxy,
        "javdb.com": JavdbProxy
    }
    
    proxy_class = proxy_map.get(domain)
    if not proxy_class:
        raise HTTPException(status_code=400, detail=f"Unsupported domain: {domain}")
        
    proxy = proxy_class(request)
    return await proxy.handle_stream(url)
