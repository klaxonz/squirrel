"""Subscription update domain module

Unified management of all subscription update logic, providing a clean API interface
"""
from .models import UpdateMode, UpdateTrigger
from .scheduler import scheduler

__all__ = ["UpdateMode", "UpdateTrigger", "scheduler", "SubscriptionUpdateService"]


class SubscriptionUpdateService:
    def __init__(self, session_factory=None):
        from .orchestrator import SubscriptionOrchestrator
        from .scheduler import SubscriptionScheduler

        self.orchestrator = SubscriptionOrchestrator(session_factory=session_factory)
        self.scheduler = SubscriptionScheduler(session_factory=session_factory)

    def update(self, request):
        return self.orchestrator.update(request)

    def schedule_one(self, subscription_id, url, trigger=UpdateTrigger.MANUAL, mode=UpdateMode.INCREMENTAL, **kwargs):
        return self.scheduler.schedule_one(subscription_id, url, trigger=trigger, mode=mode, **kwargs)

    def run_one_inline(self, subscription_id, url, trigger=UpdateTrigger.MANUAL, mode=UpdateMode.INCREMENTAL, **kwargs):
        return self.scheduler.run_one_inline(subscription_id, url, trigger=trigger, mode=mode, **kwargs)

    def schedule_batch(self, subscription_ids, trigger=UpdateTrigger.SCHEDULED):
        return self.scheduler.schedule_batch(subscription_ids, trigger=trigger)

    def enqueue_all_active(self, trigger=UpdateTrigger.SCHEDULED, mode=UpdateMode.INCREMENTAL):
        return self.scheduler.enqueue_all_active(trigger=trigger, mode=mode)

    def enqueue_due_states(self, trigger=UpdateTrigger.SCHEDULED, mode=UpdateMode.INCREMENTAL, **kwargs):
        return self.scheduler.enqueue_due_states(trigger=trigger, mode=mode, **kwargs)
