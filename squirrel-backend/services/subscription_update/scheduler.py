import logging
from typing import List, Optional, Dict
from sqlalchemy import select, func
from core.database import get_session
from core.cache import redis_client
from models.subscription import Subscription
from services import message_service
from queues.duplicate_checker import create_simple_checker
from queues.direct_producer import direct_domain_producer
from queues.queue_config import get_queue_config, QueueType, QueueMode
from utils import url_helper
from utils.site_catalog import SiteCatalog
from .models import SubscriptionUpdateRequest, UpdateTrigger, UpdateMode
from .orchestrator import orchestrator

logger = logging.getLogger()


class SubscriptionScheduler:
    """Subscription update scheduler."""
    
    def schedule_one(
        self,
        subscription_id: int,
        url: str,
        trigger: UpdateTrigger = UpdateTrigger.MANUAL,
        mode: UpdateMode = UpdateMode.SMART,
        user_id: Optional[int] = None,
        force: bool = False,
        trace_id: Optional[str] = None
    ) -> bool:
        domain = url_helper.extract_top_level_domain(url)
        if not SiteCatalog.is_site_enabled(domain=domain):
            logger.info(f"Skip scheduling subscription {subscription_id} because site is disabled: {domain}")
            return False

        request = SubscriptionUpdateRequest(
            subscription_id=subscription_id,
            url=url,
            trigger=trigger,
            mode=mode,
            user_id=user_id,
            force=force,
            trace_id=trace_id
        )
        
        result = orchestrator.update(request)
        return result.success
    
    def schedule_batch(
        self,
        subscription_ids: List[int],
        trigger: UpdateTrigger = UpdateTrigger.SCHEDULED
    ) -> tuple[int, int]:

        success_count = 0
        error_count = 0
        
        with get_session() as session:
            subscriptions = session.scalars(
                select(Subscription)
                .where(
                    Subscription.id.in_(subscription_ids),
                    Subscription.is_deleted == False
                )
            ).all()
            
            for sub in subscriptions:
                if self.schedule_one(sub.id, sub.url, trigger):
                    success_count += 1
                else:
                    error_count += 1
        
        return success_count, error_count
    
    def enqueue_all_active(
        self, 
        trigger: UpdateTrigger = UpdateTrigger.SCHEDULED,
        mode: UpdateMode = UpdateMode.INCREMENTAL
    ) -> tuple[int, int]:

        subscriptions = self._fetch_all_active()
        
        if not subscriptions:
            logger.info("No active subscriptions to enqueue")
            return 0, 0
        
        logger.info(f"Enqueuing {len(subscriptions)} active subscriptions (mode={mode.value})")
        
        grouped = self._group_by_domain(subscriptions)
        
        success_count = 0
        error_count = 0
        
        for domain, subs in grouped.items():
            logger.info(f"Processing {len(subs)} subscriptions for domain: {domain}")
            
            last_subscription_id = self._get_offset(domain, mode)
            
            reordered_subs = self._reorder_by_offset(subs, last_subscription_id)
            
            logger.info(f"Domain {domain} starting from subscription_id={reordered_subs[0].id if reordered_subs else 'N/A'}")
            
            for sub in reordered_subs:
                try:
                    enqueued = self._enqueue_subscription_update(sub, trigger, mode, domain)
                    if enqueued:
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to enqueue subscription {sub.id}: {e}", exc_info=True)
                    error_count += 1
        
        logger.info(f"Enqueue completed: success={success_count}, failed={error_count}")
        return success_count, error_count

    @staticmethod
    def _count_active_subscriptions() -> int:
        """Count active subscriptions."""
        with get_session() as session:
            count = session.execute(
                select(func.count(Subscription.id))
                .where(Subscription.is_deleted == False)
            ).scalar() or 0
            return count

    @staticmethod
    def _fetch_all_active() -> List[Subscription]:
        """Fetch all active subscriptions."""
        with get_session() as session:
            subscriptions = session.scalars(
                select(Subscription)
                .where(Subscription.is_deleted == False)
                .order_by(Subscription.id.desc())
            ).all()
            return list(subscriptions)

    @staticmethod
    def _group_by_domain(subscriptions: List[Subscription]) -> Dict[str, List[Subscription]]:
        """Group subscriptions by domain."""
        grouped = {}
        for sub in subscriptions:
            try:
                domain = url_helper.extract_top_level_domain(sub.url)
                if domain not in grouped:
                    grouped[domain] = []
                grouped[domain].append(sub)
            except Exception as e:
                logger.warning(f"Failed to extract domain from {sub.url}: {e}")
                if 'unknown' not in grouped:
                    grouped['unknown'] = []
                grouped['unknown'].append(sub)
        return grouped
    
    @staticmethod
    def _get_offset_key(domain: str, mode: UpdateMode) -> str:
        """Return the Redis key used for offsets."""
        return f"subscription:update:offset:{domain}:{mode.value}"
    
    @staticmethod
    def _get_offset(domain: str, mode: UpdateMode) -> int:
        """Fetch the last processed subscription_id for the domain/mode."""
        key = SubscriptionScheduler._get_offset_key(domain, mode)
        offset = redis_client.get(key)
        return int(offset) if offset else 0
    
    @staticmethod
    def update_offset(domain: str, mode: UpdateMode, subscription_id: int):
        """Update offset; called after enqueueing a subscription."""
        key = SubscriptionScheduler._get_offset_key(domain, mode)
        # Set TTL to 7 days to avoid accumulating keys.
        redis_client.setex(key, 7 * 24 * 3600, subscription_id)
        logger.debug(f"Updated offset for {domain}:{mode.value} to subscription_id={subscription_id}")
    
    @staticmethod
    def _reorder_by_offset(subscriptions: List[Subscription], last_subscription_id: int) -> List[Subscription]:
        """Reorder subscriptions based on the offset in descending-id order."""
        if last_subscription_id == 0:
            return subscriptions
        
        smaller_than_offset = []
        larger_or_equal = []
        
        for sub in subscriptions:
            if sub.id < last_subscription_id:
                smaller_than_offset.append(sub)
            else:
                larger_or_equal.append(sub)
        
        result = smaller_than_offset + larger_or_equal
        
        if result:
            logger.debug(
                f"Reordered subscriptions (clockwise): from {result[0].id} to {result[-1].id} "
                f"(last_offset={last_subscription_id})"
            )
        
        return result
    
    @staticmethod
    def _enqueue_subscription_update(
        sub: Subscription, 
        trigger: UpdateTrigger, 
        mode: UpdateMode, 
        domain: Optional[str] = None
    ) -> bool:
        """
        将订阅更新任务加入域队列
        
        Args:
            sub: 订阅对象
            trigger: 更新触发器
            mode: 更新模式
            domain: 域名（用于offset更新）
            
        Returns:
            是否成功入队
        """
        if domain and not SiteCatalog.is_site_enabled(domain=domain):
            logger.debug(f"Skip enqueue for disabled site: subscription_id={sub.id}, domain={domain}")
            return False

        content = {
            'subscription_id': sub.id,
            'url': sub.url,
            'mode': mode.value,
            'user_id': None,
            'force': False,
            'domain': domain  # include domain for offset updates
        }
        
        message = message_service.create_message(content)
        message_dict = message.to_dict()
        
        # 确定优先级
        if trigger == UpdateTrigger.MANUAL:
            priority = "manual"
        elif mode == UpdateMode.FULL:
            priority = "full"
        else:
            priority = "incr"
        
        # Duplicate checks are only applied for scheduled triggers.
        if trigger == UpdateTrigger.SCHEDULED:
            import json
            
            # 构建域队列名称用于去重检查
            url_domain = url_helper.extract_top_level_domain(sub.url)
            config = get_queue_config()
            site = config.get_site_by_domain(url_domain)
            
            if not site:
                logger.error(f"Unsupported domain: {url_domain}, subscription_id={sub.id}")
                return False
            
            mode_mapping = {"manual": QueueMode.MANUAL, "incr": QueueMode.INCREMENTAL, "full": QueueMode.FULL}
            queue_name = config.build_queue_name(QueueType.SUBSCRIPTION_UPDATE, site, mode_mapping[priority])
            
            checker = create_simple_checker(
                queue_name=queue_name,
                key_fn=lambda msg: (
                    json.loads(msg['body'])['subscription_id'],
                    json.loads(msg['body'])['mode']
                )
            )
            
            if checker.is_duplicate(message_dict):
                logger.debug(f"Skipped duplicate subscription {sub.id} (mode={mode.value})")
                return False
        
        # 使用新的直接域队列生产者
        try:
            direct_domain_producer.send_subscription_update(message_dict, sub.url, priority)
            logger.debug(f"Enqueued subscription {sub.id} (priority={priority}, mode={mode.value})")
            return True
        except ValueError as e:
            logger.error(f"Failed to enqueue subscription update: {e}, subscription_id={sub.id}")
            return False


scheduler = SubscriptionScheduler()
