QUEUE_VIDEO_DOWNLOAD_TASK = 'video_download_queue'
QUEUE_VIDEO_DOWNLOAD_SCHEDULED_TASK = 'video_download_scheduled_queue'
QUEUE_VIDEO_EXTRACT_TASK = 'video_extract_queue'
QUEUE_VIDEO_EXTRACT_SCHEDULED_TASK = 'video_extract_scheduled_queue'

# site extract queue
QUEUE_VIDEO_EXTRACT_YOUTUBE_TASK = 'video_extract_youtube_queue'
QUEUE_VIDEO_EXTRACT_YOUTUBE_SCHEDULED_TASK = 'video_extract_youtube_scheduled_queue'
QUEUE_VIDEO_EXTRACT_BILIBILI_TASK = 'video_extract_bilibili_queue'
QUEUE_VIDEO_EXTRACT_BILIBILI_SCHEDULED_TASK = 'video_extract_bilibili_scheduled_queue'
QUEUE_VIDEO_EXTRACT_PORNHUB_TASK = 'video_extract_pornhub_queue'
QUEUE_VIDEO_EXTRACT_PORNHUB_SCHEDULED_TASK = 'video_extract_pornhub_scheduled_queue'
QUEUE_VIDEO_EXTRACT_JAVDB_TASK = 'video_extract_javdb_queue'
QUEUE_VIDEO_EXTRACT_JAVDB_SCHEDULED_TASK = 'video_extract_javdb_scheduled_queue'

QUEUE_SUBSCRIBE_TASK = 'video_subscribe_queue'
QUEUE_VIDEO_PROGRESS_TASK = 'video_progress_queue'

MESSAGE_TYPE_DOWNLOAD = 'download'
MESSAGE_TYPE_SUBSCRIBE = 'subscribe'

REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS = 'video:download:progress'
REDIS_KEY_VIDEO_DOWNLOAD_STATUS = 'video:download:status'
REDIS_KEY_VIDEO_DOWNLOAD_CACHE = 'video:download:cache'

REDIS_KEY_TASK_STATUS = 'video:task:status'

UNSUBSCRIBED_CHANNELS_SET = "unsubscribed_channels"
UNSUBSCRIBE_EXPIRATION = 60 * 60 * 24  # 24 hours in seconds
