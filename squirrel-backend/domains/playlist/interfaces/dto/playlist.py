from pydantic import BaseModel, Field, field_validator


class PlaylistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description='播放列表名称')
    description: str | None = Field(None, max_length=512, description='播放列表描述')

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError('name cannot be empty')
        return normalized


class PlaylistUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255, description='播放列表名称')
    description: str | None = Field(None, max_length=512, description='播放列表描述')

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            raise ValueError('name cannot be empty')
        return normalized


class PlaylistItemAdd(BaseModel):
    video_id: int = Field(..., description='视频ID')
    playlist_id: int | None = Field(None, description='播放列表ID,留空则添加到默认列表')


class PlaylistItemReorder(BaseModel):
    playlist_id: int = Field(..., description='播放列表ID')
    video_id: int = Field(..., description='视频ID')
    new_position: int = Field(..., ge=1, description='新的位置(从 1 开始)')


class PlaylistDto(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    is_default: bool
    video_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
