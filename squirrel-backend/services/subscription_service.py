from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.sql import text
from core.database import get_session
from crawl import SubscriptionMeta, SubscriptionImportItem
from schemas.subscription.dto.subscription_dto import SubscriptionDto
from models.links import UserSubscription
from models.message import Message
from models.subscription import Subscription, ContentType
from services import user_config_service
from services import subscription_sync_state_service
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


def get_active_user_subscription_url_map(user_id: int) -> Dict[str, int]:
    with get_session() as session:
        rows = session.execute(
            select(Subscription.url, Subscription.id)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                Subscription.is_deleted.is_(False),
                Subscription.url.is_not(None),
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
            )
        ).all()
        return {url: subscription_id for url, subscription_id in rows if url}


def create_subscription(user_id: int, subscribe_info: SubscriptionMeta):  
    with get_session() as session:
        subscription = get_subscription_by_url_and_name(url=subscribe_info.url, name=subscribe_info.name)
        if subscription:
            subscription_sync_state_service.ensure_sync_states(subscription.id, subscription.url)
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
            session.flush()
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
    subscription_sync_state_service.ensure_sync_states(subscription.id, subscription.url)
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


def list_subscription_options(user_id: int) -> List[Dict[str, Any]]:
    with get_session() as session:
        rows = session.execute(
            select(Subscription.id, Subscription.name, Subscription.avatar)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
            )
            .distinct()
            .order_by(Subscription.name.asc(), Subscription.id.asc())
        ).all()

    return [
        {
            'subscription_id': subscription_id,
            'subscription_name': subscription_name,
            'subscription_avatar': subscription_avatar,
        }
        for subscription_id, subscription_name, subscription_avatar in rows
    ]


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
    from crawl import get_subscription_registry, Subscription
    from urllib.parse import urlparse

    existing_subscription = get_active_user_subscription_by_url(user_id=user_id, url=url)
    if existing_subscription:
        return existing_subscription

    # 使用新的注册表 API 创建 Subscription
    subscription_registry = get_subscription_registry()
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower().split(':')[0]
    subscription_key = subscription_registry.get_by_domain(domain)
    if not subscription_key:
        raise ValueError(f"No subscription handler found for domain: {domain}")
    subscription_cls = subscription_registry.get(subscription_key)
    if not subscription_cls or not isinstance(subscription_cls, type):
        raise ValueError(f"Invalid subscription class for key: {subscription_key}")
    subscribe_channel: Subscription = subscription_cls(url=url)
    subscribe_info = subscribe_channel.get_subscribe_info()

    subscription = get_subscription_by_url_and_name(url, subscribe_info.name)

    if subscription:
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
    subscription = get_subscription_by_id(subscription_id)
    if subscription:
        subscription_sync_state_service.ensure_sync_states(subscription.id, subscription.url)


def create_subscribe_message(url: str, user_id: int) -> Dict[str, Any]:
    import json
    from common import constants
    from queues.producer import RedisStreamProducer

    with get_session() as session:
        task = {
            "url": url,
            "user_id": user_id
        }
        message = Message(body=json.dumps(task))
        session.add(message)
        session.commit()
        dump_json = message.to_dict()
        RedisStreamProducer().send(constants.QUEUE_SUBSCRIBE, dump_json)
    return dump_json


def unsubscribe_by_id(user_id: int, subscription_id: int) -> bool:
    with get_session() as session:
        if not subscription_id:
            return False

        subscription = session.scalars(
            select(Subscription).where(Subscription.id == subscription_id)
        ).first()

        if not subscription:
            return False

        user_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription.id,
                UserSubscription.is_deleted.is_(False),
            )
        ).first()

        if not user_subscription:
            return False

        user_subscription.is_deleted = True

        remaining_active_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.subscription_id == subscription.id,
                UserSubscription.is_deleted.is_(False),
            )
        ).first()

        should_deactivate_subscription = remaining_active_subscription is None
        if should_deactivate_subscription:
            subscription.is_deleted = True

        session.commit()

    if should_deactivate_subscription:
        subscription_sync_state_service.deactivate_sync_states(
            subscription_id,
            reason='no_active_subscribers',
        )

    return True


def check_subscription_status(user_id: int, url: str) -> bool:
    if not url:
        return False
    with get_session() as session:
        subscription = session.scalars(
            select(Subscription).where(Subscription.url == url)
        ).first()
        if subscription:
            user_subscription = session.scalars(
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.subscription_id == subscription.id,
                    UserSubscription.is_deleted.is_(False)
                )
            ).first()
            if user_subscription:
                return True
    return False


def get_user_subscription_nsfw(user_id: int, subscription_id: int) -> Optional[bool]:
    with get_session() as session:
        user_sub = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).first()
        if user_sub:
            return user_sub.is_nsfw
        return None


def verify_subscription_access(user_id: int, subscription_id: int) -> Tuple[Optional[Subscription], str]:
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription or subscription.is_deleted:
            return None, "not_found"

        user_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).first()
        if not user_subscription:
            return None, "forbidden"

        session.expunge(subscription)
        return subscription, "ok"


