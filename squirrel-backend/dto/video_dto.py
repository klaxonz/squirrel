from pydantic import BaseModel


class VideoExtractDto(BaseModel):
    url: str
    subscribed: bool
    only_extract: bool
    subscription_id: int
