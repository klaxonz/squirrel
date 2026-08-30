"""Subscription update orchestrator
Unified entry point responsible for coordinating the entire update flow
"""

from __future__ import annotations

import logging

from sqlalchemy import select

import infrastructure.site_catalog.url as url_helper
from domains.subscription.application.services.core.listing.service import SubscriptionListService
from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.user.application.services.config import UserConfigService
from infrastructure.database.session import get_session
from infrastructure.site_catalog.catalog import SiteCatalog
from shared_kernel.domain.exceptions import DomainError

from .models import SubscriptionUpdateRequest, SubscriptionUpdateResult
from .strategies.default_strategy import DefaultUpdateStrategy

logger = logging.getLogger(__name__)


class SubscriptionOrchestrator:
    """Subscription update orchestrator

    Responsibilities:
    1. Receive update requests
    2. Select appropriate update strategy
    3. Execute update flow
    4. Return update results
    """

    def __init__(
        self,
        session_factory=None,
        lifecycle: SubscriptionSyncLifecycle | None = None,
        strategy: DefaultUpdateStrategy | None = None,
    ):
        self.session_factory = session_factory or get_session
        if strategy is None:
            user_config = UserConfigService(session_factory=self.session_factory)
            listing_service = SubscriptionListService(
                session_factory=self.session_factory,
                get_user_config=user_config.get_config,
            )
            strategy = DefaultUpdateStrategy(listing_service=listing_service)
        self.default_strategy = strategy
        self.lifecycle = lifecycle or SubscriptionSyncLifecycle(session_factory=self.session_factory)
        self.lifecycle.bind_orchestrator(self)

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
                message = f'Site is disabled, skip subscription update: {domain}'
                logger.info(message)
                self.lifecycle.skip_sync(request, reason='site_disabled')
                return SubscriptionUpdateResult(
                    subscription_id=request.subscription_id,
                    success=True,
                    videos_found=0,
                    videos_enqueued=0,
                    skipped_reason='site_disabled',
                )

            if not self._has_active_subscribers(request.subscription_id):
                message = f'No active subscribers, skip subscription update: subscription_id={request.subscription_id}'
                logger.info(message)
                self.lifecycle.skip_sync(request, reason='no_subscribers')
                return SubscriptionUpdateResult(
                    subscription_id=request.subscription_id,
                    success=True,
                    videos_found=0,
                    videos_enqueued=0,
                    skipped_reason='no_subscribers',
                )

            logger.debug(
                'Updating subscription %s (trigger=%s, mode=%s)',
                request.subscription_id,
                request.trigger.value,
                request.mode.value,
            )

            result = self.default_strategy.execute(request)
            if result.skipped_reason:
                self.lifecycle.skip_sync(request, reason=result.skipped_reason)
            elif result.success:
                self.lifecycle.record_gap_observation(request, result)
                self.lifecycle.request_total_video_backfill_if_needed(request, result)
                self.lifecycle.complete_sync(request, result)

            return result

        except Exception as e:  # orchestrator boundary — always return SubscriptionUpdateResult
            logger.error('Orchestrator error for subscription %s: %s', request.subscription_id, e, exc_info=True)
            retryable = bool(
                getattr(
                    e,
                    'retryable',
                    not isinstance(e, (DomainError, ValueError, TypeError, AttributeError, KeyError)),
                ),
            )
            error_type = str(getattr(e, 'error_type', None) or type(e).__name__)
            if request.inline_video_extraction:
                self.lifecycle.fail_sync(request, e)

            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                error_message=str(e),
                error_type=error_type,
                retryable=retryable,
                retry_after_seconds=getattr(e, 'retry_after_seconds', None),
            )

    def _has_active_subscribers(self, subscription_id: int) -> bool:
        with self.session_factory() as session:
            row = session.execute(
                select(UserSubscription.id)
                .where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                )
                .limit(1),
            ).first()
            return row is not None
