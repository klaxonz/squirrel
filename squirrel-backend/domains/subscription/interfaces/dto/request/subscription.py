
from pydantic import BaseModel


class SubscribeRequest(BaseModel):
    url: str


class UnsubscribeRequest(BaseModel):
    subscription_id: int


class ImportSubscriptionsRequest(BaseModel):
    subscription_urls: list[str] | None = None


class UpdateSubscriptionRequest(BaseModel):
    subscription_id: int
    name: str | None = None
    description: str | None = None
    avatar: str | None = None
    status: str | None = None


class ToggleStatusRequest(BaseModel):
    subscription_id: int
    is_enable: bool
