"""ActorDTO - 演员/UP主数据传输对象
"""

from pydantic import BaseModel, Field, validator


class ActorDTO(BaseModel):
    """演员/UP主数据对象

    特点：
    - 不可变对象（frozen=True）
    - 自动验证
    - 可序列化
    """

    url: str = Field(..., description="演员主页URL")
    name: str = Field(..., description="演员名称")
    avatar: str | None = Field(None, description="头像URL")

    class Config:
        frozen = True  # 不可变对象
        json_encoders = {
            # 如果需要自定义序列化
        }

    @validator("url")
    def validate_url(cls, v):
        """验证URL格式"""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")

        v = v.strip()

        # 基本URL格式验证
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

        return v

    @validator("name")
    def validate_name(cls, v):
        """验证名称非空"""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @validator("avatar")
    def validate_avatar(cls, v):
        """验证头像URL（可选）"""
        if v is None or v == "":
            return None

        v = v.strip()

        if not v.startswith(("http://", "https://")):
            raise ValueError("Avatar URL must start with http:// or https://")

        return v

    def to_dict(self):
        """转换为字典"""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建"""
        return cls(**data)

    def __repr__(self):
        return f"ActorDTO(url='{self.url}', name='{self.name}')"
