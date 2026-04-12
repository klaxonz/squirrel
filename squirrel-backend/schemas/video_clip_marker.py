from pydantic import BaseModel, Field, field_validator, model_validator


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()
    return normalized or None


class ClipMarkerCreate(BaseModel):
    video_id: int = Field(..., description='视频ID')
    title: str | None = Field(None, max_length=255, description='片段标题')
    note: str | None = Field(None, description='片段备注')
    start_time: float = Field(..., ge=0, description='开始时间(秒)')
    end_time: float | None = Field(None, ge=0, description='结束时间(秒)')

    @field_validator('title', 'note')
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @model_validator(mode='after')
    def validate_bounds(self):
        if self.end_time is not None and self.end_time < self.start_time:
            raise ValueError('end_time must be greater than or equal to start_time')
        return self


class ClipMarkerUpdate(BaseModel):
    title: str | None = Field(None, max_length=255, description='片段标题')
    note: str | None = Field(None, description='片段备注')
    start_time: float | None = Field(None, ge=0, description='开始时间(秒)')
    end_time: float | None = Field(None, ge=0, description='结束时间(秒)')

    @field_validator('title', 'note')
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @model_validator(mode='after')
    def validate_bounds(self):
        if self.start_time is not None and self.end_time is not None and self.end_time < self.start_time:
            raise ValueError('end_time must be greater than or equal to start_time')
        return self
