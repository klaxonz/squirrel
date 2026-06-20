import logging

from fastapi import APIRouter, Depends, Query

from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from domains.video.application.services.listing.service import VideoListService
from domains.video.interfaces.http.dependencies import get_video_list_service
from domains.video.interfaces.http.query_params import VideoListQuery
from infrastructure.http import response
from infrastructure.site_catalog.catalog import SiteCatalog

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get('/detail')
def get_video(
    video_id: int = Query(None, description='视频ID'),
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: VideoListService = Depends(get_video_list_service),
):
    video = svc.get_video(current_user.id, video_id)
    return response.success(video)


@router.get('/list')
def get_videos(
    params: VideoListQuery = Depends(),
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: VideoListService = Depends(get_video_list_service),
):
    domains_list: list[str] | None = None
    if params.site:
        resolved = SiteCatalog.resolve_domains(params.site)
        domains_list = resolved or None

    videos, next_cursor = svc.list_videos(
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
