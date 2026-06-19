from pydantic import BaseModel, Field


class HistoryBase(BaseModel):
    video_id: int = Field(..., description='视频ID')
    last_position: float = Field(0.0, description='最后观看位置(秒)')
    timestamp: int | None = Field(None, description='Client report timestamp in milliseconds')


class HistoryCreate(HistoryBase):
    pass


class HistoryBatchUpdate(BaseModel):
    reports: list[HistoryCreate] = Field(default_factory=list, description='批量上报的播放历史')
