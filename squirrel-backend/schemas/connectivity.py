"""
站点连通性测试相关的数据模型
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse


class ConnectivityTestRequest(BaseModel):
    """连通性测试请求模型"""
    url: str = Field(..., description="要测试的URL地址")
    timeout: Optional[int] = Field(10, description="超时时间（秒），默认10秒", ge=1, le=60)
    follow_redirects: Optional[bool] = Field(True, description="是否跟随重定向")
    
    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("URL不能为空")
        
        v_str = str(v).strip()
        
        # 如果没有协议，自动添加 http://
        if not v_str.startswith(("http://", "https://")):
            v_str = "https://" + v_str
        
        try:
            parsed = urlparse(v_str)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("无效的URL格式")
        except Exception:
            raise ValueError("无效的URL格式")
        
        return v_str


class ConnectivityTestResponse(BaseModel):
    """连通性测试响应模型"""
    url: str = Field(..., description="测试的URL")
    status: str = Field(..., description="测试状态：success, failed, timeout, error")
    accessible: bool = Field(..., description="是否可访问")
    status_code: Optional[int] = Field(None, description="HTTP状态码")
    response_time: Optional[float] = Field(None, description="响应时间（毫秒）")
    final_url: Optional[str] = Field(None, description="最终访问的URL（如果有重定向）")
    error_message: Optional[str] = Field(None, description="错误信息")
    dns_resolved: Optional[bool] = Field(None, description="DNS是否解析成功")
    ip_address: Optional[str] = Field(None, description="解析到的IP地址")
    headers: Optional[Dict[str, str]] = Field(None, description="响应头信息")
    
    
class BatchConnectivityTestRequest(BaseModel):
    """批量连通性测试请求模型"""
    urls: list[str] = Field(..., description="要测试的URL列表", min_length=1, max_length=20)
    timeout: Optional[int] = Field(10, description="超时时间（秒），默认10秒", ge=1, le=60)
    follow_redirects: Optional[bool] = Field(True, description="是否跟随重定向")


class BatchConnectivityTestResponse(BaseModel):
    """批量连通性测试响应模型"""
    results: list[ConnectivityTestResponse] = Field(..., description="测试结果列表")
    summary: Dict[str, Any] = Field(..., description="汇总信息")
