from fastapi import APIRouter, Depends

from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from domains.video.application.services.creators.service import CreatorService
from infrastructure.database.session import get_session
from infrastructure.http import response

router = APIRouter(prefix='/api/creator', tags=['Creator API'])


def get_creator_service() -> CreatorService:
    return CreatorService(session_factory=get_session)


@router.get('/detail/{creator_id}')
def get_creator_detail(
    creator_id: int,
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: CreatorService = Depends(get_creator_service),
):
    del current_user  # auth gate only
    detail = svc.get_creator_detail(creator_id)
    if not detail:
        return response.not_found('创作者不存在')
    return response.success(detail)
