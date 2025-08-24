import logging
from fastapi import Query, APIRouter, Request, HTTPException, Depends, Response
from fastapi.responses import PlainTextResponse
import common.response as response
from common.video_stream import VideoStreamHandler
from core import download_config
from core.exceptions.video_exceptions import UnsupportedDomainError, VideoUrlExtractionError
from models.user import User
from schemas.video.request.video import SortBy, DownloadVideoRequest
from services import video_service, subscription_video_service, subscription_service
from sites.downloader import DownloaderFactory
from sites.meta import VideoFactory
from utils.jwt_helper import get_current_user

logger = logging.getLogger()

router = APIRouter(tags=['频道视频接口'])


@router.get("/api/video/url")
def get_video_url(
        video_id: int = Query(None, description="视频ID")
):
    try:
        if video_id is None:
            return response.param_error("参数错误 (VIDEO_ID_REQUIRED)")

        video_urls = video_service.get_video_url(video_id)
        # 校验是否成功提取到可播放链接（支持 DASH 的 mpd_url 返回）
        has_video = getattr(video_urls, 'video_url', None)
        has_audio = getattr(video_urls, 'audio_url', None)
        has_mpd = getattr(video_urls, 'mpd_url', None)
        if not video_urls or (not has_video and not has_audio and not has_mpd):
            return response.not_found("无法获取播放链接 (NO_STREAM_URL)")
        return response.success(video_urls)

    except UnsupportedDomainError as e:
        logger.warning(f"Unsupported domain for video {video_id}: {e}")
        return response.param_error("不支持的域名 (UNSUPPORTED_DOMAIN)")
    except VideoUrlExtractionError as e:
        logger.error(f"Video URL extraction failed for {video_id}: {e}")
        return response.server_error("播放链接提取失败 (EXTRACT_FAILED)")
    except ValueError as e:
        # 包括视频不存在等
        msg = str(e)
        if 'not found' in msg.lower():
            return response.not_found("视频不存在 (VIDEO_NOT_FOUND)")
        logger.error(f"Invalid request for get_video_url: {e}")
        return response.param_error("请求不合法 (BAD_REQUEST)")
    except Exception as e:
        logger.exception(f"Unexpected error in get_video_url for video_id={video_id}: {e}")
        return response.server_error("服务器内部错误 (SERVER_ERROR)")


@router.get("/api/video/detail")
def get_video(
        video_id: int = Query(None, description="视频ID"),
        current_user: User = Depends(get_current_user)
):
    video = video_service.get_video(current_user.id, video_id)
    return response.success(video)


@router.get("/api/video/list")
def get_videos(
        query: str = Query(None, description="搜索关键字"),
        subscription_id: int = Query(None, description="订阅ID"),
        category: str = Query(None, description="阅读状态: all, read, unread, preview, like"),
        sort_by: SortBy = Query(SortBy.UPLOADED_AT, description="排序字段"),
        nsfw: str = Query("all", description="NSFW 过滤: all|yes|no", pattern=r"^(all|yes|no)$"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量"),
        current_user: User = Depends(get_current_user)
):
    videos, total_counts, counts = video_service.list_videos(
        current_user.id, query, subscription_id, category, sort_by, nsfw, page, page_size
    )
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
    video_info = downloader.get_video_info()
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
    from sites.proxy import ProxyFactory
    proxy = ProxyFactory.create_proxy(domain, request)
    return await proxy.handle_stream(url)


@router.get("/api/video/subtitles")
def get_video_subtitles(
        video_id: int = Query(..., description="视频ID"),
        lang: str = Query("ai-zh", description="字幕语言代码（b站如 ai-zh/zh/zh-CN/en 等）"),
        fmt: str = Query("srt", description="返回格式：目前仅支持 srt"),
        current_user: User = Depends(get_current_user)
):
    if fmt.lower() != "srt":
        raise HTTPException(status_code=400, detail="Only srt format is supported")

    video = video_service.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        from sites.subtitles import SubtitlesFactory
        srt_text, filename = SubtitlesFactory.get_subtitles_for_video(video, lang, fmt)
        return PlainTextResponse(
            content=srt_text,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"inline; filename=\"{filename}\""
            }
        )
    except ValueError as e:
        detail = str(e)
        if 'No subtitles available' in detail:
            raise HTTPException(status_code=404, detail="No subtitles available")
        raise HTTPException(status_code=400, detail=detail)
    except Exception:
        logger.exception('Subtitles fetch failed')
        raise HTTPException(status_code=500, detail="Server error")


@router.get("/api/video/mpd")
def get_video_mpd(
        video_id: int = Query(..., description="视频ID"),
):
    """
    根据不同站点生成 MPD（站点适配在 sites/* 中实现）
    """
    if video_id is None:
        raise HTTPException(status_code=400, detail="video_id is required")

    video = video_service.get_video_by_id(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        from sites.mpd import MpdFactory
        mpd_xml = MpdFactory.build_mpd_for_video(video)
        if not mpd_xml:
            raise HTTPException(status_code=500, detail="Failed to build MPD")
        return Response(
            content=mpd_xml,
            media_type="application/dash+xml",
            headers={
                "Cache-Control": "no-store, max-age=0",
                "Pragma": "no-cache"
            }
        )
    except ValueError as e:
        # 未注册对应站点的 MPD 构建器
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Failed to build MPD")
        raise HTTPException(status_code=500, detail="Internal Server Error")

