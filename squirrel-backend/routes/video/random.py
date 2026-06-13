from fastapi import APIRouter, Depends, Query

from common import response
from models.user import User
from schemas.video.request.video import ContentType, DurationFilter, TimeRange, VideoCategory, YesNoAll
from services.site_catalog.catalog import SiteCatalog
from services.user.auth import get_current_user
from services.video.listing.service import get_video as get_video_detail
from services.video.random import get_random_video as get_random_video_record

router = APIRouter()


@router.get('/random')
def get_random_video(
    category: VideoCategory = Query(VideoCategory.ALL, description='类别：all|read|unread|preview|liked|later'),
    subscription_id: int = Query(None, description='订阅ID'),
    nsfw: YesNoAll = Query(YesNoAll.ALL, description='NSFW 过滤: all|yes|no'),
    site: str = Query(None, description='站点过滤：例如 youtube、bilibili 等（支持别名）'),
    query: str = Query(None, description='搜索关键字'),
    time_range: TimeRange = Query(TimeRange.ALL, description='时间范围: all|today|week|month|year'),
    duration: DurationFilter = Query(DurationFilter.ALL, description='时长: all|short|medium|long'),
    content_type: ContentType = Query(ContentType.ALL, description='内容类型: all|CHANNEL|PLAYLIST|ACTRESS|MOVIE|TV_SERIES|ACTOR'),
    current_user: User = Depends(get_current_user),
):
    domains_list: list[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains_list = resolved or None

    video = get_random_video_record(
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
        return response.not_found('未找到符合条件的视频')

    detail = get_video_detail(current_user.id, video.id)
    return response.success(detail)
