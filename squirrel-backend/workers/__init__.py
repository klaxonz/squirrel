"""Worker handlers for Redis Streams consumers.

模块导入副作用：在 import workers.* 时自动向 ConsumerRegistry 注册。
"""

from mq import ConsumerRegistry
from common.constants import get_all_queues

# 延迟导入实际处理器，避免循环引用
from .extract_worker import handle_extract_entry, handle_extract_site
from .download_worker import handle_download
from .subscription_worker import handle_subscribe
from .subscription_update_worker import (
    handle_subscription_update,
    handle_subscription_update_manual,
)

# 注册入口解析队列
ConsumerRegistry.register("video_extract_queue", "extract", "extract-entry", handle_extract_entry)
ConsumerRegistry.register("video_extract_scheduled_queue", "extract", "extract-entry-scheduled", handle_extract_entry)

# 注册站点解析队列（基于常量自动扩展）
for q in get_all_queues():
    if q.startswith("video_extract_") and (q.endswith("_queue") or q.endswith("_scheduled_queue") or q.startswith("video_extract_for_download_")):
        ConsumerRegistry.register(q, "extract-site", f"extract-{q}", handle_extract_site)

# 下载
ConsumerRegistry.register("video_download_queue", "download", "download", handle_download)
ConsumerRegistry.register("video_download_scheduled_queue", "download", "download-scheduled", handle_download)

# 订阅
ConsumerRegistry.register("video_subscribe_queue", "subscription", "subscribe", handle_subscribe)
ConsumerRegistry.register("subscription_update_queue", "subscription", "sub-update", handle_subscription_update)
ConsumerRegistry.register("subscription_update_manual_queue", "subscription", "sub-update-manual", handle_subscription_update_manual)



