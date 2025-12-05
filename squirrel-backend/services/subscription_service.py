from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.sql import text
from core.database import get_session
from crawl import SubscriptionMeta
from schemas.subscription.dto.subscription_dto import SubscriptionDto
from models.links import UserSubscription
from models.message import Message
from models.subscription import Subscription, ContentType
from services import user_config_service
from sqlfile.subscription_sql import get_subscriptions_count_sql, get_subscriptions_sql, get_subscription_sql
from utils.sql_parser import parse_dynamic_sql


def _detect_subscription_type(url: str) -> str:
    """检测订阅类型：播放列表或频道"""
    # YouTube 播放列表检测
    if 'youtube.com' in url or 'youtu.be' in url:
        if 'list=' in url or '/playlist?' in url:
            return ContentType.PLAYLIST
    
    # Bilibili 播放列表检测（收藏夹、合集）
    if 'bilibili.com' in url:
        if '/favlist' in url or 'fid=' in url:
            return ContentType.PLAYLIST
        if '/season/' in url or 'season_id=' in url:
            return ContentType.PLAYLIST
    
    # 默认为频道
    return ContentType.CHANNEL


def get_subscription_by_id(subscription_id: int):
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        return subscription


def get_subscription_by_url_and_name(url: str, name: str):
    with get_session() as session:
        subscription = session.scalars(select(Subscription).where(
            Subscription.url == url,
            Subscription.name == name
        )).first()
        return subscription


def get_active_user_subscription_by_url(user_id: int, url: str):
    with get_session() as session:
        subscription = session.execute(
            select(Subscription)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                Subscription.url == url,
                Subscription.is_deleted == False,
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted == False,
            )
        ).scalar_one_or_none()
        return subscription


def create_subscription(user_id: int, subscribe_info: SubscriptionMeta):
    with get_session() as session:
        subscription = get_subscription_by_url_and_name(url=subscribe_info.url, name=subscribe_info.name)
        if subscription:
            return subscription
        else:
            # 检测订阅类型：播放列表还是频道
            content_type = _detect_subscription_type(subscribe_info.url)
            
            subscription = Subscription(
                type=content_type,
                name=subscribe_info.name,
                url=subscribe_info.url,
                avatar=subscribe_info.avatar,
                description=None,
                extra_data={}
            )
            session.add(subscription)
        user_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription.id
            )).first()
        if not user_subscription:
            is_nsfw = False
            url = subscribe_info.url
            if 'pornhub.com' in url or 'javdb.com' in url:
                is_nsfw = True

            user_subscription = UserSubscription(
                user_id=user_id,
                subscription_id=subscription.id,
                is_nsfw=is_nsfw
            )
            session.add(user_subscription)
        session.commit()
    return subscription


def list_subscriptions(
        user_id: int,
        query: Optional[str],
        type: Optional[str],
        nsfw: str,
        page: int,
        page_size: int,
        domains: Optional[List[str]] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """Get subscription list"""

    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)

    with get_session() as session:
        params = {
            'user_id': user_id,
            'query': query,
            'type': type,
            'nsfw': nsfw,
            'show_nsfw': show_nsfw,
            'filter_nsfw_when_all': (nsfw == 'all' and not show_nsfw),
            'limit': page_size,
            'offset': (page - 1) * page_size
        }
        domain_filters = []
        if domains:
            for idx, d in enumerate(domains):
                key = f"domain_like_{idx}"
                params[key] = f"%{d}%"
                domain_filters.append(f"s.url like :{key}")
        
        count_sql = get_subscriptions_count_sql()
        dynamic_sql = parse_dynamic_sql(count_sql, params)
        if domain_filters:
            where_inject = " and (" + " or ".join(domain_filters) + ")"
            dynamic_sql = dynamic_sql.replace("order by", where_inject + "\norder by") if "order by" in dynamic_sql else dynamic_sql + where_inject
        total_count = session.execute(text(dynamic_sql), params).scalar()
        
        sql = get_subscriptions_sql()
        final_sql = parse_dynamic_sql(sql, params)
        if domain_filters:
            where_inject = " and (" + " or ".join(domain_filters) + ")"
            final_sql = final_sql.replace("order by", where_inject + "\norder by") if "order by" in final_sql else final_sql + where_inject

        results = session.execute(text(final_sql), params).all()
        subscriptions = [SubscriptionDto.model_validate(row._mapping).model_dump() for row in results]
            
        return subscriptions, total_count


def get_subscription_detail(subscription_id: int) -> SubscriptionDto:
    with get_session() as session:
        sql = get_subscription_sql()
        params = {
            'subscription_id': subscription_id
        }
        parse_dynamic_sql(sql, params)
        subscription = session.execute(text(sql), params).first()
        if not subscription:
            return None
        subscription = SubscriptionDto.model_validate(subscription._mapping)
        return subscription


def update_subscription(
        subscription_id: int,
        update_data: Dict[str, Any]
) -> bool:
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            return False

        for key, value in update_data.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)

        session.add(subscription)
        session.commit()
        return True


def toggle_status(subscription_id: int, status: bool, field: str) -> bool:
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            return False
        try:
            setattr(subscription, field, status)
            session.add(subscription)
            session.commit()
            return True
        except ValueError:
            return False


def toggle_nsfw_status(user_id: int, subscription_id: int, is_nsfw: bool) -> bool:
    with get_session() as session:
        user_sub = session.execute(
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted == 0
            )
        ).scalar_one_or_none()
        if not user_sub:
            return False
        
        user_sub.is_nsfw = is_nsfw
        session.commit()
        return True


