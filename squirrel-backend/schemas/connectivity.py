"""Data models for site connectivity testing
"""
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class ConnectivityTestRequest(BaseModel):
    """Connectivity test request model"""

    url: str = Field(..., description="URL to test")
    timeout: int | None = Field(10, description="Timeout (seconds), default 10s", ge=1, le=60)
    follow_redirects: bool | None = Field(True, description="Whether to follow redirects")

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("URL must not be empty")

        v_str = str(v).strip()

        # Auto-add https:// if no protocol specified
        if not v_str.startswith(("http://", "https://")):
            v_str = "https://" + v_str

        try:
            parsed = urlparse(v_str)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception:
            raise ValueError("Invalid URL format")

        return v_str


class ConnectivityTestResponse(BaseModel):
    """Connectivity test response model"""

    url: str = Field(..., description="Tested URL")
    status: str = Field(..., description="Test status: success, failed, timeout, error")
    accessible: bool = Field(..., description="Whether accessible")
    status_code: int | None = Field(None, description="HTTP status code")
    response_time: float | None = Field(None, description="Response time (ms)")
    final_url: str | None = Field(None, description="Final URL (if redirected)")
    error_message: str | None = Field(None, description="Error message")
    dns_resolved: bool | None = Field(None, description="Whether DNS resolved successfully")
    ip_address: str | None = Field(None, description="Resolved IP address")
    headers: dict[str, str] | None = Field(None, description="Response headers")


class BatchConnectivityTestRequest(BaseModel):
    """Batch connectivity test request model"""

    urls: list[str] = Field(..., description="URLs to test", min_length=1, max_length=20)
    timeout: int | None = Field(10, description="Timeout (seconds), default 10s", ge=1, le=60)
    follow_redirects: bool | None = Field(True, description="Whether to follow redirects")


class BatchConnectivityTestResponse(BaseModel):
    """Batch connectivity test response model"""

    results: list[ConnectivityTestResponse] = Field(..., description="Test result list")
    summary: dict[str, Any] = Field(..., description="Summary information")
