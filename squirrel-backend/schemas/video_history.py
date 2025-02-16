from pydantic import BaseModel, Field


class HistoryBase(BaseModel):
    video_id: int = Field(..., description="视频ID")
    last_position: float = Field(0.0, description="最后观看位置(秒)")


class HistoryCreate(HistoryBase):
    pass
