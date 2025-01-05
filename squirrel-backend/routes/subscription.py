import json

from fastapi import APIRouter, Query
from sqlalchemy import select

import common.response as response
from consumer import subscribe_task
from core.database import get_session
from models.message import Message
from models.subscription import Subscription
from schemas.subscription import (
    SubscribeRequest,
    UnsubscribeRequest,
    ToggleStatusRequest
)
from services.subscription_service import subscription_service

router = APIRouter(tags=['订阅接口'])


@router.post("/api/subscription/subscribe")
def subscribe_content(req: SubscribeRequest):
    with get_session() as session:
        task = {"url": req.url}
        message = Message(
            body=json.dumps(task),
        )
        session.add(message)
        session.commit()

        message = session.scalars(select(Message).where(Message.id == message.id)).first()
        dump_json = message.to_dict()
        subscribe_task.process_subscribe_message.send(dump_json)
        message.send_status = 'SENDING'
        session.refresh(message)

    return response.success()


@router.post("/api/subscription/unsubscribe")
def unsubscribe_content(req: UnsubscribeRequest):
    if req.subscription_id:
        with get_session() as session:
            subscription = session.scalars(
                select(Subscription).where(Subscription.id == req.subscription_id)).first()
            if subscription:
                subscription.is_deleted = True
                session.commit()
    elif req.url:
        with get_session() as session:
            subscription = session.scalars(select(Subscription).where(Subscription.content_url == req.url)).first()
            if subscription:
                subscription.is_deleted = True
                session.commit()
    return response.success()


@router.get("/api/subscription/status")
def subscribe_content(url: str = Query(None)):
    is_subscribed = False
    with get_session() as session:
        if url:
            subscription = session.scalars(select(Subscription).where(Subscription.content_url == url)).first()
            if subscription:
                is_subscribed = True
    return response.success({
        "is_subscribed": is_subscribed
    })


@router.get("/api/subscription/list")
def list_subscriptions(
        query: str = Query(None, description="搜索关键字"),
        content_type: str = Query(None, description="内容类型"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    subscriptions, total = subscription_service.list_subscriptions(query, content_type, page, page_size)
    return response.success({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "data": subscriptions
    })


@router.post("/api/subscription/toggle-status")
def toggle_channel_status(req: ToggleStatusRequest):
    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_enable")
    return response.success({"success": success})


@router.post("/api/subscription/toggle-auto-download")
def toggle_auto_download(req: ToggleStatusRequest):
    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_auto_download")
    return response.success({"success": success})


@router.post("/api/subscription/toggle-download-all")
def toggle_download_all(req: ToggleStatusRequest):
    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_download_all")
    return response.success({"success": success})


@router.post("/api/subscription/toggle-extract-all")
def toggle_extract_all(req: ToggleStatusRequest):
    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_extract_all")
    return response.success({"success": success})
