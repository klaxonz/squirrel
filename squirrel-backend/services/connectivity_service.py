"""Site connectivity service - provides site accessibility detection, response time measurement, etc.
"""
import inspect
import logging
import socket
import time
from urllib.parse import urlparse

import httpx

from schemas.connectivity import ConnectivityTestResponse
from utils.runtime_http import get_cloudflare_bypass_client

logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-CH-UA": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
}

AGGRESSIVE_HEADER_EXTRAS = {
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
}

RESTRICTED_STATUS_CODES = {401, 403, 406, 409, 412, 429}


async def _await_if_needed(result):
    if inspect.isawaitable(result):
        return await result
    return result


def build_browser_headers(target_url: str, aggressive: bool = False) -> dict[str, str]:
    headers = dict(BROWSER_HEADERS)
    parsed = urlparse(target_url)
    if parsed.scheme and parsed.netloc:
        origin = f"{parsed.scheme}://{parsed.netloc}"
        headers.setdefault("Referer", origin + "/")
        headers.setdefault("Origin", origin)
    if aggressive:
        headers.update(AGGRESSIVE_HEADER_EXTRAS)
    return headers


async def fetch_with_fallback(
    client: httpx.AsyncClient,
    url: str,
) -> httpx.Response:
    response = await client.get(url, headers=build_browser_headers(url))
    if response.status_code in RESTRICTED_STATUS_CODES:
        logger.info("Site %s returned restricted status %s, retrying with aggressive headers", url, response.status_code)
        fallback_response = await client.get(url, headers=build_browser_headers(url, aggressive=True))
        if fallback_response.status_code not in RESTRICTED_STATUS_CODES:
            logger.info("Aggressive headers resolved restriction for %s", url)
            return fallback_response
        bypass_response = await _fetch_with_cloudflare_bypass(url)
        if bypass_response is not None and bypass_response.status_code not in RESTRICTED_STATUS_CODES:
            logger.info("Cloudflare bypass resolved restriction for %s", url)
            return bypass_response
        response = fallback_response
    return response


async def _fetch_with_cloudflare_bypass(url: str):
    client = get_cloudflare_bypass_client()
    if client is None:
        return None

    headers = build_browser_headers(url, aggressive=True)
    try:
        return await _await_if_needed(client.html(url, headers=headers))
    except Exception as exc:
        logger.warning("Cloudflare bypass connectivity test failed for %s: %s", url, exc)
        return None


async def test_site_connectivity(
    url: str,
    timeout: int = 10,
    follow_redirects: bool = True,
) -> ConnectivityTestResponse:
    """Test connectivity of a single site

    Args:
        url: The URL to test
        timeout: Timeout in seconds
        follow_redirects: Whether to follow redirects

    Returns:
        ConnectivityTestResponse: Test result

    """
    start_time = time.time()
    test_result = ConnectivityTestResponse(
        url=url,
        status="unknown",
        accessible=False,
    )

    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        if hostname:
            try:
                ip_address = socket.gethostbyname(hostname)
                test_result.dns_resolved = True
                test_result.ip_address = ip_address
                logger.info("DNS resolved for %s: %s", hostname, ip_address)
            except socket.gaierror as e:
                test_result.dns_resolved = False
                test_result.status = "error"
                test_result.error_message = f"DNS\u89e3\u6790\u5931\u8d25: {e!s}"
                logger.warning("DNS resolution failed for %s: %s", hostname, e)
                return test_result

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=follow_redirects,
            verify=False,
        ) as client:
            try:
                response = await fetch_with_fallback(client, url)
                response_time = (time.time() - start_time) * 1000

                test_result.status_code = response.status_code
                test_result.response_time = round(response_time, 2)
                test_result.final_url = str(response.url)

                test_result.headers = {
                    "content-type": response.headers.get("content-type", ""),
                    "server": response.headers.get("server", ""),
                    "content-length": response.headers.get("content-length", ""),
                }

                if 200 <= response.status_code < 400:
                    test_result.status = "success"
                    test_result.accessible = True
                    logger.info("Site %s is accessible, status: %s, time: %f'.2f'ms", url, response.status_code, response_time)
                elif response.status_code in RESTRICTED_STATUS_CODES:
                    test_result.status = "restricted"
                    test_result.accessible = True
                    test_result.error_message = f"\u7ad9\u70b9\u54cd\u5e94\u9650\u5236HTTP\u72b6\u6001\u7801: {response.status_code}"
                    logger.info("Site %s responded with restricted status %s but is reachable", url, response.status_code)
                else:
                    test_result.status = "failed"
                    test_result.accessible = False
                    test_result.error_message = f"HTTP\u72b6\u6001\u7801: {response.status_code}"
                    logger.warning("Site %s returned status %s", url, response.status_code)

            except httpx.TimeoutException as e:
                test_result.status = "timeout"
                test_result.accessible = False
                test_result.error_message = f"\u8bf7\u6c42\u8d85\u65f6\uff08{timeout}\u79d2\uff09"
                logger.warning("Timeout testing %s: %s", url, e)

            except httpx.ConnectError as e:
                test_result.status = "error"
                test_result.accessible = False
                test_result.error_message = f"\u8fde\u63a5\u5931\u8d25: {e!s}"
                logger.warning("Connection error testing %s: %s", url, e)

            except httpx.HTTPError as e:
                test_result.status = "error"
                test_result.accessible = False
                test_result.error_message = f"HTTP\u9519\u8bef: {e!s}"
                logger.warning("HTTP error testing %s: %s", url, e)

    except Exception as e:
        test_result.status = "error"
        test_result.accessible = False
        test_result.error_message = f"\u672a\u77e5\u9519\u8bef: {e!s}"
        logger.error("Unexpected error testing %s: %s", url, e, exc_info=True)

    return test_result
