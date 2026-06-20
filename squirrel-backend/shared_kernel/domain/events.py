"""Lightweight in-process domain event dispatcher.

This lets a domain/persistence module announce "something happened" (e.g. a
video was saved) without taking a direct dependency on the module that reacts
to it (e.g. the Meilisearch indexer). That removes the function-body imports
that were used to dodge import cycles -- listeners register themselves at
bootstrap, and the publisher only knows the event name.

Scope: this is deliberately tiny and synchronous. It is NOT a message bus --
listeners run in the caller's thread, right after the event fires. Use it for
side effects that must happen close to the triggering write (index updates,
cache invalidation, lightweight notifications). For durable/async work use the
existing crawl/scheduler infrastructure.

Listeners that raise are logged and skipped; one bad listener must never break
the others or the publishing call site.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# A listener takes the event payload (an arbitrary dict) and returns nothing.
EventListener = Callable[[dict[str, Any]], None]


class DomainEventDispatcher:
    """Registry + fire for named in-process domain events."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[EventListener]] = defaultdict(list)

    def register(self, event: str, listener: EventListener) -> None:
        """Subscribe ``listener`` to ``event``.

        Events are identified by a stable string name (e.g.
        ``'video.saved'``). Registration is idempotent: the same listener is
        not added twice for the same event.
        """
        if listener not in self._listeners[event]:
            self._listeners[event].append(listener)

    def fire(self, event: str, payload: dict[str, Any] | None = None) -> None:
        """Synchronously invoke every listener subscribed to ``event``.

        Listener exceptions are caught and logged so a failing side effect
        cannot propagate back into the publishing write path.
        """
        payload = payload or {}
        for listener in self._listeners.get(event, []):
            try:
                listener(payload)
            except Exception:
                logger.exception('Domain event listener failed: event=%s', event)

    def listener_count(self, event: str) -> int:
        return len(self._listeners.get(event, []))

    def reset(self) -> None:
        """Clear all subscriptions (test helper)."""
        self._listeners.clear()


# Process-wide singleton. Listeners register at import/bootstrap time.
domain_events = DomainEventDispatcher()


# Canonical event names live here as constants so publishers and subscribers
# agree on spelling without importing each other.
class DomainEvents:
    VIDEO_SAVED = 'video.saved'
