import json
from datetime import datetime

from fastapi import APIRouter, Query, Depends
from sqlalchemy import select
from typing import Dict, Any, cast
import common.response as response
from core.database import get_session
from core.cache import RedisClient
from models.links import UserSubscription
from models.message import Message
from models.subscription import Subscription
from models.user import User
from schemas.subscription.request.subscription import SubscribeRequest, UnsubscribeRequest, ToggleStatusRequest
from services import subscription_service, message_service
from typing import List
from core.site_catalog import SiteCatalog
from core.cache import DistributedLock
from utils.jwt_helper import get_current_user
from mq.producer import RedisStreamProducer
from common import constants

router = APIRouter(tags=['订阅接口'])
client = RedisClient.get_instance().get_client()


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
        RedisStreamProducer().send(constants.QUEUE_SUBSCRIBE, dump_json)

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
def get_subscription_status(
        url: str = Query(None),
        current_user: User = Depends(get_current_user)
):
    is_subscribed = False
    with get_session() as session:
        if url:
            subscription = session.scalars(select(Subscription).where(Subscription.url == url)).first()
            if subscription:
                user_subscription = session.scalars(select(UserSubscription).where(
                    UserSubscription.user_id == current_user.id,
                    UserSubscription.subscription_id == subscription.id,
                    UserSubscription.is_deleted.is_(False))
                ).first()
                if user_subscription:
                    is_subscribed = True
    return response.success({
        "is_subscribed": is_subscribed
    })


@router.get("/api/subscription/detail/{subscription_id}")
def get_subscription_detail(subscription_id: int, current_user: User = Depends(get_current_user)):
    """获取订阅（频道）详情，附带当前用户的 is_nsfw 状态和统计字段"""
    sub = subscription_service.get_subscription_detail(subscription_id)
    if not sub:
        return response.not_found("订阅不存在")

    # 查询当前用户在该订阅下的 NSFW 设置
    with get_session() as session:
        user_sub = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == current_user.id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).first()

    data = sub.model_dump() if hasattr(sub, 'model_dump') else dict(sub)
    data["is_nsfw"] = bool(getattr(user_sub, 'is_nsfw', False))
    return response.success(data)


@router.get("/api/subscription/list")
def list_subscriptions(
        query: str = Query(None, description="搜索关键字"),
        type: str = Query(None, description="内容类型"),
        nsfw: str = Query("all", description="NSFW 过滤: all|yes|no", pattern=r"^(all|yes|no)$"),
        site: str = Query(None, description="站点过滤：例如 youtube、bilibili 等（支持别名）"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
        current_user: User = Depends(get_current_user)
):
    domains: List[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains = resolved if resolved else None

    subscriptions, total = subscription_service.list_subscriptions(
        current_user.id, query, type, nsfw, page, page_size, domains
    )
    return response.success({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "data": subscriptions
    })


@router.post("/api/subscription/{subscription_id}/refresh")
def refresh_subscription(subscription_id: int, current_user: User = Depends(get_current_user)):
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription or subscription.is_deleted:
            return response.not_found("订阅不存在")
        user_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == current_user.id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).first()
        if not user_subscription:
            return response.forbidden("无权操作该订阅")

    # 使用分布式锁作为“是否进行中”的唯一来源，避免仅依赖缓存状态
    lock_key = f"lock:subscription:update:{subscription_id}"
    lock = DistributedLock(lock_key)
    if lock.is_locked():
        return response.success({
            "status": "in_progress",
            "inProgress": True
        })

    # 组装消息体，使用 DB 最新数据
    sub_detail = subscription_service.get_subscription_detail(subscription_id)
    if not sub_detail:
        return response.not_found("订阅不存在")

    content = {
        "subscription_id": getattr(sub_detail, 'id', subscription_id),
        "url": getattr(sub_detail, 'url', ''),
        "total_videos": getattr(sub_detail, 'total_videos', 0),
        "total_extract": getattr(sub_detail, 'total_extract', 0),
        "is_nsfw": getattr(sub_detail, 'is_nsfw', False),
    }
    message = message_service.create_message(content)

    # 设置手动占用标记，减少与定时的竞争（短 TTL）
    client.set(f"{constants.REDIS_KEY_SUBSCRIPTION_MANUAL_PENDING_PREFIX}{subscription_id}", 1, ex=120)

    # 将手动更新投递到入口队列，随后由消费者按 domain 路由
    RedisStreamProducer().send(constants.QUEUE_SUBSCRIPTION_UPDATE_MANUAL, message.to_dict())

    # 返回入队成功结果
    return response.success({
        "status": "queued",
        "inProgress": False,
        "subscriptionId": subscription_id,
        "requestId": getattr(message, 'id', None),
        "queuedAt": datetime.utcnow().isoformat()
    })


@router.post("/api/subscription/toggle-auto-download")
def toggle_auto_download(req: ToggleStatusRequest):
    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_auto_download")
    return response.success({"success": success})


@router.post("/api/subscription/toggle-download-all")
def toggle_download_all(req: ToggleStatusRequest):
    success = subscription_service.toggle_status(req.subscription_id, req.is_enable, "is_download_all")
    return response.success({"success": success})


@router.post("/api/subscription/toggle-nsfw")
def toggle_nsfw(
        req: ToggleStatusRequest,
        current_user: User = Depends(get_current_user)
):
    success = subscription_service.toggle_nsfw_status(
        current_user.id,
        req.subscription_id,
        req.is_enable
    )
    return response.success({"success": success})
