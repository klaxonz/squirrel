"""Subscription update orchestrator
Unified entry point responsible for coordinating the entire update flow
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
    """Subscription update orchestrator

    Responsibilities:
    1. Receive update requests
    2. Select appropriate update strategy
    3. Execute update flow
    4. Return update results
    """

    def __init__(self, session_factory=None):
        self.default_strategy = DefaultUpdateStrategy()
        self.session_factory = session_factory or get_session

    def update(self, request: SubscriptionUpdateRequest) -> SubscriptionUpdateResult:
        """Execute subscription update

        Args:
            request: Update request

        Returns:
            Update result

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

    def _has_active_subscribers(self, subscription_id: int) -> bool:
        with self.session_factory() as session:
            row = session.execute(
                select(UserSubscription.id).where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                )
                .limit(1),
            ).first()
            return row is not None

    def _resolve_site(self, url: str) -> str:
        """Resolve site name"""
        domain = url_helper.extract_top_level_domain(url)

        site_key, _ = SiteCatalog.find_site_by_domain(domain)
        if site_key:
            return site_key

        return "default"

    def _select_strategy(self, site_name: str) -> UpdateStrategy:
        """Select update strategy"""
        strategy = StrategyRegistry.get_strategy(site_name)
        if strategy:
            logger.debug("Using %s strategy", site_name)
            return strategy

        logger.debug("No specific strategy for %s, using default", site_name)
        return self.default_strategy


orchestrator = SubscriptionOrchestrator()

