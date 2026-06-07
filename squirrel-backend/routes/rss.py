import logging
from threading import Thread
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, SecretStr

from common import response
from models.user import User
from services import rss_service
from utils.jwt_helper import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rss", tags=["rss"])


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


@router.get("/accounts")
def list_rss_accounts(current_user: User = Depends(get_current_user)):
    return response.success({"data": rss_service.list_accounts(current_user.id)})


@router.post("/accounts")
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
            sync_entry_limit=req.sync_entry_limit,
        )
    except rss_service.RssServiceError as exc:
        return response.param_error(str(exc))
    return response.success(account)


@router.put("/accounts/{account_id}")
def update_rss_account(
    account_id: int,
    req: RssAccountUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    payload = req.model_dump(exclude_unset=True)
    credential = payload.pop("credential", None)
    if credential is not None:
        payload["credential"] = credential.get_secret_value()
    try:
        account = rss_service.update_account(current_user.id, account_id, **payload)
    except rss_service.RssServiceError as exc:
        return response.param_error(str(exc))
    if account is None:
        return response.not_found("RSS 账号不存在")
    return response.success(account)


@router.delete("/accounts/{account_id}")
def delete_rss_account(account_id: int, current_user: User = Depends(get_current_user)):
    if not rss_service.delete_account(current_user.id, account_id):
        return response.not_found("RSS 账号不存在")
    return response.success()


@router.post("/accounts/test")
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
        # API boundary -- convert to HTTP error response
        return response.error(f"RSS 服务连接失败: {exc}")
    return response.success(result)


@router.post("/accounts/{account_id}/test")
def test_rss_account(account_id: int, current_user: User = Depends(get_current_user)):
    try:
        result = rss_service.test_account(current_user.id, account_id)
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        return response.error(f"RSS 服务连接失败: {exc}")
    if result is None:
        return response.not_found("RSS 账号不存在")
    return response.success(result)


@router.post("/accounts/{account_id}/sync")
def sync_rss_account(
    account_id: int,
    entry_limit: int | None = Query(None, ge=1, alias="entryLimit"),
    current_user: User = Depends(get_current_user),
):
    try:
        rss_service.sync_account(current_user.id, account_id, entry_limit=entry_limit)
    except rss_service.RssServiceError as exc:
        return response.param_error(str(exc))
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        return response.error(f"RSS 同步失败: {exc}")
    return response.success(None)


@router.post("/accounts/{account_id}/sync/start")
def start_rss_sync(
    account_id: int,
    entry_limit: int | None = Query(None, ge=1, alias="entryLimit"),
    force_full_sync: bool = Query(False, alias="forceFullSync"),
    current_user: User = Depends(get_current_user),
):
    progress = rss_service.get_sync_progress(current_user.id, account_id)
    if progress is None:
        return response.not_found("RSS 账号不存在")
    if progress.get("running"):
        return response.param_error("RSS account sync is already running")

    user_id = current_user.id

    def _bg_sync():
        try:
            rss_service.sync_account(user_id, account_id, entry_limit=entry_limit, force_full_sync=force_full_sync)
        except rss_service.RssServiceError:
            pass
        except Exception:
            # task boundary -- prevent single failure from crashing request
            logger.exception("Background RSS sync failed for account_id=%s", account_id)

    thread = Thread(target=_bg_sync, daemon=True)
    thread.start()
    return response.success({"started": True, "account_id": account_id})


@router.get("/accounts/{account_id}/sync/status")
def get_rss_sync_status(account_id: int, current_user: User = Depends(get_current_user)):
    progress = rss_service.get_sync_progress(current_user.id, account_id)
    if progress is None:
        return response.not_found("RSS 账号不存在")
    return response.success(progress)


class RssFeedSubscribeRequest(BaseModel):
    accountId: int
    feedUrl: str
    category: str | None = None


class RssFeedUnsubscribeRequest(BaseModel):
    accountId: int


@router.post("/feeds/subscribe")
def subscribe_rss_feed(
    req: RssFeedSubscribeRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        feed = rss_service.subscribe_feed(
            current_user.id,
            account_id=req.accountId,
            feed_url=req.feedUrl,
            category=req.category,
        )
    except rss_service.RssServiceError as exc:
        return response.param_error(str(exc))
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        return response.error(f"RSS 订阅失败: {exc}")
    return response.success(feed)


@router.delete("/feeds/{feed_id}")
def unsubscribe_rss_feed(
    feed_id: int,
    account_id: int = Query(..., alias="accountId"),
    current_user: User = Depends(get_current_user),
):
    try:
        if not rss_service.unsubscribe_feed(current_user.id, account_id, feed_id):
            return response.not_found("RSS 订阅源不存在")
    except rss_service.RssServiceError as exc:
        return response.param_error(str(exc))
    return response.success()


@router.post("/feeds/{feed_id}/sync")
def sync_rss_feed(
    feed_id: int,
    entry_limit: int = Query(50, ge=1, le=500, alias="entryLimit"),
    current_user: User = Depends(get_current_user),
):
    try:
        result = rss_service.sync_feed(current_user.id, feed_id, entry_limit=entry_limit)
    except rss_service.RssServiceError as exc:
        return response.param_error(str(exc))
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        return response.error(f"RSS 同步失败: {exc}")
    return response.success(result)


@router.patch("/feeds/{feed_id}")
def patch_rss_feed(
    feed_id: int,
    req: dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    try:
        feed = rss_service.update_feed(current_user.id, feed_id, **req)
    except rss_service.RssServiceError as exc:
        return response.param_error(str(exc))
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        return response.error(f"更新订阅源失败: {exc}")
    return response.success(feed)


@router.post("/feeds/{feed_id}/read")
def mark_rss_feed_as_read(
    feed_id: int,
    current_user: User = Depends(get_current_user),
):
    return response.success(rss_service.mark_feed_as_read(current_user.id, feed_id))


@router.get("/feeds")
def list_rss_feeds(
    account_id: int | None = Query(None, alias="accountId"),
    current_user: User = Depends(get_current_user),
):
    return response.success({"data": rss_service.list_feeds(current_user.id, account_id)})


@router.get("/entries")
def list_rss_entries(
    account_id: int | None = Query(None, alias="accountId"),
    feed_id: int | None = Query(None, alias="feedId"),
    is_read: bool | None = Query(None, alias="isRead"),
    is_starred: bool | None = Query(None, alias="isStarred"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(get_current_user),
):
    return response.success(rss_service.list_entries(
        current_user.id,
        account_id=account_id,
        feed_id=feed_id,
        is_read=is_read,
        is_starred=is_starred,
        page=page,
        page_size=page_size,
    ))


class RssEntryUpdateRequest(BaseModel):
    isRead: bool | None = None
    isStarred: bool | None = None


class RssEntriesBulkUpdateRequest(BaseModel):
    entryIds: list[int]
    isRead: bool


@router.patch("/entries/bulk")
def update_rss_entries_bulk(
    req: RssEntriesBulkUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    return response.success(rss_service.update_entries_read_status(
        current_user.id,
        req.entryIds,
        is_read=req.isRead,
    ))


@router.patch("/entries/{entry_id}")
def update_rss_entry(
    entry_id: int,
    req: RssEntryUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    entry = rss_service.update_entry(
        current_user.id,
        entry_id,
        is_read=req.isRead,
        is_starred=req.isStarred,
    )
    if entry is None:
        return response.not_found("RSS 文章不存在")
    return response.success(entry)


@router.post("/entries/{entry_id}/view")
def record_rss_entry_view(
    entry_id: int,
    current_user: User = Depends(get_current_user),
):
    rss_service.record_entry_view(current_user.id, entry_id)
    return response.success()


@router.get("/entries/recently-viewed")
def list_recently_viewed(
    current_user: User = Depends(get_current_user),
):
    return response.success({"data": rss_service.list_recently_viewed(current_user.id)})
