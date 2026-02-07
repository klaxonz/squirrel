import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class KProxyProvider:
    def __init__(self, base_url: str = "http://127.0.0.1:8002", timeout: int = 5):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def get_proxy(self, domain: Optional[str] = None):
        if not domain:
            logger.warning("Domain not provided, cannot get proxy")
            return None

        try:
            url = f"{self.base_url}/api/proxy/random"
            response = requests.get(url, params={"domain": domain}, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            if data.get("status") == "0" and data.get("data"):
                proxy_data = data["data"]
                from squirrel_sdk.crawl.proxy_provider import ProxyInfo
                return ProxyInfo(
                    host=proxy_data["host"],
                    port=proxy_data["port"],
                    username=proxy_data.get("username"),
                    password=proxy_data.get("password"),
                )
            else:
                logger.warning(f"No proxy available for domain {domain}: {data.get('message')}")
                return None

        except Exception as e:
            logger.error(f"Failed to get proxy for domain {domain}: {e}")
            return None

    def report_result(self, proxy, domain: str, success: bool) -> None:
        try:
            url = f"{self.base_url}/api/proxy/report"
            payload = {
                "ip": proxy.host,
                "port": proxy.port,
                "domain": domain,
                "success": 1 if success else 0,
            }
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

        except Exception as e:
            logger.error(f"Failed to report proxy result: {e}")
