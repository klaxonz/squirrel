import logging
import time
from urllib.parse import urlparse
from urllib.parse import urljoin

from curl_cffi.requests import AsyncSession

from squirrel_cf_bypass.app.core.cache import ClearanceCache
from squirrel_cf_bypass.app.core.models import ClearanceRecord
from squirrel_cf_bypass.app.core.models import HtmlResult
from squirrel_cf_bypass.app.core.models import MirrorResult
from squirrel_cf_bypass.app.core.session_pool import SessionPool

logger = logging.getLogger(__name__)


class CloudflareBypassService:
    def __init__(self, solver, cache: ClearanceCache, session_pool: SessionPool, ttl_seconds: float = 900):
        self._solver = solver
        self._cache = cache
        self._session_pool = session_pool
        self._ttl_seconds = ttl_seconds

    def health_payload(self) -> dict:
        return {
            'status': 'ok',
            'version': '0.1.0',
            'solver_ready': bool(getattr(self._solver, 'ready', False)),
            'cache_entries': self._cache.size(),
            'session_entries': self._session_pool.size(),
        }

    async def clear_runtime_state(self) -> None:
        self._cache.clear()
        await self._session_pool.clear()

    async def fetch_html(
        self,
        url: str,
        proxy: str | None = None,
        custom_headers: dict[str, str] | None = None,
        bypass_cache: bool = False,
    ):
        hostname = str(urlparse(url).hostname or '').strip().lower()
        cached_record = None if bypass_cache else self._cache.get(hostname, proxy)
        if cached_record is not None:
            logger.info('Cloudflare clearance cache hit for %s; trying cached HTTP fetch', hostname)
            cached_result = await self._fetch_html_with_cached_clearance(
                url,
                hostname,
                proxy,
                cached_record,
                custom_headers=custom_headers,
            )
            if cached_result is not None:
                return cached_result
            logger.info('Cached HTTP fetch hit Cloudflare challenge for %s; falling back to browser', hostname)
        elif bypass_cache:
            logger.info('Cloudflare clearance cache bypass requested for %s', hostname)
        else:
            logger.info('Cloudflare clearance cache miss for %s; using browser', hostname)

        result = await self._solver.fetch_html(
            url,
            proxy=proxy,
            cached_record=cached_record,
            custom_headers=custom_headers,
        )
        if result is None:
            return None
        result.source = result.source or 'solver'
        record = ClearanceRecord(
            cookies=result.cookies,
            user_agent=result.user_agent,
            created_at=time.time(),
            expires_at=time.time() + self._ttl_seconds,
            browser_config=result.browser_config,
            browser_os=result.browser_os,
        )
        self._cache.set(hostname, proxy, record)
        logger.info('Cloudflare clearance cached for %s', hostname)
        return result

    @staticmethod
    def _is_challenge_response(status_code: int, html: str) -> bool:
        html_lower = html.lower()
        return (
            status_code in {403, 503}
            or '<title>just a moment' in html_lower
            or 'please complete the captcha' in html_lower
            or '/cdn-cgi/challenge-platform/' in html_lower
            or 'cf-turnstile-response' in html_lower
            or 'challenges.cloudflare.com/turnstile/v0' in html_lower
        )

    def _get_or_create_session(self, hostname: str, proxy: str | None):
        session = self._session_pool.get(hostname, proxy)
        if session is not None:
            return session

        proxies = {'http': proxy, 'https': proxy} if proxy else None
        session = AsyncSession(impersonate='firefox', proxies=proxies, timeout=30)
        self._session_pool.store(hostname, proxy, session)
        return session

    async def _fetch_html_with_cached_clearance(
        self,
        url: str,
        hostname: str,
        proxy: str | None,
        cached_record: ClearanceRecord,
        custom_headers: dict[str, str] | None = None,
    ) -> HtmlResult | None:
        session = self._get_or_create_session(hostname, proxy)
        upstream_headers = self._strip_control_headers(custom_headers or {})
        upstream_headers['user-agent'] = cached_record.user_agent
        cookie_header = self._merge_cookie_header(upstream_headers.get('cookie', ''), cached_record.cookies)
        if cookie_header:
            upstream_headers['cookie'] = cookie_header

        response = await session.get(
            url,
            headers=upstream_headers,
            allow_redirects=True,
        )
        html = response.text
        if self._is_challenge_response(response.status_code, html):
            return None

        return HtmlResult(
            html=html,
            final_url=str(response.url),
            status_code=response.status_code,
            cookies=cached_record.cookies,
            user_agent=cached_record.user_agent,
            browser_config=cached_record.browser_config,
            browser_os=cached_record.browser_os,
            source='cache',
        )

    @staticmethod
    def _extract_control_headers(headers: dict[str, str]) -> tuple[str | None, str | None, bool]:
        hostname = None
        proxy = None
        bypass_cache = False
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower == 'x-hostname':
                hostname = value
            elif key_lower == 'x-proxy':
                proxy = value
            elif key_lower == 'x-bypass-cache':
                bypass_cache = value.lower() in {'1', 'true', 'yes', 'on'}
        return hostname, proxy, bypass_cache

    @staticmethod
    def _strip_control_headers(headers: dict[str, str]) -> dict[str, str]:
        return {
            key: value
            for key, value in headers.items()
            if key.lower() not in {'x-hostname', 'x-proxy', 'x-bypass-cache', 'host'}
        }

    @staticmethod
    def _merge_cookie_header(existing_cookie: str, cf_cookies: dict[str, str]) -> str:
        pairs: dict[str, str] = {}
        for item in existing_cookie.split(';'):
            if '=' in item:
                name, value = item.split('=', 1)
                pairs[name.strip()] = value.strip()
        pairs.update(cf_cookies)
        return '; '.join(f'{name}={value}' for name, value in pairs.items())

    async def mirror_request(
        self,
        method: str,
        path: str,
        query_string: str,
        headers: dict[str, str],
        body: bytes,
    ) -> MirrorResult:
        hostname, proxy, bypass_cache = self._extract_control_headers(headers)
        if not hostname:
            raise ValueError('x-hostname header is required')

        cached_record = None if bypass_cache else self._cache.get(hostname, proxy)
        if cached_record is None:
            seed_url = f'https://{hostname}/'
            html_result = await self.fetch_html(seed_url, proxy=proxy)
            if html_result is None:
                raise RuntimeError(f'Failed to seed clearance for {hostname}')
            cached_record = self._cache.get(hostname, proxy)
            if cached_record is None:
                raise RuntimeError(f'No cached clearance available for {hostname}')

        session = self._get_or_create_session(hostname, proxy)

        target_url = urljoin(f'https://{hostname}', path)
        if query_string:
            target_url = f'{target_url}?{query_string}'

        upstream_headers = self._strip_control_headers(headers)
        upstream_headers['user-agent'] = cached_record.user_agent
        cookie_header = self._merge_cookie_header(upstream_headers.get('cookie', ''), cached_record.cookies)
        if cookie_header:
            upstream_headers['cookie'] = cookie_header

        response = await session.request(
            method=method,
            url=target_url,
            headers=upstream_headers,
            data=body or None,
            allow_redirects=False,
        )
        if response.status_code == 403:
            self._cache.invalidate(hostname, proxy)

        return MirrorResult(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.content,
        )
