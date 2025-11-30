"""
订阅更新调度器
提供定时任务和手动触发的统一接口
"""
import logging
from typing import List, Optional, Dict
from sqlalchemy import select, func
from core.database import get_session
from core.cache import redis_client
from models.subscription import Subscription
from services import message_service
from mq.producer import RedisStreamProducer
from mq.duplicate_checker import create_simple_checker
from utils import url_helper
from utils.site_catalog import SiteCatalog
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
        force: bool = False,
        trace_id: Optional[str] = None
    ) -> bool:
        """
        调度单个订阅更新
        
        Returns:
            是否成功
        """
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
        将所有活跃订阅发送到消息队列（按 domain 分发，支持断点续传）
        
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
        
        # 按 domain 分组
        grouped = self._group_by_domain(subscriptions)
        
        success_count = 0
        error_count = 0
        
        for domain, subs in grouped.items():
            logger.info(f"Processing {len(subs)} subscriptions for domain: {domain}")
            
            # 从 Redis 获取上次处理的 offset
            last_subscription_id = self._get_offset(domain, mode)
            
            # 将订阅列表重新排序：从 offset 开始到末尾，然后从头到 offset（形成圆圈）
            reordered_subs = self._reorder_by_offset(subs, last_subscription_id)
            
            logger.info(f"Domain {domain} starting from subscription_id={reordered_subs[0].id if reordered_subs else 'N/A'}")
            
            queue_name = self._get_queue_for_domain(domain, trigger, mode)
            
            for sub in reordered_subs:
                try:
                    enqueued = self._enqueue_subscription_update(sub, trigger, mode, queue_name, domain)
                    if enqueued:
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
                .order_by(Subscription.id.desc())
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
    def _get_offset_key(domain: str, mode: UpdateMode) -> str:
        """获取偏移量的 Redis key"""
        return f"subscription:update:offset:{domain}:{mode.value}"
    
    @staticmethod
    def _get_offset(domain: str, mode: UpdateMode) -> int:
        """获取指定 domain 和 mode 的上次处理的 subscription_id"""
        key = SubscriptionScheduler._get_offset_key(domain, mode)
        offset = redis_client.get(key)
        return int(offset) if offset else 0
    
    @staticmethod
    def update_offset(domain: str, mode: UpdateMode, subscription_id: int):
        """
        更新偏移量（由 base.py 调用）
        在视频 URL 入队后调用此方法
        """
        key = SubscriptionScheduler._get_offset_key(domain, mode)
        # 设置过期时间为 7 天，避免 Redis 累积过多 key
        redis_client.setex(key, 7 * 24 * 3600, subscription_id)
        logger.debug(f"Updated offset for {domain}:{mode.value} to subscription_id={subscription_id}")
    
    @staticmethod
    def _reorder_by_offset(subscriptions: List[Subscription], last_subscription_id: int) -> List[Subscription]:
        """
        根据 offset 重新排序订阅列表（顺时针：从大 id 到小 id）
        形成圆圈效果：优先处理 id 大的（更新的订阅）
        
        Args:
            subscriptions: 订阅列表（已按 id desc 排序）
            last_subscription_id: 上次处理的 subscription_id
            
        Returns:
            重新排序后的订阅列表
        """
        if last_subscription_id == 0:
            # 没有 offset，直接返回原列表（从最大 id 开始）
            return subscriptions
        
        # 顺时针：从大到小处理
        # 找到 offset 位置，继续处理更小的 id
        smaller_than_offset = []  # id < offset（继续处理）
        larger_or_equal = []      # id >= offset（等会儿再处理）
        
        for sub in subscriptions:
            if sub.id < last_subscription_id:
                smaller_than_offset.append(sub)
            else:
                larger_or_equal.append(sub)
        
        # 从 offset 之后继续（更小的 id），然后回到最大的 id
        result = smaller_than_offset + larger_or_equal
        
        if result:
            logger.debug(
                f"Reordered subscriptions (clockwise): from {result[0].id} to {result[-1].id} "
                f"(last_offset={last_subscription_id})"
            )
        
        return result
    
    @staticmethod
    def _get_queue_for_domain(domain: str, trigger: UpdateTrigger, mode: UpdateMode = UpdateMode.INCREMENTAL) -> str:
        """获取 domain 对应的队列名"""
        from crawl import MetaRegistry
        
        if trigger == UpdateTrigger.MANUAL:
            queue_type = 'manual'
        elif mode == UpdateMode.FULL:
            queue_type = 'full'
        else:
            queue_type = 'incremental'
        
        # 检查该域名是否有注册的插件
        if MetaRegistry.get_meta_class(domain):
            return constants.get_subscription_update_queue(domain, queue_type)
        
        if trigger == UpdateTrigger.MANUAL:
            return constants.QUEUE_SUBSCRIPTION_UPDATE_MANUAL
        elif mode == UpdateMode.FULL:
            return constants.QUEUE_SUBSCRIPTION_UPDATE_FULL
        else:
            return constants.QUEUE_SUBSCRIPTION_UPDATE_INCREMENTAL
    
    @staticmethod
    def _enqueue_subscription_update(
        sub: Subscription, 
        trigger: UpdateTrigger, 
        mode: UpdateMode, 
        queue_name: str,
        domain: Optional[str] = None
    ) -> bool:
        """将订阅更新任务发送到消息队列"""
        if domain and not SiteCatalog.is_site_enabled(domain=domain):
            logger.debug(f"Skip enqueue for disabled site: subscription_id={sub.id}, domain={domain}")
            return False

        content = {
            'subscription_id': sub.id,
            'url': sub.url,
            'mode': mode.value,
            'user_id': None,
            'force': False,
            'domain': domain  # 传递 domain 信息，用于后续更新 offset
        }
        
        message = message_service.create_message(content)
        message_dict = message.to_dict()
        
        # 调用方决定是否检查重复
        # 策略：定时任务检查重复，手动触发不检查
        if trigger == UpdateTrigger.SCHEDULED:
            # 创建重复检测器，基于 subscription_id 和 mode 判断
            import json
            checker = create_simple_checker(
                queue_name=queue_name,
                key_fn=lambda msg: (
                    json.loads(msg['body'])['subscription_id'],
                    json.loads(msg['body'])['mode']
                )
            )
            
            # 检查队列中是否已存在，如果存在则跳过
            if checker.is_duplicate(message_dict):
                logger.debug(f"Skipped duplicate subscription {sub.id} for {queue_name} (mode={mode.value})")
                return
        
        # 发送消息
        RedisStreamProducer().send(queue_name, message_dict)
        logger.debug(f"Enqueued subscription {sub.id} to {queue_name} (mode={mode.value})")
        return True


scheduler = SubscriptionScheduler()

