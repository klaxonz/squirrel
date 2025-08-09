from __future__ import annotations

from enum import Enum

from common import constants


class ExtractQueueType(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    FOR_DOWNLOAD = "for_download"

def extract_stream_for_site(site: str, queue_type: ExtractQueueType) -> str:
    # constants.DOMAIN_QUEUE_MAPPING 的 key 是 domain，不是 site 名；
    # 这里按 site 名使用既有命名规范拼接。
    if queue_type == ExtractQueueType.MANUAL:
        return f"video_extract_{site}_queue"
    if queue_type == ExtractQueueType.SCHEDULED:
        return f"video_extract_{site}_scheduled_queue"
    return f"video_extract_for_download_{site}_queue"


