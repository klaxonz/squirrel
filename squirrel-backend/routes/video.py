import logging

from fastapi import APIRouter, Depends, Query

from common import response
from models.user import User
from schemas.video.request.video import (
    ContentType,
    DurationFilter,
    RemoteVideoSaveRequest,
    SortBy,
    TimeRange,
    VideoCategory,
    YesNoAll,
)
from services.auth_service import get_current_user
from services.video_service import VideoService
from utils.site_catalog import SiteCatalog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["频道视频接口"])


def get_video_service() -> VideoService:
    return VideoService()


@router.post("/remote-save")
def save_remote_video(
        data: RemoteVideoSaveRequest,
        current_user: User = Depends(get_current_user),
        svc: VideoService = Depends(get_video_service),
):
    try:
        video = svc.save_remote_video(data.model_dump())
        return response.success(svc.get_video(current_user.id, video.id))
    except ValueError as exc:
        return response.param_error(str(exc))
    except Exception:
        # API boundary -- convert to HTTP error response
        logger.exception("Failed to save remote video")
        return response.server_error("保存远端视频失败")


@router.get("/detail")
def get_video(
        video_id: int = Query(None, description="视频ID"),
        current_user: User = Depends(get_current_user),
        svc: VideoService = Depends(get_video_service),
):
    video = svc.get_video(current_user.id, video_id)
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
        current_user: User = Depends(get_current_user),
        svc: VideoService = Depends(get_video_service),
):

    domains_list: list[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains_list = resolved or None

    if hasattr(current_user, "_cached_config"):
        logger.info("[Performance] Route: Using cached user config")

    videos, total_counts = svc.list_videos(
        current_user.id, query, subscription_id, category.value, sort_by.value, nsfw.value, domains_list, page, page_size,
        with_total=with_total, time_range=time_range.value, duration=duration.value, content_type=content_type.value, special=special.value,
    )

    result = response.success({
        "total": total_counts,
        "page": page,
        "pageSize": page_size,
        "data": videos,
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
        current_user: User = Depends(get_current_user),
        svc: VideoService = Depends(get_video_service),
):
    domains_list: list[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains_list = resolved or None

    video = svc.get_random_video(
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
    detail = svc.get_video(current_user.id, video.id)
    return response.success(detail)



