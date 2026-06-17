from pydantic import BaseModel


class VideoExtractDto(BaseModel):
    url: str
    subscribed: bool
    only_extract: bool
    subscription_id: int
    sync_state_id: int | None = None
    run_id: str | None = None
    trigger: str | None = None
    is_manual: bool = False
    is_extract_all: bool = False
