# Base queues
QUEUE_VIDEO_DOWNLOAD = 'queue::video::download::manual'
QUEUE_VIDEO_DOWNLOAD_SCHEDULED = 'queue::video::download::scheduled'
QUEUE_VIDEO_EXTRACT = 'queue::video::extract::manual'
QUEUE_VIDEO_EXTRACT_SCHEDULED = 'queue::video::extract::scheduled'
QUEUE_SUBSCRIBE = 'queue::video::subscribe'
QUEUE_VIDEO_PROGRESS = 'queue::video::progress'
QUEUE_SUBSCRIPTION_UPDATE = 'queue::subscription::update::scheduled'
QUEUE_SUBSCRIPTION_UPDATE_MANUAL = 'queue::subscription::update::manual'

# Redis keys
REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS = 'video:download:progress'
REDIS_KEY_VIDEO_DOWNLOAD_STATUS = 'video:download:status'
REDIS_KEY_VIDEO_DOWNLOAD_CACHE = 'video:download:cache'
REDIS_KEY_VIDEO_EXTRACT_CACHE = 'video:extract:cache'
# Subscription update progress and flags
REDIS_KEY_SUBSCRIPTION_UPDATE_PROGRESS_PREFIX = 'subscription:update:progress:'
REDIS_KEY_SUBSCRIPTION_MANUAL_PENDING_PREFIX = 'subscription:update:manual_pending:'
# New: subscription enqueued flags (separate for scheduled/manual)
REDIS_KEY_SUBSCRIPTION_ENQUEUED_SCHEDULED_PREFIX = 'subscription:update:enqueued:scheduled:'
REDIS_KEY_SUBSCRIPTION_ENQUEUED_MANUAL_PREFIX = 'subscription:update:enqueued:manual:'
# New: per-video enqueued flag prefix
REDIS_KEY_VIDEO_EXTRACT_ENQUEUED_PREFIX = 'video:extract:enqueued:'

VIDEO_EXTRACT_FIELD_NAME = 'is_extract'
VIDEO_DOWNLOAD_FIELD_NAME = 'is_download'

VIDEO_EXTRACT_EXPIRE = 10 * 60

SUPPORTED_SITES = {
    'bilibili.com': 'bilibili',
    'youtube.com': 'youtube',
    'pornhub.com': 'pornhub',
    'javdb.com': 'javdb'
}

# System config keys
SYS_ENABLE_SCHEDULER = "enable_scheduler"
SYS_ENABLE_WORKER = "enable_worker"


def get_all_queues():
    base_queues = [
        QUEUE_VIDEO_DOWNLOAD,
        QUEUE_VIDEO_DOWNLOAD_SCHEDULED,
        QUEUE_VIDEO_EXTRACT,
        QUEUE_VIDEO_EXTRACT_SCHEDULED,
        QUEUE_SUBSCRIBE,
        QUEUE_VIDEO_PROGRESS,
        QUEUE_SUBSCRIPTION_UPDATE,
        QUEUE_SUBSCRIPTION_UPDATE_MANUAL,
    ]

    site_queues = []
    for site_name in SUPPORTED_SITES.values():
        site_queues.extend([
            f'queue::video::extract::{site_name}::manual',
            f'queue::video::extract::{site_name}::scheduled',
            f'queue::subscription::update::{site_name}::manual',
            f'queue::subscription::update::{site_name}::scheduled',
        ])

    return base_queues + site_queues


DOMAIN_QUEUE_MAPPING = {
    domain: {
        'manual': f'queue::video::extract::{site_name}::manual',
        'scheduled': f'queue::video::extract::{site_name}::scheduled'
    }
    for domain, site_name in SUPPORTED_SITES.items()
}

# New: subscription update domain queues mapping
SUBSCRIPTION_UPDATE_DOMAIN_QUEUE_MAPPING = {
    domain: {
        'manual': f'queue::subscription::update::{site_name}::manual',
        'scheduled': f'queue::subscription::update::{site_name}::scheduled',
    }
    for domain, site_name in SUPPORTED_SITES.items()
}
