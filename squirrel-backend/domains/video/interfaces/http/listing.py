import logging

from fastapi import APIRouter, Depends, Query

from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from domains.video.application.services.listing.service import get_video as get_video_detail
from domains.video.application.services.listing.service import list_videos
from domains.video.interfaces.dto.request.video import (
    ContentType,
    DurationFilter,
    SortBy,
    TimeRange,
    VideoCategory,
    YesNoAll,
)
from infrastructure.http import response
from infrastructure.site_catalog.catalog import SiteCatalog

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get('/detail')
def get_video(
    video_id: int = Query(None, description='视频ID'),
    current_user: User = Depends(get_current_user),
):
    video = get_video_detail(current_user.id, video_id)
    return response.success(video)


@router.get('/list')
def get_videos(
    query: str = Query(None, description='搜索关键字'),
    subscription_id: int = Query(None, description='订阅ID'),
    category: VideoCategory = Query(VideoCategory.ALL, description='阅读状态: all, read, unread, preview, like'),
    sort_by: SortBy = Query(SortBy.UPLOADED_AT, description='排序字段'),
    nsfw: YesNoAll = Query(YesNoAll.ALL, description='NSFW 过滤: all|yes|no'),
    special: YesNoAll = Query(YesNoAll.ALL, description='特别关注过滤: all|yes|no'),
    site: str = Query(None, description='站点过滤:例如 youtube、bilibili 等(支持别名)'),
    cursor: str | None = Query(None, description='分页游标(首页不传;翻页传上一页响应的 next_cursor)'),
    page_size: int = Query(20, ge=1, le=100, alias='pageSize', description='每页数量'),
    time_range: TimeRange = Query(TimeRange.ALL, description='时间范围: all|today|week|month|year'),
    duration: DurationFilter = Query(DurationFilter.ALL, description='时长: all|short|medium|long'),
    content_type: ContentType = Query(ContentType.ALL, description='内容类型: all|CHANNEL|PLAYLIST|ACTRESS|MOVIE|TV_SERIES|ACTOR'),
    current_user: User = Depends(get_current_user),
):
    domains_list: list[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains_list = resolved or None

    if hasattr(current_user, '_cached_config'):
        logger.info('[Performance] Route: Using cached user config')

    videos, next_cursor = list_videos(
        current_user.id, query, subscription_id, category.value, sort_by.value, nsfw.value, domains_list,
        cursor, page_size,
        time_range=time_range.value, duration=duration.value, content_type=content_type.value, special=special.value,
    )

    return response.success({
        'data': videos,
        'next_cursor': next_cursor,
        'has_more': next_cursor is not None,
    })
