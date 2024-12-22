import json

from fastapi import APIRouter, Query
from sqlmodel import select

import common.response as response
from consumer import subscribe_task
from core.database import get_session
from models import Subscription
from models.message import Message
from schemas.subscription import (
    SubscribeRequest,
    UnsubscribeRequest,
    ToggleStatusRequest
)
from services.subscription_service import SubscriptionService

router = APIRouter(tags=['订阅接口'])


@router.post("/api/subscription/subscribe")
def subscribe_content(req: SubscribeRequest):
    """订阅新内容"""
    with get_session() as session:
        task = {"url": req.url}
        message = Message(
            body=json.dumps(task),
        )
        session.add(message)
        session.commit()

        message = session.exec(select(Message).where(Message.message_id == message.message_id)).first()
        dump_json = message.model_dump_json()
        subscribe_task.process_subscribe_message.send(dump_json)
        message.send_status = 'SENDING'
        session.refresh(message)

    return response.success()


@router.post("/api/subscription/unsubscribe")
def unsubscribe_content(req: UnsubscribeRequest):
    if req.subscription_id:
        # 通过id取消订阅
        with get_session() as session:
            subscription = session.exec(select(Subscription).where(Subscription.subscription_id == req.subscription_id)).first()
            if subscription:
                subscription.is_deleted = True
                session.commit()
    elif req.url:
        # 通过url取消订阅
        with get_session() as session:
            subscription = session.exec(select(Subscription).where(Subscription.content_url == req.url)).first()
            if subscription:
                subscription.is_deleted = True
                session.commit()
    return response.success()


@router.get("/api/subscription/list")
def list_subscriptions(
    query: str = Query(None, description="搜索关键字"),
    content_type: str = Query(None, description="内容类型"),
    status: str = Query(None, description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取订阅列表"""
    subscription_service = SubscriptionService()
    subscriptions, total = subscription_service.list_subscriptions(
        query, content_type, status, page, page_size
    )
    return response.success({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "data": subscriptions
    })


@router.post("/api/subscription/toggle-status")
def toggle_channel_status(req: ToggleStatusRequest):
    subscription_service = SubscriptionService()
    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_enable")
    return response.success({"success": success})


@router.post("/api/subscription/toggle-auto-download")
def toggle_auto_download(req: ToggleStatusRequest):
    subscription_service = SubscriptionService()
    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_auto_download")
    return response.success({"success": success})


@router.post("/api/subscription/toggle-download-all")
def toggle_download_all(req: ToggleStatusRequest):
    subscription_service = SubscriptionService()

    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_download_all")
    return response.success({"success": success})


@router.post("/api/subscription/toggle-extract-all")
def toggle_extract_all(req: ToggleStatusRequest):
    subscription_service = SubscriptionService()

    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_extract_all")
    return response.success({"success": success})


