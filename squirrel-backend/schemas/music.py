from pydantic import BaseModel, Field, field_validator


class MusicTrackPayload(BaseModel):
    title: str = Field("", max_length=255)
    hash: str = Field(..., min_length=1, max_length=128)
    album_id: str = Field("", max_length=128)
    album_audio_id: str = Field("", max_length=128)

    @field_validator("hash")
    @classmethod
    def normalize_hash(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("hash cannot be empty")
        return normalized


class MusicPlaylistTrackAdd(BaseModel):
    list_id: str = Field(..., min_length=1, max_length=128)
    track: MusicTrackPayload


class MusicPlaylistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    is_private: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name cannot be empty")
        return normalized


class MusicPlaylistCollect(BaseModel):
    playlist_id: str = Field(..., min_length=1, max_length=128)


class MusicPlayHistoryReport(BaseModel):
    album_audio_id: str = Field(..., min_length=1, max_length=128)
    played_at: int | None = Field(None, ge=0)
    play_count: int = Field(1, ge=1)
