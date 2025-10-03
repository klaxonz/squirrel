# Base queues
QUEUE_VIDEO_DOWNLOAD = 'queue::video::download::manual'
QUEUE_VIDEO_DOWNLOAD_SCHEDULED = 'queue::video::download::scheduled'
QUEUE_VIDEO_EXTRACT = 'queue::video::extract::manual'
QUEUE_VIDEO_EXTRACT_SCHEDULED = 'queue::video::extract::scheduled'
QUEUE_SUBSCRIBE = 'queue::video::subscribe'
# Subscription update queues - incremental (5 min) and full (1 hour)
QUEUE_SUBSCRIPTION_UPDATE_INCREMENTAL = 'queue::subscription::update::incremental'
QUEUE_SUBSCRIPTION_UPDATE_FULL = 'queue::subscription::update::full'
QUEUE_SUBSCRIPTION_UPDATE_MANUAL = 'queue::subscription::update::manual'

# Redis keys
REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS = 'video:download:progress'
REDIS_KEY_SUBSCRIPTION_MANUAL_PENDING_PREFIX = 'subscription:update:manual_pending:'


# System config keys
SYS_ENABLE_SCHEDULER = "enable_scheduler"
SYS_ENABLE_WORKER = "enable_worker"
SYS_BLUR_NSFW_THUMBNAILS = "blur_nsfw_thumbnails"


def get_subscription_update_queue(domain: str, queue_type: str) -> str:
    """
    动态生成订阅更新队列名称
    
    Args:
        domain: 域名 (如 'bilibili.com')
        queue_type: 队列类型 ('manual', 'incremental', 'full')
    
    Returns:
        队列名称字符串
    """
    # 从域名提取站点名称 (如 'bilibili.com' -> 'bilibili')
    site_name = domain.split('.')[0] if '.' in domain else domain
    return f'queue::subscription::update::{site_name}::{queue_type}'
