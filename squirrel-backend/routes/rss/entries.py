from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from common import response
from models.user import User
from services.rss.service import RssService
from services.user.auth import get_current_user

from .dependencies import get_rss_service

router = APIRouter()


class RssEntryUpdateRequest(BaseModel):
    isRead: bool | None = None
    isStarred: bool | None = None


class RssEntriesBulkUpdateRequest(BaseModel):
    entryIds: list[int]
    isRead: bool


@router.get("/entries")
def list_rss_entries(
    account_id: int | None = Query(None, alias="accountId"),
    feed_id: int | None = Query(None, alias="feedId"),
    is_read: bool | None = Query(None, alias="isRead"),
    is_starred: bool | None = Query(None, alias="isStarred"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    return response.success(svc.list_entries(
        current_user.id,
        account_id=account_id,
        feed_id=feed_id,
        is_read=is_read,
        is_starred=is_starred,
        page=page,
        page_size=page_size,
    ))


@router.patch("/entries/bulk")
def update_rss_entries_bulk(
    req: RssEntriesBulkUpdateRequest,
    current_user: User = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    return response.success(svc.update_entries_read_status(
        current_user.id,
        req.entryIds,
        is_read=req.isRead,
    ))


@router.patch("/entries/{entry_id}")
def update_rss_entry(
    entry_id: int,
    req: RssEntryUpdateRequest,
    current_user: User = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    entry = svc.update_entry(
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
    svc: RssService = Depends(get_rss_service),
):
    svc.record_entry_view(current_user.id, entry_id)
    return response.success()


@router.get("/entries/recently-viewed")
def list_recently_viewed(
    current_user: User = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    return response.success({"data": svc.list_recently_viewed(current_user.id)})
