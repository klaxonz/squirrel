# Base queues
QUEUE_VIDEO_DOWNLOAD = 'queue:video:download:manual'
QUEUE_VIDEO_DOWNLOAD_SCHEDULED = 'queue:video:download:scheduled'
QUEUE_SUBSCRIBE = 'queue:video:subscribe'

# Redis keys
REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS = 'video:download:progress'
REDIS_KEY_SUBSCRIPTION_MANUAL_PENDING_PREFIX = 'subscription:update:manual_pending:'


# System config keys
SYS_ENABLE_SCHEDULER = "enable_scheduler"
SYS_ENABLE_WORKER = "enable_worker"
SYS_BLUR_NSFW_THUMBNAILS = "blur_nsfw_thumbnails"
