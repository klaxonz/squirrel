"""ActorDTO - Actor/Creator data transfer object"""

from pydantic import BaseModel, Field, validator


class ActorDTO(BaseModel):
    """Actor/Creator data object

    Features:
    - Immutable (frozen=True)
    - Automatic validation
    - Serializable
    """

    url: str = Field(..., description='Actor homepage URL')
    name: str = Field(..., description='Actor name')
    avatar: str | None = Field(None, description='Avatar URL')

    class Config:
        frozen = True  # Immutable object

    @validator('url')
    def validate_url(cls, v):
        """Validate URL format"""
        if not v or not v.strip():
            raise ValueError('URL cannot be empty')

        v = v.strip()

        # Basic URL format validation
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')

        return v

    @validator('name')
    def validate_name(cls, v):
        """Validate name is not empty"""
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

    @validator('avatar')
    def validate_avatar(cls, v):
        """Validate avatar URL (optional)"""
        if v is None or v == '':
            return None

        v = v.strip()

        if not v.startswith(('http://', 'https://')):
            raise ValueError('Avatar URL must start with http:// or https://')

        return v

    def to_dict(self):
        """Convert to dictionary"""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)

    def __repr__(self):
        return f"ActorDTO(url='{self.url}', name='{self.name}')"
