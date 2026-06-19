from fastapi import APIRouter, Depends

from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from domains.video.application.services.listing.service import get_video as get_video_detail
from domains.video.application.services.random import get_random_video as get_random_video_record
from domains.video.interfaces.http.query_params import VideoRandomQuery
from infrastructure.http import response
from infrastructure.site_catalog.catalog import SiteCatalog

router = APIRouter()


@router.get('/random')
def get_random_video(
    params: VideoRandomQuery = Depends(),
    current_user: User = Depends(get_current_user),
):
    domains_list: list[str] | None = None
    if params.site:
        resolved = SiteCatalog.resolve_domains(params.site)
        domains_list = resolved or None

    video = get_random_video_record(
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

    detail = get_video_detail(current_user.id, video.id)
    return response.success(detail)