def handle_subscribe_request(url: str, user_id: int) -> Subscription:
    """
    处理订阅请求（用于消息队列消费者）
    
    Args:
        url: 订阅URL
        user_id: 用户ID
        
    Returns:
        订阅对象
    """
    from crawl import SubscriptionFactory

    existing_subscription = get_active_user_subscription_by_url(user_id=user_id, url=url)
    if existing_subscription:
        return existing_subscription

    subscribe_channel = SubscriptionFactory.create_subscription(url)
    subscribe_info = subscribe_channel.get_subscribe_info()

    subscription = get_subscription_by_url_and_name(url, subscribe_info.name)
    
    if subscription:
        if not subscription.is_deleted:
            return subscription
        
        restore_subscription(subscription.id, user_id)
        return get_subscription_by_id(subscription.id)
    
    subscription = create_subscription(user_id, subscribe_info)
    return subscription


def restore_subscription(subscription_id: int, user_id: int) -> None:
    """
    恢复已删除的订阅
    
    Args:
        subscription_id: 订阅ID
        user_id: 用户ID
    """
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            return
        
        subscription.is_deleted = False
        
        user_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.user_id == user_id
            )
        ).first()
        
        if user_subscription and user_subscription.is_deleted:
            user_subscription.is_deleted = False
        elif not user_subscription:
            user_subscription = UserSubscription(
                subscription_id=subscription_id,
                user_id=user_id,
                is_deleted=False
            )
            session.add(user_subscription)
        
        session.commit()


def preview_user_subscriptions(site_name: str) -> Dict[str, Any]:
    """
    预览用户在指定站点的订阅列表（不实际导入）
    
    Args:
        site_name: 站点名称（如 'bilibili', 'youtube' 等）
        
    Returns:
        预览结果：{
            'site': 站点名称,
            'total': 找到的订阅数量,
            'subscriptions': 订阅列表 [{'url': '...', 'name': '...', 'avatar': '...'}, ...]
        }
    """
    import logging
    from crawl import get_importer_registry, SubscriptionFactory
    
    logger = logging.getLogger()
    
    try:
        # 获取对应站点的 importer
        importer_registry = get_importer_registry()
        importer_class = importer_registry.get_by_site(site_name)
        
        if not importer_class:
            raise ValueError(f"No importer found for site: {site_name}")
        
        # 创建 importer 实例并获取订阅列表
        importer = importer_class()
        subscription_urls = importer.get_user_subscriptions()
        
        logger.info(f"Found {len(subscription_urls)} subscriptions from {site_name} for preview")
        
        # 直接返回 URL 列表，不获取详细信息（避免耗时）
        return {
            'site': site_name,
            'total': len(subscription_urls),
            'urls': subscription_urls[:100]  # 预览最多显示前100个
        }
        
    except Exception as e:
        logger.error(f"Failed to preview subscriptions from {site_name}: {e}", exc_info=True)
        raise


def _enqueue_subscriptions_async(subscription_urls: List[str], user_id: int, site_name: str):
    """
    在后台线程中投递订阅任务到消息队列
    
    Args:
        subscription_urls: 订阅 URL 列表
        user_id: 用户ID
        site_name: 站点名称
    """
    import logging
    import json
    from common import constants
    from mq.producer import RedisStreamProducer
    
    logger = logging.getLogger()
    
    try:
        enqueued = 0
        producer = RedisStreamProducer()
        
        with get_session() as session:
            for url in subscription_urls:
                try:
                    # 创建订阅任务
                    task = {
                        "url": url,
                        "user_id": user_id
                    }
                    message = Message(body=json.dumps(task))
                    session.add(message)
                    session.flush()  # 获取 message.id
                    
                    # 投递到队列
                    dump_json = message.to_dict()
                    producer.send(constants.QUEUE_SUBSCRIBE, dump_json)
                    enqueued += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to enqueue subscription {url}: {e}")
            
            session.commit()
        
        logger.info(f"Enqueued {enqueued}/{len(subscription_urls)} subscription tasks from {site_name}")
        
    except Exception as e:
        logger.error(f"Failed to enqueue subscriptions from {site_name}: {e}", exc_info=True)


def import_user_subscriptions(site_name: str, user_id: int) -> Dict[str, Any]:
    """
    从指定站点导入用户的所有订阅（异步）
    
    Args:
        site_name: 站点名称（如 'bilibili', 'youtube' 等）
        user_id: 用户ID
        
    Returns:
        导入结果：{
            'total': 总数
        }
    """
    import logging
    import threading
    from crawl import get_importer_registry
    
    logger = logging.getLogger()
    
    try:
        # 获取对应站点的 importer
        importer_registry = get_importer_registry()
        importer_class = importer_registry.get_by_site(site_name)
        
        if not importer_class:
            raise ValueError(f"No importer found for site: {site_name}")
        
        # 创建 importer 实例并获取订阅列表
        importer = importer_class()
        subscription_urls = importer.get_user_subscriptions()
        
        logger.info(f"Found {len(subscription_urls)} subscriptions from {site_name}")
        
        # 在后台线程中投递消息
        thread = threading.Thread(
            target=_enqueue_subscriptions_async,
            args=(subscription_urls, user_id, site_name),
            daemon=True
        )
        thread.start()
        
        logger.info(f"Started background thread to enqueue {len(subscription_urls)} subscriptions")
        
        # 立即返回
        return {
            'total': len(subscription_urls)
        }
        
    except Exception as e:
        logger.error(f"Failed to import subscriptions from {site_name}: {e}", exc_info=True)
        raise
