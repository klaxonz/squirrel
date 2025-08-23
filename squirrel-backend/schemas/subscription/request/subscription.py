from typing import Optional

from pydantic import BaseModel


class SubscribeRequest(BaseModel):
    url: str


class UnsubscribeRequest(BaseModel):
    subscription_id: Optional[int] = None
    url: Optional[str] = None


class UpdateSubscriptionRequest(BaseModel):
    subscription_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    avatar: Optional[str] = None
    status: Optional[str] = None


class ToggleStatusRequest(BaseModel):
    subscription_id: int
    is_enable: bool
