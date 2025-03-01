from pydantic import Field, BaseModel


class VideoInteractionUpdate(BaseModel):
    video_id: int = Field(..., description="视频ID")
    interaction_type: int = Field(..., description="1: like, 2: dislike")


class VideoInteractionDelete(BaseModel):
    video_id: int = Field(..., description="视频ID")
