"""VideoDTO - 视频数据传输对象
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator

from .actor_dto import ActorDTO
from .validators import (
    parse_publish_date,
    validate_duration,
    validate_not_empty,
    validate_url,
)


class VideoDTO(BaseModel):
    """视频数据传输对象

    特点：
    - 纯数据对象，无行为
    - 不可变（frozen=True）
    - 自动验证所有字段
    - 可序列化、可缓存
    - 统一数据格式

    与插件Video对象的区别：
    - Video对象：带懒加载属性、可能触发HTTP请求
    - VideoDTO：纯数据、所有字段立即可用、无副作用
    """

    # ========== 必填字段 ==========
    url: str = Field(..., description="视频URL")
    title: str = Field(..., description="视频标题")
    site_name: str = Field(..., description="站点名称，如bilibili, youtube")

    # ========== 可选基础字段 ==========
    thumbnail: str | None = Field(None, description="缩略图URL")
    duration: int | None = Field(None, ge=0, description="视频时长（秒）")
    publish_date: datetime | None = Field(None, description="发布时间")
    description: str | None = Field(None, description="视频描述")
    tags: list[str] | None = Field(None, description="标签列表")

    # ========== 关联数据 ==========
    actors: list[ActorDTO] = Field(default_factory=list, description="演员/UP主列表")

    # ========== 元数据 ==========
    raw_data: dict[str, Any] | None = Field(
        None,
        description="原始数据（用于调试和审计）",
    )

    class Config:
        frozen = True  # 不可变对象
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }

    # ========== 验证器 ==========

    @validator("url")
    def validate_url_field(cls, v):
        """验证URL格式"""
        return validate_url(v)

    @validator("title")
    def validate_title(cls, v):
        """验证标题非空"""
        return validate_not_empty(v, "Title")

    @validator("site_name")
    def validate_site_name(cls, v):
        """验证站点名称"""
        return validate_not_empty(v, "Site name")

    @validator("thumbnail")
    def validate_thumbnail_url(cls, v):
        """验证缩略图URL（可选）"""
        if v is None or v == "":
            return None

        v = v.strip()

        if not v:
            return None

        # 缩略图URL可以是相对路径或完整URL
        if v.startswith(("http://", "https://", "/")):
            return v

        raise ValueError("Thumbnail URL must be absolute or relative path")

    @validator("duration")
    def validate_duration_field(cls, v):
        """验证时长"""
        return validate_duration(v)

    @validator("publish_date", pre=True)
    def parse_and_validate_publish_date(cls, v):
        """解析并验证发布时间"""
        return parse_publish_date(v)

    @validator("description")
    def clean_description(cls, v):
        """清理描述文本"""
        if v is None or v == "":
            return None

        # 去除首尾空白
        v = v.strip()

        if not v:
            return None

        # 限制长度（避免过长的描述）
        max_length = 10000
        if len(v) > max_length:
            v = v[:max_length] + "..."

        return v

    @validator("tags")
    def validate_tags(cls, v):
        """验证标签列表"""
        if v is None or v == []:
            return None

        if not isinstance(v, list):
            raise ValueError("Tags must be a list")

        # 清理标签
        cleaned_tags = []
        for tag in v:
            if isinstance(tag, str):
                tag = tag.strip()
                if tag:
                    cleaned_tags.append(tag)

        return cleaned_tags or None

    @validator("actors")
    def validate_actors_list(cls, v):
        """验证演员列表"""
        if v is None:
            return []

        if not isinstance(v, list):
            raise ValueError("Actors must be a list")

        # 确保所有元素都是ActorDTO
        for actor in v:
            if not isinstance(actor, ActorDTO):
                raise ValueError(f"Actor must be ActorDTO instance, got {type(actor)}")

        return v

    # ========== 工具方法 ==========

    def to_dict(self, exclude_none: bool = True) -> dict[str, Any]:
        """转换为字典

        Args:
            exclude_none: 是否排除None值

        Returns:
            字典表示

        """
        data = self.dict(exclude_none=exclude_none)

        # 转换actors为字典列表
        if data.get("actors"):
            data["actors"] = [actor.to_dict() for actor in self.actors]

        # 转换datetime为ISO格式字符串
        if data.get("publish_date"):
            data["publish_date"] = self.publish_date.isoformat()

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VideoDTO":
        """从字典创建

        Args:
            data: 字典数据

        Returns:
            VideoDTO实例

        """
        # 转换actors
        if data.get("actors"):
            if isinstance(data["actors"], list):
                data["actors"] = [
                    ActorDTO(**actor) if isinstance(actor, dict) else actor
                    for actor in data["actors"]
                ]

        return cls(**data)

    def has_actors(self) -> bool:
        """是否有演员信息"""
        return bool(self.actors)

    def has_thumbnail(self) -> bool:
        """是否有缩略图"""
        return bool(self.thumbnail)

    def has_publish_date(self) -> bool:
        """是否有发布时间"""
        return self.publish_date is not None

    def get_summary(self) -> str:
        """获取摘要信息（用于日志）"""
        return (
            f"VideoDTO(url='{self.url}', title='{self.title[:50]}...', "
            f"site='{self.site_name}', actors={len(self.actors)})"
        )

    def __repr__(self):
        return self.get_summary()
