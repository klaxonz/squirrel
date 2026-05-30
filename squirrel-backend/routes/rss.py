from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, SecretStr

import common.response as response
from models.user import User
from services import rss_service
from utils.jwt_helper import get_current_user

router = APIRouter(prefix='/api/rss', tags=['rss'])


class RssAccountCreateRequest(BaseModel):
    provider: str
    name: str
    base_url: str
    username: Optional[str] = None
    credential: SecretStr
    enabled: bool = True


class RssAccountUpdateRequest(BaseModel):
    provider: Optional[str] = None
    name: Optional[str] = None
    base_url: Optional[str] = None
    username: Optional[str] = None
    credential: Optional[SecretStr] = None
    enabled: Optional[bool] = None


class RssAccountTestRequest(BaseModel):
    provider: str
    base_url: str
    username: Optional[str] = None
    credential: SecretStr


@router.get('/accounts')
def list_rss_accounts(current_user: User = Depends(get_current_user)):
    return response.success({'data': rss_service.list_accounts(current_user.id)})


@router.post('/accounts')
def create_rss_account(req: RssAccountCreateRequest, current_user: User = Depends(get_current_user)):
    try:
        account = rss_service.create_account(
            current_user.id,
            provider=req.provider,
            name=req.name,
            base_url=req.base_url,
            username=req.username,
            credential=req.credential.get_secret_value(),
            enabled=req.enabled,
        )
    except rss_service.RssServiceError as exc:
        return response.param_error(str(exc))
    return response.success(account)


@router.put('/accounts/{account_id}')
def update_rss_account(
    account_id: int,
    req: RssAccountUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    payload = req.model_dump(exclude_unset=True)
    credential = payload.pop('credential', None)
    if credential is not None:
        payload['credential'] = credential.get_secret_value()
    try:
        account = rss_service.update_account(current_user.id, account_id, **payload)
    except rss_service.RssServiceError as exc:
        return response.param_error(str(exc))
    if account is None:
        return response.not_found('RSS 账号不存在')
    return response.success(account)


@router.delete('/accounts/{account_id}')
def delete_rss_account(account_id: int, current_user: User = Depends(get_current_user)):
    if not rss_service.delete_account(current_user.id, account_id):
        return response.not_found('RSS 账号不存在')
    return response.success()


@router.post('/accounts/test')
def test_rss_account_config(req: RssAccountTestRequest, current_user: User = Depends(get_current_user)):
    try:
        result = rss_service.test_account_config(
            provider=req.provider,
            base_url=req.base_url,
            username=req.username,
            credential=req.credential.get_secret_value(),
        )
    except rss_service.RssServiceError as exc:
        return response.param_error(str(exc))
    except Exception as exc:
        return response.error(f'RSS 服务连接失败: {exc}')
    return response.success(result)


@router.post('/accounts/{account_id}/test')
def test_rss_account(account_id: int, current_user: User = Depends(get_current_user)):
    try:
        result = rss_service.test_account(current_user.id, account_id)
    except Exception as exc:
        return response.error(f'RSS 服务连接失败: {exc}')
    if result is None:
        return response.not_found('RSS 账号不存在')
    return response.success(result)


@router.post('/accounts/{account_id}/sync')
def sync_rss_account(
    account_id: int,
    entry_limit: int = Query(50, ge=1, le=200, alias='entryLimit'),
    current_user: User = Depends(get_current_user),
):
    try:
        result = rss_service.sync_account(current_user.id, account_id, entry_limit=entry_limit)
    except rss_service.RssServiceError as exc:
        return response.param_error(str(exc))
    except Exception as exc:
        return response.error(f'RSS 同步失败: {exc}')
    if result is None:
        return response.not_found('RSS 账号不存在')
    return response.success(result)


@router.get('/feeds')
def list_rss_feeds(
    account_id: Optional[int] = Query(None, alias='accountId'),
    current_user: User = Depends(get_current_user),
):
    return response.success({'data': rss_service.list_feeds(current_user.id, account_id)})


@router.get('/entries')
def list_rss_entries(
    account_id: Optional[int] = Query(None, alias='accountId'),
    feed_id: Optional[int] = Query(None, alias='feedId'),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100, alias='pageSize'),
    current_user: User = Depends(get_current_user),
):
    return response.success(rss_service.list_entries(
        current_user.id,
        account_id=account_id,
        feed_id=feed_id,
        page=page,
        page_size=page_size,
    ))
