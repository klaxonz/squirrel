import logging
from fastapi import Query, APIRouter, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
import common.response as response
from models.user import User
from schemas.video.request.video import RemoteVideoSaveRequest, SortBy, VideoCategory, YesNoAll, TimeRange, DurationFilter, ContentType
from services import video_service
from services.video_subtitle_service import SubtitleErrorCode, SubtitleServiceError, fetch_video_subtitles
from typing import List
from utils.site_catalog import SiteCatalog
from utils.jwt_helper import get_current_user

logger = logging.getLogger()

router = APIRouter(prefix='/api/video', tags=['频道视频接口'])


@router.post("/remote-save")
def save_remote_video(
        data: RemoteVideoSaveRequest,
        current_user: User = Depends(get_current_user)
):
    try:
        video = video_service.save_remote_video(data.model_dump())
        return response.success(video_service.get_video(current_user.id, video.id))
    except ValueError as exc:
        return response.param_error(str(exc))
    except Exception:
        logger.exception("Failed to save remote video")
        return response.server_error("保存远端视频失败")


@router.get("/detail")
def get_video(
        video_id: int = Query(None, description="视频ID"),
        current_user: User = Depends(get_current_user)
):
    video = video_service.get_video(current_user.id, video_id)
    return response.success(video)


@router.get("/list")
def get_videos(
        query: str = Query(None, description="搜索关键字"),
        subscription_id: int = Query(None, description="订阅ID"),
        category: VideoCategory = Query(VideoCategory.ALL, description="阅读状态: all, read, unread, preview, like"),
        sort_by: SortBy = Query(SortBy.UPLOADED_AT, description="排序字段"),
        nsfw: YesNoAll = Query(YesNoAll.ALL, description="NSFW 过滤: all|yes|no"),
        special: YesNoAll = Query(YesNoAll.ALL, description="特别关注过滤: all|yes|no"),
        site: str = Query(None, description="站点过滤：例如 youtube、bilibili 等（支持别名）"),
        with_total: bool = Query(False, alias="withTotal", description="是否返回 total（会额外执行 count 查询）"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量"),
        time_range: TimeRange = Query(TimeRange.ALL, description="时间范围: all|today|week|month|year"),
        duration: DurationFilter = Query(DurationFilter.ALL, description="时长: all|short|medium|long"),
        content_type: ContentType = Query(ContentType.ALL, description="内容类型: all|CHANNEL|PLAYLIST|ACTRESS|MOVIE|TV_SERIES|ACTOR"),
        current_user: User = Depends(get_current_user)
):

    domains_list: List[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains_list = resolved if resolved else None

    if hasattr(current_user, '_cached_config'):
        logger.info(f"[Performance] Route: Using cached user config")

    videos, total_counts = video_service.list_videos(
        current_user.id, query, subscription_id, category.value, sort_by.value, nsfw.value, domains_list, page, page_size,
        with_total=with_total, time_range=time_range.value, duration=duration.value, content_type=content_type.value, special=special.value,
    )

    result = response.success({
        "total": total_counts,
        "page": page,
        "pageSize": page_size,
        "data": videos
    })

    return result


@router.get("/random")
def get_random_video(
        category: VideoCategory = Query(VideoCategory.ALL, description="类别：all|read|unread|preview|liked|later"),
        subscription_id: int = Query(None, description="订阅ID"),
        nsfw: YesNoAll = Query(YesNoAll.ALL, description="NSFW 过滤: all|yes|no"),
        site: str = Query(None, description="站点过滤：例如 youtube、bilibili 等（支持别名）"),
        query: str = Query(None, description="搜索关键字"),
        time_range: TimeRange = Query(TimeRange.ALL, description="时间范围: all|today|week|month|year"),
        duration: DurationFilter = Query(DurationFilter.ALL, description="时长: all|short|medium|long"),
        content_type: ContentType = Query(ContentType.ALL, description="内容类型: all|CHANNEL|PLAYLIST|ACTRESS|MOVIE|TV_SERIES|ACTOR"),
        current_user: User = Depends(get_current_user)
):
    domains_list: List[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains_list = resolved if resolved else None

    video = video_service.get_random_video(
        current_user.id,
        category=category.value,
        subscription_id=subscription_id,
        nsfw=nsfw.value,
        domains=domains_list,
        query=query,
        time_range=time_range.value,
        duration=duration.value,
        content_type=content_type.value,
    )
    if not video:
        return response.not_found("未找到符合条件的视频")

    # 返回完整视频详情，便于前端直接播放
    detail = video_service.get_video(current_user.id, video.id)
    return response.success(detail)


@router.get("/proxy")
async def proxy_video(domain: str, url: str, request: Request, referer: str | None = None):
    """代理视频文件，用于解决跨域问题"""
    from core.streaming.proxy import VideoProxy

    proxy = VideoProxy(request, domain=domain)
    return await proxy.handle_stream(url, referer=referer)


@router.get("/subtitles")
def get_video_subtitles(
        video_id: int = Query(..., description="视频ID"),
        lang: str | None = Query(None, description="字幕语言代码；留空时走站点默认值"),
        fmt: str = Query("srt", description="返回格式：支持 srt、vtt"),
        current_user: User = Depends(get_current_user)
):
    try:
        subtitle_file = fetch_video_subtitles(video_id, lang=lang, fmt=fmt)
        return PlainTextResponse(
            content=subtitle_file.content,
            media_type=subtitle_file.media_type,
            headers={
                "Content-Disposition": f"inline; filename=\"{subtitle_file.filename}\""
            }
        )
    except SubtitleServiceError as exc:
        if exc.code in {SubtitleErrorCode.VIDEO_NOT_FOUND, SubtitleErrorCode.SUBTITLES_NOT_AVAILABLE}:
            raise HTTPException(status_code=404, detail=exc.message)
        raise HTTPException(status_code=400, detail=exc.message)
    except Exception:
        logger.exception('Subtitles fetch failed')
        raise HTTPException(status_code=500, detail="Server error")
