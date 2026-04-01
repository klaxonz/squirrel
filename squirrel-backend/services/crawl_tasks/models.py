from enum import Enum


class CrawlTaskStatus(str, Enum):
    PENDING = 'pending'
    LEASED = 'leased'
    RUNNING = 'running'
    RETRY_WAIT = 'retry_wait'
    SUCCEEDED = 'succeeded'
    DEAD = 'dead'
    CANCELLED = 'cancelled'


class CrawlJobStatus(str, Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCEEDED = 'succeeded'
    PARTIAL_FAILED = 'partial_failed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
