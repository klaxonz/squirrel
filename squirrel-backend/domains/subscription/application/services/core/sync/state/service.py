from domains.subscription.application.services.core.sync.state import (
    _completion,
    _crud,
    _gap,
    _queue,
    _recovery,
    _utils,
)
from domains.subscription.application.services.core.sync.state._intervals import SYNC_BATCH_SIZE
from domains.subscription.application.services.core.sync.state.session import use_session_factory


class SubscriptionSyncStateService:
    """Application boundary for subscription synchronization state transitions."""

    SYNC_BATCH_SIZE = SYNC_BATCH_SIZE

    def __init__(self, session_factory=None):
        self.session_factory = session_factory

    def build_queue_token(self):
        return _utils.build_queue_token()

    def _call(self, name, *args, **kwargs):
        operation = self._operation(name)
        with use_session_factory(self.session_factory):
            return operation(*args, **kwargs)

    def _operation(self, name):
        modules = (_completion, _crud, _gap, _queue, _recovery, _utils)
        for module in modules:
            operation = getattr(module, name, None)
            if operation is not None:
                return operation
        raise AttributeError(name)

    def mark_sync_success(self, *args, **kwargs):
        return self._call('mark_sync_success', *args, **kwargs)

    def continue_full_sync_batch(self, *args, **kwargs):
        return self._call('continue_full_sync_batch', *args, **kwargs)

    def get_sync_state(self, *args, **kwargs):
        return self._call('get_sync_state', *args, **kwargs)

    def __getattr__(self, name):
        self._operation(name)
        return lambda *args, **kwargs: self._call(name, *args, **kwargs)




__all__ = ['SYNC_BATCH_SIZE', 'SubscriptionSyncStateService']
