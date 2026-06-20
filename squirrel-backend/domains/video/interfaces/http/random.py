from fastapi import APIRouter, Depends

from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from domains.video.application.services.listing.service import VideoListService
from domains.video.application.services.random import VideoRandomService
from domains.video.interfaces.http.dependencies import get_video_list_service, get_video_random_service
from domains.video.interfaces.http.query_params import VideoRandomQuery
from infrastructure.http import response
from infrastructure.site_catalog.catalog import SiteCatalog

router = APIRouter()


@router.get('/random')
def get_random_video(
    params: VideoRandomQuery = Depends(),
    current_user: CurrentUserDto = Depends(get_current_user),
    random_svc: VideoRandomService = Depends(get_video_random_service),
    list_svc: VideoListService = Depends(get_video_list_service),
):
    domains_list: list[str] | None = None
    if params.site:
        resolved = SiteCatalog.resolve_domains(params.site)
        domains_list = resolved or None

    video = random_svc.get_random_video(
        current_user.id,
        category=params.category.value,
        subscription_id=params.subscription_id,
        nsfw=params.nsfw.value,
        domains=domains_list,
        query=params.query,
        time_range=params.time_range.value,
        duration=params.duration.value,
        content_type=params.content_type.value,
    )
    if not video:
        return response.not_found('未找到符合条件的视频')

    detail = list_svc.get_video(current_user.id, video.id)
    return response.success(detail)
