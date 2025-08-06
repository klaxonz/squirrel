from typing import Dict
import httpx
from starlette.responses import StreamingResponse

from proxy.video_proxy import VideoProxy
from proxy.config import get_domain_config


class BilibiliProxy(VideoProxy):
    def __init__(self, request):
        super().__init__(request)

    def _extract_domain_from_request(self) -> str:
        """返回Bilibili域名"""
        return "bilibili.com"

    @property
    def headers(self) -> Dict[str, str]:
        # 使用配置中的自定义headers，如果有的话
        domain_config = get_domain_config("bilibili.com")
        if domain_config and domain_config.custom_headers:
            return domain_config.custom_headers.copy()

        # 默认headers
        return {
            "Referer": "https://www.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "video",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site"
        }

    async def handle_stream(self, url: str) -> StreamingResponse:
        # Enhanced timeout configuration for Bilibili
        timeout_config = httpx.Timeout(
            connect=30.0,
            read=120.0,
            write=30.0,
            pool=10.0
        )

        # Use parent class's enhanced streaming with Bilibili-specific config
        return await super().handle_stream(url)