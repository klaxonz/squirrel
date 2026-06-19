from fastapi import Query
from pydantic import BaseModel


class SubscribeRequest(BaseModel):
    url: str


class UnsubscribeRequest(BaseModel):
    subscription_id: int


class ImportSubscriptionsRequest(BaseModel):
    subscription_urls: list[str] | None = None


class SubscriptionImportPreviewQuery:
    def __init__(
        self,
        cursor: str | None = Query(None, description='Pagination cursor JSON'),
        limit: int = Query(50, ge=1, le=200, description='Preview page size'),
    ) -> None:
        self.cursor = cursor
        self.limit = limit


class ToggleStatusRequest(BaseModel):
    subscription_id: int
    is_enable: bool


class SubscriptionListQuery:
    def __init__(
        self,
        query: str = Query(None, description='Search keyword'),
        type: str = Query(None, description='Content type'),
        nsfw: str = Query('all', description='NSFW filter: all|yes|no', pattern=r'^(all|yes|no)$'),
        special: str = Query('all', description='Special follow filter: all|yes|no', pattern=r'^(all|yes|no)$'),
        site: str = Query(None, description='Site filter: e.g. youtube, bilibili (supports aliases)'),
        page: int = Query(1, ge=1, description='Page number'),
        page_size: int = Query(10, ge=1, le=100, alias='pageSize', description='Page size'),
    ) -> None:
        self.query = query
        self.type = type
        self.nsfw = nsfw
        self.special = special
        self.site = site
        self.page = page
        self.page_size = page_size
