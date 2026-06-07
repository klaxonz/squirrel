from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class VideoProxyRequest(BaseModel):
    """视频代理请求模型"""

    domain: str = Field(..., description="目标域名")
    url: str = Field(..., description="目标URL")

    @field_validator("domain", mode="before")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("域名不能为空")
        # 确保为字符串再处理
        v_str = str(v)
        return v_str.strip().lower()

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("URL不能为空")

        v_str = str(v).strip()
        try:
            parsed = urlparse(v_str)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("无效的URL格式")
        except Exception:
            raise ValueError("无效的URL格式")

        return v_str


class ProxyErrorResponse(BaseModel):
    """代理错误响应模型"""

    error: str = Field(..., description="错误信息")
    domain: str | None = Field(None, description="相关域名")
    status_code: int = Field(..., description="HTTP状态码")
