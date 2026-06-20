"""Tests for the in-process domain event dispatcher."""

from shared_kernel.domain.events import DomainEventDispatcher, DomainEvents, domain_events


def test_registered_listener_is_invoked_on_fire():
    dispatcher = DomainEventDispatcher()
    received = []
    dispatcher.register(DomainEvents.VIDEO_SAVED, lambda payload: received.append(payload['video_id']))

    dispatcher.fire(DomainEvents.VIDEO_SAVED, {'video_id': 42})

    assert received == [42]


def test_multiple_listeners_all_run():
    dispatcher = DomainEventDispatcher()
    calls = []
    dispatcher.register(DomainEvents.VIDEO_SAVED, lambda p: calls.append(('a', p.get('video_id'))))
    dispatcher.register(DomainEvents.VIDEO_SAVED, lambda p: calls.append(('b', p.get('video_id'))))

    dispatcher.fire(DomainEvents.VIDEO_SAVED, {'video_id': 7})

    assert calls == [('a', 7), ('b', 7)]


def test_failing_listener_does_not_block_others_and_is_swallowed():
    dispatcher = DomainEventDispatcher()
    survivors = []

    def boom(_payload):
        raise RuntimeError('listener exploded')

    dispatcher.register(DomainEvents.VIDEO_SAVED, boom)
    dispatcher.register(DomainEvents.VIDEO_SAVED, lambda p: survivors.append(p['video_id']))

    # Must not raise even though one listener throws.
    dispatcher.fire(DomainEvents.VIDEO_SAVED, {'video_id': 99})

    assert survivors == [99]


def test_register_is_idempotent():
    dispatcher = DomainEventDispatcher()
    listener = lambda p: None  # noqa: E731
    dispatcher.register(DomainEvents.VIDEO_SAVED, listener)
    dispatcher.register(DomainEvents.VIDEO_SAVED, listener)
    assert dispatcher.listener_count(DomainEvents.VIDEO_SAVED) == 1


def test_fire_with_no_listeners_is_a_noop():
    dispatcher = DomainEventDispatcher()
    dispatcher.fire(DomainEvents.VIDEO_SAVED, {'video_id': 1})  # no error
    dispatcher.fire(DomainEvents.VIDEO_SAVED)  # missing payload defaults to {}


def test_event_name_constant_is_stable():
    assert DomainEvents.VIDEO_SAVED == 'video.saved'


def test_singleton_is_usable():
    # The process-wide singleton must be importable and functional.
    seen = []
    domain_events.register(DomainEvents.VIDEO_SAVED, lambda p: seen.append(p.get('video_id')))
    try:
        domain_events.fire(DomainEvents.VIDEO_SAVED, {'video_id': 5})
        assert 5 in seen
    finally:
        domain_events.reset()
