from enum import Enum


class ExtractQueueType(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    FOR_DOWNLOAD = "for_download"