def _dedupe_import_items(subscriptions: List[SubscriptionImportItem]) -> List[SubscriptionImportItem]:
    seen_urls = set()
    result = []
    for sub in subscriptions:
        if not sub.url or sub.url in seen_urls:
            continue
        seen_urls.add(sub.url)
        result.append(sub)
    return result


def preview_user_subscriptions(site_name: str, user_id: int) -> Dict[str, Any]:
    """
    预览用户在指定站点的订阅列表（不实际导入）
    
    Args:
        site_name: 站点名称（如 'bilibili', 'youtube' 等）
        user_id: 用户ID

    Returns:
        预览结果：{
            'site': 站点名称,
            'total': 找到的订阅数量,
            'subscriptions': 订阅列表 [{'url': '...', 'name': '...', 'avatar': '...'}, ...]
        }
    """
    import logging
    from crawl import get_importer_registry
    
    logger = logging.getLogger()
    
    try:
        # 获取对应站点的 importer
        importer_registry = get_importer_registry()
        importer_plugin = importer_registry.get(site_name)
        
        if not importer_plugin:
            raise ValueError(f"No importer found for site: {site_name}")
        
        # 创建 importer 实例并获取订阅列表
        if isinstance(importer_plugin, type):
            importer = importer_plugin()
        else:
            importer = importer_plugin
        subscriptions = _dedupe_import_items(importer.get_user_subscriptions())

        logger.info(f"Found {len(subscriptions)} subscriptions from {site_name} for preview")

        imported_url_map = get_active_user_subscription_url_map(user_id)
        imported_count = 0

        preview_subscriptions = []
        for sub in subscriptions:
            data = sub.to_dict()
            is_imported = sub.url in imported_url_map
            data["is_imported"] = is_imported
            if is_imported:
                data["subscription_id"] = imported_url_map[sub.url]
                imported_count += 1
            preview_subscriptions.append(data)

        return {
            'site': site_name,
            'total': len(subscriptions),
            'imported': imported_count,
            'not_imported': len(subscriptions) - imported_count,
            'subscriptions': preview_subscriptions
        }

    except Exception as e:
        logger.error(f"Failed to preview subscriptions from {site_name}: {e}", exc_info=True)
        raise


def _enqueue_subscriptions_async(subscriptions: List[SubscriptionImportItem], user_id: int, site_name: str):
    """
    在后台线程中投递订阅任务到消息队列
    
    Args:
        subscriptions: 订阅列表
        user_id: 用户ID
        site_name: 站点名称
    """
    import logging
    import json
    from common import constants
    from queues.producer import RedisStreamProducer
    
    logger = logging.getLogger()
    
    try:
        enqueued = 0
        producer = RedisStreamProducer()

        with get_session() as session:
            for sub in subscriptions:
                url = sub.url
                try:
                    # 创建订阅任务
                    task = {
                        "url": url,
                        "name": sub.name,
                        "avatar": sub.avatar,
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

        logger.info(f"Enqueued {enqueued}/{len(subscriptions)} subscription tasks from {site_name}")
        
    except Exception as e:
        logger.error(f"Failed to enqueue subscriptions from {site_name}: {e}", exc_info=True)


def import_user_subscriptions(
    site_name: str,
    user_id: int,
    selected_urls: Optional[List[str]] = None
) -> Dict[str, Any]:
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
        importer_plugin = importer_registry.get(site_name)
        
        if not importer_plugin:
            raise ValueError(f"No importer found for site: {site_name}")
        
        # 创建 importer 实例并获取订阅列表
        if isinstance(importer_plugin, type):
            importer = importer_plugin()
        else:
            importer = importer_plugin
        all_subscriptions = _dedupe_import_items(importer.get_user_subscriptions())
        found_total = len(all_subscriptions)

        logger.info(f"Found {found_total} subscriptions from {site_name}")

        subscriptions = all_subscriptions
        if selected_urls is not None:
            selected_url_set = {u for u in selected_urls if u}
            subscriptions = [s for s in all_subscriptions if s.url in selected_url_set]
        selected_total = len(subscriptions)

        imported_url_map = get_active_user_subscription_url_map(user_id)
        imported_urls = set(imported_url_map.keys())
        to_import = [s for s in subscriptions if s.url not in imported_urls]

        # 在后台线程中投递消息
        if to_import:
            thread = threading.Thread(
                target=_enqueue_subscriptions_async,
                args=(to_import, user_id, site_name),
                daemon=True
            )
            thread.start()
            logger.info(f"Started background thread to enqueue {len(to_import)} subscriptions")
        else:
            logger.info("No new subscriptions to import")

        # 立即返回
        return {
            'total': len(to_import),
            'found': found_total,
            'selected': selected_total,
            'skipped': selected_total - len(to_import)
        }
        
    except Exception as e:
        logger.error(f"Failed to import subscriptions from {site_name}: {e}", exc_info=True)
        raise
