from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Optional, Protocol, TypeVar, runtime_checkable

from .exceptions import NetworkError

logger = logging.getLogger(__name__)

T = TypeVar('T')


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


def _build_proxy_unavailable_error(domain: Optional[str], reason: str) -> NetworkError:
    normalized_domain = domain or 'unknown'
    return NetworkError(
        f'Proxy unavailable for domain={normalized_domain}: {reason}',
        context={
            'domain': normalized_domain,
            'reason': reason,
        },
    )


@contextmanager
def proxy_context(
    domain: str,
    configure_callback: Optional[Callable[[Optional[str]], None]] = None,
    restore_callback: Optional[Callable[[Optional[str]], None]] = None,
):
    """通用代理管理上下文管理器

    Args:
        domain: 目标域名
        configure_callback: 配置代理的回调函数，接收代理URL字符串
        restore_callback: 恢复代理的回调函数，接收之前的代理URL字符串

    Yields:
        Tuple[Optional[ProxyProvider], Optional[ProxyInfo]]: (代理提供者, 代理信息)

    Example:
        with proxy_context('bilibili.com', lambda url: request_settings.set_proxy(url)) as (provider, proxy_info):
            result = sync(coro)
    """
    proxy_provider = get_proxy_provider()
    proxy_info = None
    success = False
    previous_proxy = None

    try:
        if not proxy_provider:
            logger.error(f'Proxy provider not configured for domain={domain}')
            raise _build_proxy_unavailable_error(domain, 'proxy provider not configured')

        try:
            proxy_info = proxy_provider.get_proxy(domain)
        except Exception as e:
            logger.warning(f'Failed to get proxy for domain={domain}: {e}')
            raise _build_proxy_unavailable_error(domain, 'failed to get proxy') from e

        if not proxy_info:
            logger.error(f'No proxy available for domain={domain}')
            raise _build_proxy_unavailable_error(domain, 'no proxy available')

        proxy_url = proxy_info.to_url()
        logger.info(f'Proxy configured: domain={domain}, proxy={proxy_info.host}:{proxy_info.port}')

        if configure_callback:
            configure_callback(proxy_url)

        yield proxy_provider, proxy_info
        success = True

    finally:
        if restore_callback:
            restore_callback(previous_proxy)

        if proxy_provider and proxy_info:
            try:
                proxy_provider.report_result(proxy_info, domain, success)
            except Exception as e:
                logger.warning(f'Failed to report proxy result: {e}')


def execute_with_proxy_rotation(
    domain: str,
    execute_func: Callable[[], T],
    configure_callback: Callable[[Optional[str]], None],
    restore_callback: Optional[Callable[[], None]] = None,
    should_retry: Optional[Callable[[Exception], bool]] = None,
    max_retries: int = 3,
) -> T:
    """通用代理轮换执行函数

    当执行失败时，自动获取新的代理并重试。

    Args:
        domain: 目标域名
        execute_func: 执行函数，无参数，返回结果
        configure_callback: 配置代理的回调函数，接收代理URL字符串
        restore_callback: 恢复代理的回调函数，无参数
        should_retry: 判断是否应该重试的函数，接收异常，返回bool。默认所有异常都重试
        max_retries: 最大重试次数

    Returns:
        执行函数的返回值

    Example:
        result = execute_with_proxy_rotation(
            domain='bilibili.com',
            execute_func=lambda: sync(coro),
            configure_callback=lambda url: request_settings.set_proxy(url or ''),
            restore_callback=lambda: request_settings.set_proxy(previous_proxy),
            max_retries=3
        )
    """
    proxy_provider = get_proxy_provider()

    if not proxy_provider:
        logger.error(f'Proxy provider not configured for domain={domain}')
        raise _build_proxy_unavailable_error(domain, 'proxy provider not configured')

    try:
        for attempt in range(max_retries + 1):
            proxy_info = None

            try:
                proxy_info = proxy_provider.get_proxy(domain)
            except Exception as e:
                logger.warning(f'Failed to get proxy for domain={domain}: {e}')
                raise _build_proxy_unavailable_error(domain, 'failed to get proxy') from e

            if proxy_info:
                proxy_url = proxy_info.to_url()
                logger.info(
                    f'Proxy configured (attempt {attempt + 1}/{max_retries + 1}): '
                    f'domain={domain}, proxy={proxy_info.host}:{proxy_info.port}'
                )
                configure_callback(proxy_url)
            else:
                logger.error(f'No proxy available for domain={domain}')
                raise _build_proxy_unavailable_error(domain, 'no proxy available')

            try:
                result = execute_func()

                if proxy_info:
                    try:
                        proxy_provider.report_result(proxy_info, domain, True)
                    except Exception as e:
                        logger.warning(f'Failed to report proxy success: {e}')

                return result

            except Exception as e:
                if proxy_info:
                    try:
                        proxy_provider.report_result(proxy_info, domain, False)
                    except Exception as report_error:
                        logger.warning(f'Failed to report proxy failure: {report_error}')

                is_last_attempt = attempt >= max_retries
                should_not_retry = should_retry and not should_retry(e)

                if is_last_attempt:
                    logger.warning(
                        f'Proxy rotation exhausted after {attempt + 1} attempts for domain={domain}'
                    )
                    raise

                if should_not_retry:
                    logger.info(f'Exception not retryable for domain={domain}: {type(e).__name__}')
                    raise

                logger.info(
                    f'Request failed with proxy, retrying with new proxy '
                    f'(attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__}'
                )

        raise RuntimeError(f'Proxy rotation failed for domain={domain}')

    finally:
        if restore_callback:
            restore_callback()
