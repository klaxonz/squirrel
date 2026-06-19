import logging

from fastapi import APIRouter, Depends, Query

from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from domains.video.application.services.listing.service import get_video as get_video_detail
from domains.video.application.services.listing.service import list_videos
from domains.video.interfaces.http.query_params import VideoListQuery
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
    params: VideoListQuery = Depends(),
    current_user: User = Depends(get_current_user),
):
    domains_list: list[str] | None = None
    if params.site:
        resolved = SiteCatalog.resolve_domains(params.site)
        domains_list = resolved or None

    if hasattr(current_user, '_cached_config'):
        logger.info('[Performance] Route: Using cached user config')

    videos, next_cursor = list_videos(
        current_user.id,
        params.query,
        params.subscription_id,
        params.category.value,
        params.sort_by.value,
        params.nsfw.value,
        domains_list,
        params.cursor,
        params.page_size,
        time_range=params.time_range.value,
        duration=params.duration.value,
        content_type=params.content_type.value,
        special=params.special.value,
    )

    return response.success(
        {
            'data': videos,
            'next_cursor': next_cursor,
            'has_more': next_cursor is not None,
        }
    )
