"""订阅更新编排器
统一入口，负责协调整个更新流程
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from core.database import get_session
from models.links import UserSubscription
from services import subscription_sync_state_service
from utils import url_helper
from utils.metrics import metrics
from utils.site_catalog import SiteCatalog

from .models import SubscriptionUpdateRequest, SubscriptionUpdateResult
from .strategies.default_strategy import DefaultUpdateStrategy
from .strategies.registry import StrategyRegistry

if TYPE_CHECKING:
    from services.subscription_update.strategies.base import UpdateStrategy

logger = logging.getLogger(__name__)


class SubscriptionOrchestrator:
    """订阅更新编排器

    职责：
    1. 接收更新请求
    2. 选择合适的更新策略
    3. 执行更新流程
    4. 返回更新结果
    """

    def __init__(self):
        self.default_strategy = DefaultUpdateStrategy()

    def update(self, request: SubscriptionUpdateRequest) -> SubscriptionUpdateResult:
        """执行订阅更新

        Args:
            request: 更新请求

        Returns:
            更新结果

        """
        try:
            domain = url_helper.extract_top_level_domain(request.url)
            if not SiteCatalog.is_site_enabled(domain=domain):
                message = f"Site is disabled, skip subscription update: {domain}"
                logger.info(message)
                if request.sync_state_id:
                    subscription_sync_state_service.mark_sync_skipped(
                        request.sync_state_id,
                        run_id=request.run_id,
                        request_id=request.request_id,
                        trace_id=request.trace_id,
                        trigger=request.trigger.value,
                        reason="site_disabled",
                    )
                # 记录跳过指标
                metrics.counter("subscription.update.total", tags={"site": domain, "status": "skipped", "reason": "site_disabled"})
                return SubscriptionUpdateResult(
                    subscription_id=request.subscription_id,
                    success=True,
                    videos_found=0,
                    videos_enqueued=0,
                    skipped_reason="site_disabled",
                )

            if not self._has_active_subscribers(request.subscription_id):
                message = f"No active subscribers, skip subscription update: subscription_id={request.subscription_id}"
                logger.info(message)
                if request.sync_state_id:
                    subscription_sync_state_service.mark_sync_skipped(
                        request.sync_state_id,
                        run_id=request.run_id,
                        request_id=request.request_id,
                        trace_id=request.trace_id,
                        trigger=request.trigger.value,
                        reason="no_subscribers",
                    )
                metrics.counter("subscription.update.total", tags={"site": domain, "status": "skipped", "reason": "no_subscribers"})
                return SubscriptionUpdateResult(
                    subscription_id=request.subscription_id,
                    success=True,
                    videos_found=0,
                    videos_enqueued=0,
                    skipped_reason="no_subscribers",
                )

            site_name = self._resolve_site(request.url)
            strategy = self._select_strategy(site_name)

            logger.debug(
                "Updating subscription %s using %s strategy (trigger=%s, mode=%s)",
                request.subscription_id,
                strategy.site_name,
                request.trigger.value,
                request.mode.value,
            )

            result = strategy.execute(request)

            return result

        except Exception as e:  # orchestrator boundary — always return SubscriptionUpdateResult
            logger.error("Orchestrator error for subscription %s: %s", request.subscription_id, e, exc_info=True)
            if request.sync_state_id:
                subscription_sync_state_service.mark_sync_failed(
                    request.sync_state_id,
                    str(e),
                    run_id=request.run_id,
                    request_id=request.request_id,
                    trace_id=request.trace_id,
                    error_type=type(e).__name__,
                    trigger=request.trigger.value,
                )

            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                    error_message=str(e),
            )

    @staticmethod
    def _has_active_subscribers(subscription_id: int) -> bool:
        with get_session() as session:
            row = session.execute(
                select(UserSubscription.id).where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                )
                .limit(1),
            ).first()
            return row is not None

    def _resolve_site(self, url: str) -> str:
        """解析站点名称"""
        domain = url_helper.extract_top_level_domain(url)

        site_key, _ = SiteCatalog.find_site_by_domain(domain)
        if site_key:
            return site_key

        return "default"

    def _select_strategy(self, site_name: str) -> UpdateStrategy:
        """选择更新策略"""
        strategy = StrategyRegistry.get_strategy(site_name)
        if strategy:
            logger.debug("Using %s strategy", site_name)
            return strategy

        logger.debug("No specific strategy for %s, using default", site_name)
        return self.default_strategy


orchestrator = SubscriptionOrchestrator()

