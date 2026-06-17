from fastapi import APIRouter, Depends

from domains.user.application.services.auth import get_current_user
from domains.user.application.services.config import UserConfigService
from domains.user.domain.models.user import User
from infrastructure.http import response

from .dependencies import get_config_service
from .schemas import UserConfigUpdate

router = APIRouter()

@router.get("/me/config")
async def get_user_config(
    current_user: User = Depends(get_current_user),
    cfg_svc: UserConfigService = Depends(get_config_service),
):
    settings = cfg_svc.get_config(current_user.id)
    return response.success(data=settings)


@router.put("/me/config")
async def update_user_config(
    config_data: UserConfigUpdate,
    current_user: User = Depends(get_current_user),
    cfg_svc: UserConfigService = Depends(get_config_service),
):
    updated = cfg_svc.update_config(
        user_id=current_user.id,
        new_settings=config_data.settings,
        merge=config_data.merge,
    )
    return response.success(data=updated, msg="配置更新成功")
