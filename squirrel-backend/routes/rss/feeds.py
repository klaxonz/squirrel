from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from common import response
from models.user import User
from services.rss.client._base import RssServiceError
from services.rss.service import RssService
from services.user.auth import get_current_user

from .dependencies import get_rss_service

router = APIRouter()


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
    svc: RssService = Depends(get_rss_service),
):
    try:
        feed = svc.subscribe_feed(
            current_user.id,
            account_id=req.accountId,
            feed_url=req.feedUrl,
            category=req.category,
        )
    except RssServiceError as exc:
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
    svc: RssService = Depends(get_rss_service),
):
    try:
        if not svc.unsubscribe_feed(current_user.id, account_id, feed_id):
            return response.not_found("RSS 订阅源不存在")
    except RssServiceError as exc:
        return response.param_error(str(exc))
    return response.success()


@router.patch("/feeds/{feed_id}")
def patch_rss_feed(
    feed_id: int,
    req: dict[str, Any],
    current_user: User = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    try:
        feed = svc.update_feed(current_user.id, feed_id, **req)
    except RssServiceError as exc:
        return response.param_error(str(exc))
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        return response.error(f"更新订阅源失败: {exc}")
    return response.success(feed)


@router.post("/feeds/{feed_id}/read")
def mark_rss_feed_as_read(
    feed_id: int,
    current_user: User = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    return response.success(svc.mark_feed_as_read(current_user.id, feed_id))


@router.get("/feeds")
def list_rss_feeds(
    account_id: int | None = Query(None, alias="accountId"),
    current_user: User = Depends(get_current_user),
    svc: RssService = Depends(get_rss_service),
):
    return response.success({"data": svc.list_feeds(current_user.id, account_id)})
