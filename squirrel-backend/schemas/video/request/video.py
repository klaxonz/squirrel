from enum import Enum


class SortBy(str, Enum):
    UPLOADED_AT = "publish_date"
    CREATED_AT = "created_at"
