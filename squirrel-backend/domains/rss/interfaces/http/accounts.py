from fastapi import APIRouter, Depends
from pydantic import BaseModel, SecretStr

from domains.rss.application.services.client._base import RssServiceError
from domains.rss.application.services.service import RssService
from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from infrastructure.http import response

from .dependencies import get_rss_service

router = APIRouter()


class RssAccountCreateRequest(BaseModel):
    provider: str
    name: str
    base_url: str
    username: str | None = None
    credential: SecretStr
    enabled: bool = True
    sync_entry_limit: int | None = None


class RssAccountUpdateRequest(BaseModel):
    provider: str | None = None
    name: str | None = None
    base_url: str | None = None
    username: str | None = None
    credential: SecretStr | None = None
    enabled: bool | None = None
    sync_entry_limit: int | None = None


class RssAccountTestRequest(BaseModel):
    provider: str
    base_url: str
    username: str | None = None
    credential: SecretStr


@router.get('/accounts')
def list_rss_accounts(current_user: CurrentUserDto = Depends(get_current_user), svc: RssService = Depends(get_rss_service)):
    return response.success({'data': svc.list_accounts(current_user.id)})


@router.post('/accounts')
def create_rss_account(
    req: RssAccountCreateRequest,
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    try:
        account = svc.create_account(
            current_user.id,
            provider=req.provider,
            name=req.name,
            base_url=req.base_url,
            username=req.username,
            credential=req.credential.get_secret_value(),
            enabled=req.enabled,
            sync_entry_limit=req.sync_entry_limit,
        )
    except RssServiceError as exc:
        return response.param_error(str(exc))
    return response.success(account)


@router.put('/accounts/{account_id}')
def update_rss_account(
    account_id: int,
    req: RssAccountUpdateRequest,
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    payload = req.model_dump(exclude_unset=True)
    credential = payload.pop('credential', None)
    if credential is not None:
        payload['credential'] = credential.get_secret_value()
    try:
        account = svc.update_account(current_user.id, account_id, **payload)
    except RssServiceError as exc:
        return response.param_error(str(exc))
    if account is None:
        return response.not_found('RSS 账号不存在')
    return response.success(account)


@router.delete('/accounts/{account_id}')
def delete_rss_account(
    account_id: int, current_user: CurrentUserDto = Depends(get_current_user), svc: RssService = Depends(get_rss_service)
):
    if not svc.delete_account(current_user.id, account_id):
        return response.not_found('RSS 账号不存在')
    return response.success()


@router.post('/accounts/test')
def test_rss_account_config(
    req: RssAccountTestRequest,
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    try:
        result = svc.test_account_config(
            provider=req.provider,
            base_url=req.base_url,
            username=req.username,
            credential=req.credential.get_secret_value(),
        )
    except RssServiceError as exc:
        return response.param_error(str(exc))
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        return response.error(f'RSS 服务连接失败: {exc}')
    return response.success(result)


@router.post('/accounts/{account_id}/test')
def test_rss_account(
    account_id: int, current_user: CurrentUserDto = Depends(get_current_user), svc: RssService = Depends(get_rss_service)
):
    try:
        result = svc.test_account(current_user.id, account_id)
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        return response.error(f'RSS 服务连接失败: {exc}')
    if result is None:
        return response.not_found('RSS 账号不存在')
    return response.success(result)
