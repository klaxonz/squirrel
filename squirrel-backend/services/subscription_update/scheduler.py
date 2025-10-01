"""
订阅更新调度器
提供定时任务和手动触发的统一接口
"""
import logging
from typing import List, Optional
from sqlalchemy import select, func
from core.database import get_session
from models.subscription import Subscription
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
    
    def schedule_all_active(self, batch_size: int = 100) -> tuple[int, int]:
        """
        调度所有活跃订阅（定时任务使用）
        
        Returns:
            (成功数, 失败数)
        """
        total = self._count_active_subscriptions()
        if total == 0:
            logger.info("No active subscriptions to schedule")
            return 0, 0
        
        logger.info(f"Scheduling {total} active subscriptions")
        
        success_count = 0
        error_count = 0
        offset = 0
        
        while offset < total:
            batch = self._fetch_batch(offset, batch_size)
            
            for sub in batch:
                if self.schedule_one(
                    sub.id,
                    sub.url,
                    trigger=UpdateTrigger.SCHEDULED,
                    mode=UpdateMode.SMART
                ):
                    success_count += 1
                else:
                    error_count += 1
            
            offset += batch_size
            logger.debug(f"Scheduled {min(offset, total)}/{total} subscriptions")
        
        logger.info(f"Scheduling completed: success={success_count}, failed={error_count}")
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


scheduler = SubscriptionScheduler()

