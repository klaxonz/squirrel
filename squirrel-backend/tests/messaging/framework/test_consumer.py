import json
import sys
from pathlib import Path
from threading import Event

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from infrastructure.messaging.framework.consumer import ConsumerOptions, RedisStreamConsumer


class FakeRedis:
    def __init__(self, *, pending=None, new=None, deliveries=1):
        self.pending = pending or []
        self.new = new or []
        self.deliveries = deliveries
        self.created_groups = []
        self.acked = []
        self.deleted = []
        self.dlq = []
        self.reads = []

    def xgroup_create(self, *, name, groupname, id, mkstream):
        self.created_groups.append((name, groupname, id, mkstream))

    def xreadgroup(self, *, groupname, consumername, streams, count, block):
        self.reads.append((groupname, consumername, streams, count, block))
        stream, cursor = next(iter(streams.items()))
        if cursor == "0":
            return [(stream, self.pending)] if self.pending else []
        return [(stream, self.new)] if self.new else []

    def xpending_range(self, stream, group, min, max, count):
        return [{"times_delivered": self.deliveries}]

    def xadd(self, stream, fields):
        self.dlq.append((stream, fields))
        return "2-0"

    def xack(self, stream, group, message_id):
        self.acked.append((stream, group, message_id))
        return 1

    def xdel(self, stream, message_id):
        self.deleted.append((stream, message_id))
        return 1


def _fields(body):
    return {"body": json.dumps(body)}


def test_consumer_options_require_dlq_for_dlq_failure_action():
    with pytest.raises(ValueError, match="retry_dlq is required"):
        ConsumerOptions(group="group", consumer_name="consumer")


def test_failed_message_stays_pending_when_retry_is_explicit():
    redis = FakeRedis(new=[("1-0", _fields({"id": 1}))])
    options = ConsumerOptions(group="group", consumer_name="consumer", failure_action="retry")

    consumer = RedisStreamConsumer("stream", lambda _message: (_ for _ in ()).throw(ValueError("boom")), options, redis)

    assert consumer.poll_once() is True
    assert redis.acked == []
    assert redis.deleted == []
    assert redis.dlq == []


def test_failed_message_goes_to_dlq_after_max_delivery():
    redis = FakeRedis(new=[("1-0", _fields({"id": 1}))], deliveries=3)
    options = ConsumerOptions(
        group="group",
        consumer_name="consumer",
        retry_dlq="stream:dlq",
        max_delivery=3,
    )

    consumer = RedisStreamConsumer("stream", lambda _message: (_ for _ in ()).throw(ValueError("boom")), options, redis)

    assert consumer.poll_once() is True
    assert redis.acked == [("stream", "group", "1-0")]
    assert redis.deleted == [("stream", "1-0")]
    assert redis.dlq[0][0] == "stream:dlq"
    assert json.loads(redis.dlq[0][1]["body"]) == {"body": {"id": 1}, "message_id": "1-0"}


def test_failed_message_can_be_acknowledged_and_deleted():
    redis = FakeRedis(new=[("1-0", _fields({"id": 1}))])
    options = ConsumerOptions(group="group", consumer_name="consumer", failure_action="ack_delete")

    consumer = RedisStreamConsumer("stream", lambda _message: (_ for _ in ()).throw(ValueError("boom")), options, redis)

    assert consumer.poll_once() is True
    assert redis.acked == [("stream", "group", "1-0")]
    assert redis.deleted == [("stream", "1-0")]
    assert redis.dlq == []


def test_handler_receives_only_message_body():
    received = []
    redis = FakeRedis(new=[("1-0", _fields({"id": 1}))])
    options = ConsumerOptions(group="group", consumer_name="consumer", failure_action="retry")

    consumer = RedisStreamConsumer("stream", received.append, options, redis)

    assert consumer.poll_once() is True
    assert received == [{"id": 1}]
    assert redis.acked == [("stream", "group", "1-0")]


def test_start_loop_exits_when_stop_event_is_set():
    redis = FakeRedis()
    options = ConsumerOptions(group="group", consumer_name="consumer", failure_action="retry")
    stop_event = Event()
    consumer = RedisStreamConsumer("stream", lambda _message: None, options, redis)

    def stop_after_poll():
        stop_event.set()
        return False

    consumer.poll_once = stop_after_poll

    consumer.start_loop(stop_event)

    assert stop_event.is_set()
