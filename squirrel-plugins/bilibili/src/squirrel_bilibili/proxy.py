from __future__ import annotations

from crawl import VideoProxyBase, register_proxy

try:  # 后端环境可用：复用默认实现
    from core.streaming.proxy import VideoProxy as _BackendVideoProxy
except Exception:  # pragma: no cover - SDK / 非后端环境
    _BackendVideoProxy = None


_BaseProxy = _BackendVideoProxy or VideoProxyBase


@register_proxy
class BilibiliProxy(_BaseProxy):
    domain = 'bilibili.com'

    if _BackendVideoProxy is None:  # pragma: no cover - 仅在 SDK 环境触发
        async def handle_stream(self, url: str, **kwargs):  # type: ignore[override]
            raise NotImplementedError(
                "BilibiliProxy 仅在后端运行环境可用，请在后端项目中加载插件"
            )


