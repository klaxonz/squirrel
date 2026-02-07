from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass
class ProxyInfo:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None

    def to_url(self, scheme: str = "http") -> str:
        if self.username and self.password:
            return f"{scheme}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{scheme}://{self.host}:{self.port}"

    def to_dict(self) -> dict:
        return {
            "http": self.to_url("http"),
            "https": self.to_url("https"),
        }


@runtime_checkable
class ProxyProvider(Protocol):
    def get_proxy(self, domain: Optional[str] = None) -> Optional[ProxyInfo]:
        ...

    def report_result(self, proxy: ProxyInfo, domain: str, success: bool) -> None:
        ...


_global_proxy_provider: Optional[ProxyProvider] = None


def configure_proxy_provider(provider: Optional[ProxyProvider]) -> None:
    global _global_proxy_provider
    _global_proxy_provider = provider


def get_proxy_provider() -> Optional[ProxyProvider]:
    return _global_proxy_provider
