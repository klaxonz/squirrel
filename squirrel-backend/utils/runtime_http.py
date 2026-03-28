from __future__ import annotations


_cloudflare_bypass_client: object | None = None


def set_cloudflare_bypass_client(client: object | None) -> None:
    global _cloudflare_bypass_client
    _cloudflare_bypass_client = client


def get_cloudflare_bypass_client() -> object | None:
    return _cloudflare_bypass_client


def reset_runtime_http_state() -> None:
    set_cloudflare_bypass_client(None)
