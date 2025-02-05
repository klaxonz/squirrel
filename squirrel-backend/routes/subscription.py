import json

from fastapi import APIRouter, Query, Depends
from sqlalchemy import select

import common.response as response
from consumer import subscribe_task
from core.database import get_session
from models.links import UserSubscription
from models.message import Message
from models.subscription import Subscription
from models.user import User
from schemas.subscription import (
    SubscribeRequest,
    UnsubscribeRequest,
    ToggleStatusRequest
)
from services import subscription_service
from utils.jwt_helper import get_current_user

router = APIRouter(tags=['订阅接口'])


@router.post("/api/subscription/subscribe")
def subscribe_content(req: SubscribeRequest, current_user: User = Depends(get_current_user)):
    with get_session() as session:
        task = {
            "url": req.url,
            "user_id": current_user.id
        }
        message = Message(body=json.dumps(task))
        session.add(message)
        session.commit()
        dump_json = message.to_dict()
        subscribe_task.process_subscribe_message.send(dump_json)

    return response.success()


@router.post("/api/subscription/unsubscribe")
def unsubscribe_content(req: UnsubscribeRequest, current_user: User = Depends(get_current_user)):
    with get_session() as session:
        if req.subscription_id:
            subscription_filter = Subscription.id == req.subscription_id
        elif req.url:
            subscription_filter = Subscription.url == req.url
        else:
            return response.error("Invalid request parameters")
        subscription = session.scalars(
            select(Subscription).where(subscription_filter)
        ).first()
        
        if subscription:
            user_subscription = session.scalars(
                select(UserSubscription).where(
                    UserSubscription.user_id == current_user.id,
                    UserSubscription.subscription_id == subscription.id
                )
            ).first()
            
            if user_subscription:
                user_subscription.is_deleted = True
                session.commit()
                
        return response.success()


@router.get("/api/subscription/status")
def subscribe_content(
        url: str = Query(None),
        current_user: User = Depends(get_current_user)
):
    is_subscribed = False
    with get_session() as session:
        if url:
            subscription = session.scalars(select(Subscription).where(Subscription.url == url)).first()
            if subscription:
                user_subscription = session.scalars(select(UserSubscription)).where(
                    UserSubscription.user_id == current_user.id).first()
                if user_subscription:
                    is_subscribed = True
    return response.success({
        "is_subscribed": is_subscribed
    })


@router.get("/api/subscription/list")
def list_subscriptions(
        query: str = Query(None, description="搜索关键字"),
        type: str = Query(None, description="内容类型"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
        current_user: User = Depends(get_current_user)
):
    subscriptions, total = subscription_service.list_subscriptions(current_user.id, query, type, page, page_size)
    return response.success({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "data": subscriptions
    })


@router.post("/api/subscription/toggle-auto-download")
def toggle_auto_download(req: ToggleStatusRequest):
    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_auto_download")
    return response.success({"success": success})


@router.post("/api/subscription/toggle-download-all")
def toggle_download_all(req: ToggleStatusRequest):
    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_download_all")
    return response.success({"success": success})


