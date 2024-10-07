from pydantic import BaseModel


class SubscribeChannelRequest(BaseModel):
    url: str


class ChannelUpdateRequest(BaseModel):
    id: int
    if_enable: bool = None
    if_auto_download: bool = None
    if_download_all: bool = None
    if_extract_all: bool = None


class ChannelDeleteRequest(BaseModel):
    id: int


class ToggleStatusRequest(BaseModel):
    channel_id: int
    if_enable: bool
