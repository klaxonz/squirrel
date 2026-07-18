"""Featured videos for the home page hero.

Returns a small set of videos suitable for the cinema hero.
Selection favours videos that *have thumbnails* and come from the user's
active subscriptions so the result feels personal.
"""

from fastapi import APIRouter, Depends, Query

from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from domains.video.application.services.featured import VideoFeaturedService
from domains.video.interfaces.http.dependencies import get_featured_service
from infrastructure.http import response

router = APIRouter()


@router.get('/featured')
def get_featured(
    stable: bool = Query(False, description='Return a deterministic selection for visual verification.'),
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: VideoFeaturedService = Depends(get_featured_service),
):
    videos = svc.get_featured_videos(current_user.id, stable=stable)
    return response.success(videos)
