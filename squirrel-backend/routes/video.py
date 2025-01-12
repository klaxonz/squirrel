import asyncio
import logging
import re
from urllib.parse import urljoin

import httpx
from fastapi import Query, APIRouter, Request, HTTPException
from starlette.responses import StreamingResponse

import common.response as response
from common.video_stream import VideoStreamHandler
from core import download_config
from downloader.factory import DownloaderFactory
from meta.factory import VideoFactory
from schemas.video import DownloadVideoRequest, SortBy
from services import video_service, subscription_video_service, subscription_service

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
def get_channel_videos(
        query: str = Query(None, description="搜索关键字"),
        subscription_id: int = Query(None, description="订阅ID"),
        category: str = Query(None, description="阅读状态: all, read, unread, preview, like"),
        sort_by: SortBy = Query(SortBy.UPLOADED_AT, description="排序字段"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量"),
):
    videos, total_counts, counts = video_service.list_videos(query, subscription_id, category, sort_by, page, page_size)
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
    output_dir = download_config.get_download_full_path(subscription.content_name, video.season)
    filename = download_config.get_valid_filename(video.title)
    video_path = VideoStreamHandler.find_video_file(output_dir, filename)
    if not video_path:
        raise HTTPException(status_code=404, detail="Video file not found")
    return VideoStreamHandler.create_stream_response(request, video_path)


@router.get("/api/video/proxy")
async def proxy_video(domain: str, url: str, request: Request):
    """
    代理视频文件，用于解决跨域问题
    """
    if domain == "bilibili.com":
        max_retries = 3
        chunk_size = 256  # 减小 chunk size

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
    if domain == "javdb.com":
        try:
            async with httpx.AsyncClient() as client:
                # 设置请求头
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Referer': 'https://missav.com/',
                    'Origin': 'https://missav.com'
                }

                # 获取内容
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                content = response.content
                content_type = response.headers.get('content-type', '')

                # 如果是 m3u8 文件
                if url.endswith('.m3u8') or 'application/vnd.apple.mpegurl' in content_type.lower():
                    content_text = content.decode()
                    base_url = url.rsplit('/', 1)[0]

                    # 处理 m3u8 内容中的 URL
                    def replace_url(match):
                        path = match.group(1)
                        if path.startswith('http'):
                            full_url = path
                        else:
                            full_url = urljoin(base_url + '/', path)
                        return f"/api/video/proxy?domain=javdb.com&url={full_url}"

                    # 替换所有视频分片文件路径（包括.ts和.jpeg）
                    content_text = re.sub(
                        r'([^"\n]+\.(ts|jpeg|jpg|m3u8)[^"\n]*)',
                        replace_url,
                        content_text
                    )

                    return StreamingResponse(
                        iter([content_text.encode()]),
                        media_type='application/vnd.apple.mpegurl',
                        headers={
                            'Access-Control-Allow-Origin': '*',
                            'Cache-Control': 'no-cache',
                        }
                    )

                # 修改处理视频分片的部分
                return StreamingResponse(
                    iter([content]),
                    media_type=content_type or 'application/octet-stream',  # 确保始终有content-type
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Cache-Control': 'public, max-age=31536000',
                    }
                )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Error fetching content: {str(e)}")
        except Exception as e:
            logger.error(f"Error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
