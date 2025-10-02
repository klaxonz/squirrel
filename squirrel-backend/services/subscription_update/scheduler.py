"""
订阅更新调度器
提供定时任务和手动触发的统一接口
"""
import logging
from typing import List, Optional, Dict
from sqlalchemy import select, func
from core.database import get_session
from models.subscription import Subscription
from services import message_service
from mq.producer import RedisStreamProducer
from utils import url_helper
from common import constants
from .models import SubscriptionUpdateRequest, UpdateTrigger, UpdateMode
from .orchestrator import orchestrator

logger = logging.getLogger()


class SubscriptionScheduler:
    """订阅更新调度器"""
    
    def schedule_one(
        self,
        subscription_id: int,
        url: str,
        trigger: UpdateTrigger = UpdateTrigger.MANUAL,
        mode: UpdateMode = UpdateMode.SMART,
        user_id: Optional[int] = None,
        force: bool = False
    ) -> bool:
        """
        调度单个订阅更新
        
        Returns:
            是否成功
        """
        request = SubscriptionUpdateRequest(
            subscription_id=subscription_id,
            url=url,
            trigger=trigger,
            mode=mode,
            user_id=user_id,
            force=force
        )
        
        result = orchestrator.update(request)
        return result.success
    
    def schedule_batch(
        self,
        subscription_ids: List[int],
        trigger: UpdateTrigger = UpdateTrigger.SCHEDULED
    ) -> tuple[int, int]:
        """
        批量调度订阅更新
        
        Returns:
            (成功数, 失败数)
        """
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
        """
        将所有活跃订阅发送到消息队列（按 domain 分发）
        
        Args:
            trigger: 触发类型
            mode: 更新模式（增量/全量）
            
        Returns:
            (成功数, 失败数)
        """
        subscriptions = self._fetch_all_active()
        
        if not subscriptions:
            logger.info("No active subscriptions to enqueue")
            return 0, 0
        
        logger.info(f"Enqueuing {len(subscriptions)} active subscriptions (mode={mode.value})")
        
        grouped = self._group_by_domain(subscriptions)
        
        success_count = 0
        error_count = 0
        
        for domain, subs in grouped.items():
            logger.info(f"Enqueuing {len(subs)} subscriptions for domain: {domain}")
            
            queue_name = self._get_queue_for_domain(domain, trigger, mode)
            
            for sub in subs:
                try:
                    self._enqueue_subscription_update(sub, trigger, mode, queue_name)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to enqueue subscription {sub.id}: {e}", exc_info=True)
                    error_count += 1
        
        logger.info(f"Enqueue completed: success={success_count}, failed={error_count}")
        return success_count, error_count

    @staticmethod
    def _count_active_subscriptions() -> int:
        """统计活跃订阅数"""
        with get_session() as session:
            count = session.execute(
                select(func.count(Subscription.id))
                .where(Subscription.is_deleted == False)
            ).scalar() or 0
            return count

    @staticmethod
    def _fetch_all_active() -> List[Subscription]:
        """一次性获取所有活跃订阅"""
        with get_session() as session:
            subscriptions = session.scalars(
                select(Subscription)
                .where(Subscription.is_deleted == False)
                .order_by(Subscription.id.asc())
            ).all()
            return list(subscriptions)

    @staticmethod
    def _fetch_batch(offset: int, limit: int) -> List[Subscription]:
        """分批获取订阅"""
        with get_session() as session:
            subscriptions = session.scalars(
                select(Subscription)
                .where(Subscription.is_deleted == False)
                .order_by(Subscription.id.asc())
                .limit(limit)
                .offset(offset)
            ).all()
            return list(subscriptions)
    
    @staticmethod
    def _group_by_domain(subscriptions: List[Subscription]) -> Dict[str, List[Subscription]]:
        """按 domain 分组订阅"""
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
    def _get_queue_for_domain(domain: str, trigger: UpdateTrigger, mode: UpdateMode = UpdateMode.INCREMENTAL) -> str:
        """获取 domain 对应的队列名"""
        if trigger == UpdateTrigger.MANUAL:
            queue_type = 'manual'
        elif mode == UpdateMode.FULL:
            queue_type = 'full'
        else:
            queue_type = 'incremental'
        
        if domain in constants.SUBSCRIPTION_UPDATE_DOMAIN_QUEUE_MAPPING:
            return constants.SUBSCRIPTION_UPDATE_DOMAIN_QUEUE_MAPPING[domain][queue_type]
        
        if trigger == UpdateTrigger.MANUAL:
            return constants.QUEUE_SUBSCRIPTION_UPDATE_MANUAL
        elif mode == UpdateMode.FULL:
            return constants.QUEUE_SUBSCRIPTION_UPDATE_FULL
        else:
            return constants.QUEUE_SUBSCRIPTION_UPDATE_INCREMENTAL
    
    @staticmethod
    def _enqueue_subscription_update(sub: Subscription, trigger: UpdateTrigger, mode: UpdateMode, queue_name: str):
        """将订阅更新任务发送到消息队列"""
        content = {
            'subscription_id': sub.id,
            'url': sub.url,
            'mode': mode.value,
            'user_id': None,
            'force': False
        }
        
        message = message_service.create_message(content)
        RedisStreamProducer().send(queue_name, message.to_dict())
        
        logger.debug(f"Enqueued subscription {sub.id} to {queue_name} (mode={mode.value})")


scheduler = SubscriptionScheduler()

