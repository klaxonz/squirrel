import logging
from typing import Dict, Optional
from urllib.parse import urlparse
from sites.proxy_config import ProxyConfigManager

logger = logging.getLogger(__name__)


class ProxyManager:
    """负责按 URL/host 解析并提供上游 HTTP 客户端与请求头。

    - 持有 ProxyConfigManager 实例（用于 header 合并、域名解析）
    - 复用 ConnectionManager 的连接池
    """

    def __init__(self):
        self.config_manager = ProxyConfigManager()

    @staticmethod
    def _host_from_url(url: str) -> str:
        try:
            return urlparse(url).hostname or ''
        except Exception:
            return ''

    def get_headers_for_url(self, url: str, fallback: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        host = self._host_from_url(url)
        headers = self.config_manager.get_effective_headers_by_host(host)
        if headers:
            return headers
        return dict(fallback or {})

