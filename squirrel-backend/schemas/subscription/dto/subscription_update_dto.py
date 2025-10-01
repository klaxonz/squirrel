from pydantic import BaseModel


class SubscriptionUpdateDto(BaseModel):
    """订阅更新消息 DTO"""
    subscription_id: int
    url: str

