from typing import Dict
from starlette.responses import StreamingResponse

from proxy.video_proxy import VideoProxy
from proxy.config import get_domain_config


class YouTubeProxy(VideoProxy):
    def _extract_domain_from_request(self) -> str:
        """返回 YouTube 域名（用于选择域级配置）"""
        return "youtube.com"

    @property
    def headers(self) -> Dict[str, str]:
        # 优先使用配置中的自定义 headers
        domain_config = get_domain_config("youtube.com")
        if domain_config and domain_config.custom_headers:
            return domain_config.custom_headers.copy()

        # 默认 headers，模拟从 YouTube 来源播放 googlevideo 资源
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.youtube.com/",
            "Origin": "https://www.youtube.com",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "video",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
        }

    async def handle_stream(self, url: str) -> StreamingResponse:
        # 复用父类的增强流式传输逻辑
        return await super().handle_stream(url)

