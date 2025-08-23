from dataclasses import dataclass


@dataclass
class DomainConfig:
    """域名特定配置"""
    domain: str
    connect_timeout: float
    read_timeout: float
    max_retries: int
    chunk_size: int
    max_connections: int
    keepalive_expiry: float
    enable_http2: bool = True

