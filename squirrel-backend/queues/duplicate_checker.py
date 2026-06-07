"""Message queue duplicate detection utility

Directly checks whether identical messages already exist in the Redis Stream queue.
Usage is determined by the caller.
"""
import json
import logging
from collections.abc import Callable
from typing import Any

from core.cache import redis_client

logger = logging.getLogger(__name__)


class MessageDuplicateChecker:
    """Message duplicate detection utility class

    Directly checks the queue for matching messages without requiring extra markers
    """

    def __init__(
        self,
        queue_name: str,
        match_fn: Callable[[dict, dict], bool],
        check_count: int | None = None,
    ):
        """Initialize the duplicate checker

        Args:
            queue_name: Queue name (Redis Stream key)
            match_fn: Message matching function, receives two message dicts and returns whether they match
            check_count: Number of recent messages to check in the queue, None means check all messages (default)

        """
        self.queue_name = queue_name
        self.match_fn = match_fn
        self.check_count = check_count

    def is_duplicate(self, message: dict) -> bool:
        """Check if a message already exists in the queue

        Args:
            message: Message content to check

        Returns:
            True if the message already exists in the queue, False otherwise

        """
        try:
            # Read messages from the queue (newest to oldest)
            # XREVRANGE key + - [COUNT count]
            if self.check_count is None:
                # Check all messages
                messages = redis_client.xrevrange(self.queue_name, "+", "-")
            else:
                # Check only the most recent N messages
                messages = redis_client.xrevrange(
                    self.queue_name,
                    "+",
                    "-",
                    count=self.check_count,
                )

            if not messages:
                return False

            # Check for matching messages
            for msg_id, fields in messages:
                try:
                    # Parse message content
                    # Redis keys may be bytes or string, handle both
                    body_str = fields.get(b"body") or fields.get("body")
                    if body_str is None:
                        continue

                    # Convert to string
                    if isinstance(body_str, bytes):
                        body_str = body_str.decode("utf-8")

                    existing_message = json.loads(body_str)

                    # Use custom matching function
                    if self.match_fn(message, existing_message):
                        logger.debug("Duplicate message found in %s: msg_id=%s", self.queue_name, msg_id.decode() if isinstance(msg_id, bytes) else msg_id)
                        return True

                except (ValueError, TypeError, KeyError) as e:
                    logger.warning("Failed to parse message in queue: %s", e)
                    continue

            return False

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error("Failed to check duplicate in %s: %s", self.queue_name, e)
            # Return False on check failure, do not block message sending
            return False


def create_checker(
    queue_name: str,
    match_fn: Callable[[dict, dict], bool],
    check_count: int | None = None,
) -> MessageDuplicateChecker:
    """Factory function to create a duplicate checker

    Args:
        queue_name: Queue name
        match_fn: Message matching function
        check_count: Number of recent messages to check, None means check all (default)

    Returns:
        MessageDuplicateChecker instance

    """
    return MessageDuplicateChecker(queue_name, match_fn, check_count)


def create_simple_checker(
    queue_name: str,
    key_fn: Callable[[dict], Any],
    check_count: int | None = None,
) -> MessageDuplicateChecker:
    """Create a simple duplicate checker (based on key equality)

    This is a convenience function for common scenarios: dedup based on a field or field combination.

    Args:
        queue_name: Queue name
        key_fn: Function that extracts a unique identifier from the message
        check_count: Number of recent messages to check, None means check all (default)

    Returns:
        MessageDuplicateChecker instance

    Example:
        # Dedup based on subscription_id (check all messages)
        checker = create_simple_checker(
            'subscription_update',
            key_fn=lambda msg: msg['body']['subscription_id']
        )

        # Check only the 100 most recent messages (for high-frequency queues)
        checker = create_simple_checker(
            'subscription_update',
            key_fn=lambda msg: msg['body']['subscription_id'],
            check_count=100
        )

    """
    def match_fn(msg1: dict, msg2: dict) -> bool:
        try:
            return key_fn(msg1) == key_fn(msg2)
        except (ValueError, TypeError, KeyError):
            return False

    return MessageDuplicateChecker(queue_name, match_fn, check_count)

