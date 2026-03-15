import logging
from dataclasses import dataclass
from typing import Optional

import requests

from core.config import settings

logger = logging.getLogger(__name__)


def _normalize_proxy_scheme(scheme: Optional[str]) -> str:
    scheme_name = (scheme or "http").strip().lower() or "http"
    if scheme_name in {"socks", "socks5"}:
        return "socks5h"
    return scheme_name


@dataclass
class KProxyInfo:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"

    def to_url(self, scheme: Optional[str] = None) -> str:
        scheme_name = _normalize_proxy_scheme(scheme or self.protocol)
        if self.username and self.password:
            return f"{scheme_name}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{scheme_name}://{self.host}:{self.port}"

    def to_dict(self) -> dict:
        proxy_url = self.to_url()
        return {
            "http": proxy_url,
            "https": proxy_url,
        }


class KProxyProvider:
    def __init__(self, base_url: str, timeout: int = 5):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def get_proxy(self, domain: Optional[str] = None):
        if not domain:
            logger.warning("Domain not provided, cannot get proxy")
            return None

        try:
            url = f"{self.base_url}/api/proxy/random"
            logger.info(f"Requesting proxy for domain={domain}, endpoint={url}")
            response = requests.get(url, params={"domain": domain}, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            if data.get("status") == "0" and data.get("data"):
                proxy_data = data["data"]
                proxy_host = str(proxy_data["ip"]).strip()
                proxy_port = int(proxy_data["port"])
                proxy_protocol = str(proxy_data["protocol"]).strip().lower()
                supported_protocols = {"http", "https", "socks", "socks4", "socks5", "socks5h"}
                if proxy_protocol not in supported_protocols:
                    logger.warning(
                        f"Unsupported proxy protocol for domain={domain}: {proxy_protocol}"
                    )
                    return None

                logger.info(
                    f"Proxy acquired for domain={domain}: "
                    f"{proxy_host}:{proxy_port} ({proxy_protocol})"
                )
                return KProxyInfo(
                    host=proxy_host,
                    port=proxy_port,
                    username=proxy_data.get("username"),
                    password=proxy_data.get("password"),
                    protocol=_normalize_proxy_scheme(proxy_protocol),
                )
            else:
                logger.warning(
                    f"No proxy available for domain={domain}, "
                    f"status={data.get('status')}, message={data.get('message')}"
                )
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
            logger.info(
                f"Proxy result reported: domain={domain}, proxy={proxy.host}:{proxy.port}, "
                f"success={success}"
            )

        except Exception as e:
            logger.error(f"Failed to report proxy result: {e}")


def configure_default_proxy_provider() -> None:
    from crawl import configure_proxy_provider

    service_url = (settings.KPROXY_SERVICE_URL or '').strip()
    if not service_url:
        raise ValueError("配置项 KPROXY_SERVICE_URL 未设置")

    provider = KProxyProvider(
        base_url=service_url,
        timeout=settings.KPROXY_TIMEOUT,
    )
    configure_proxy_provider(provider)
    logger.info(
        "Configured global proxy provider: KProxyProvider(base_url=%s, timeout=%s)",
        provider.base_url,
        provider.timeout,
    )
