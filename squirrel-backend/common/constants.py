# Base queues
QUEUE_VIDEO_DOWNLOAD = 'video_download_queue'
QUEUE_VIDEO_DOWNLOAD_SCHEDULED = 'video_download_scheduled_queue'
QUEUE_VIDEO_EXTRACT = 'video_extract_queue'
QUEUE_VIDEO_EXTRACT_SCHEDULED = 'video_extract_scheduled_queue'
QUEUE_SUBSCRIBE = 'video_subscribe_queue'
QUEUE_VIDEO_PROGRESS = 'video_progress_queue'

# Redis keys
REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS = 'video:download:progress'
REDIS_KEY_VIDEO_DOWNLOAD_STATUS = 'video:download:status'
REDIS_KEY_VIDEO_DOWNLOAD_CACHE = 'video:download:cache'
REDIS_KEY_VIDEO_EXTRACT_CACHE = 'video:extract:cache'

VIDEO_EXTRACT_FIELD_NAME = 'is_extract'
VIDEO_DOWNLOAD_FIELD_NAME = 'is_download'

VIDEO_EXTRACT_EXPIRE = 10 * 60 * 1000

SUPPORTED_SITES = {
    'bilibili.com': 'bilibili',
    'youtube.com': 'youtube',
    'pornhub.com': 'pornhub',
    'javdb.com': 'javdb'
}


def get_all_queues():
    base_queues = [
        QUEUE_VIDEO_DOWNLOAD,
        QUEUE_VIDEO_DOWNLOAD_SCHEDULED,
        QUEUE_VIDEO_EXTRACT,
        QUEUE_VIDEO_EXTRACT_SCHEDULED,
        QUEUE_SUBSCRIBE,
        QUEUE_VIDEO_PROGRESS,
    ]

    site_queues = []
    for site_name in SUPPORTED_SITES.values():
        site_queues.extend([
            f'video_extract_{site_name}_queue',
            f'video_extract_{site_name}_scheduled_queue',
            f'video_extract_for_download_{site_name}_queue',
        ])

    return base_queues + site_queues


DOMAIN_QUEUE_MAPPING = {
    domain: {
        'manual': f'video_extract_{site_name}_queue',
        'scheduled': f'video_extract_{site_name}_scheduled_queue',
        'for_download': f'video_extract_for_download_{site_name}_queue'
    }
    for domain, site_name in SUPPORTED_SITES.items()
}
