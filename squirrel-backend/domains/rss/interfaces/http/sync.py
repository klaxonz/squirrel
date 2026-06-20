import logging
from threading import Thread

from fastapi import APIRouter, Depends, Query

from domains.rss.application.services.client._base import RssServiceError
from domains.rss.application.services.service import RssService
from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from infrastructure.http import response

from .dependencies import get_rss_service

logger = logging.getLogger(__name__)
router = APIRouter()


class RssSyncStartQuery:
    def __init__(
        self,
        entry_limit: int | None = Query(None, ge=1, alias='entryLimit'),
        force_full_sync: bool = Query(False, alias='forceFullSync'),
    ) -> None:
        self.entry_limit = entry_limit
        self.force_full_sync = force_full_sync


@router.post('/accounts/{account_id}/sync')
def sync_rss_account(
    account_id: int,
    entry_limit: int | None = Query(None, ge=1, alias='entryLimit'),
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    try:
        svc.sync_account(current_user.id, account_id, entry_limit=entry_limit)
    except RssServiceError as exc:
        return response.param_error(str(exc))
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        return response.error(f'RSS 同步失败: {exc}')
    return response.success(None)


@router.post('/accounts/{account_id}/sync/start')
def start_rss_sync(
    account_id: int,
    params: RssSyncStartQuery = Depends(),
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    progress = svc.get_sync_progress(current_user.id, account_id)
    if progress is None:
        return response.not_found('RSS 账号不存在')
    if progress.get('running'):
        return response.param_error('RSS account sync is already running')

    user_id = current_user.id
    entry_limit = params.entry_limit
    force_full_sync = params.force_full_sync

    def _bg_sync():
        try:
            svc.sync_account(user_id, account_id, entry_limit=entry_limit, force_full_sync=force_full_sync)
        except RssServiceError:
            pass
        except Exception:
            # task boundary -- prevent single failure from crashing request
            logger.exception('Background RSS sync failed for account_id=%s', account_id)

    thread = Thread(target=_bg_sync, daemon=True)
    thread.start()
    return response.success({'started': True, 'account_id': account_id})


@router.get('/accounts/{account_id}/sync/status')
def get_rss_sync_status(
    account_id: int, current_user: CurrentUserDto = Depends(get_current_user), svc: RssService = Depends(get_rss_service)
):
    progress = svc.get_sync_progress(current_user.id, account_id)
    if progress is None:
        return response.not_found('RSS 账号不存在')
    return response.success(progress)


@router.post('/feeds/{feed_id}/sync')
def sync_rss_feed(
    feed_id: int,
    entry_limit: int = Query(50, ge=1, le=500, alias='entryLimit'),
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    try:
        result = svc.sync_feed(current_user.id, feed_id, entry_limit=entry_limit)
    except RssServiceError as exc:
        return response.param_error(str(exc))
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        return response.error(f'RSS 同步失败: {exc}')
    return response.success(result)
