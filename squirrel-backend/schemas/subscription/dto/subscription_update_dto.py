from pydantic import BaseModel


class SubscriptionUpdateDto(BaseModel):
    subscription_id: int
    url: str
    total_videos: int
    total_extract: int
    is_nsfw: bool | None = None

