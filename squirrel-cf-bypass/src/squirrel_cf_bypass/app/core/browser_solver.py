import asyncio
import logging
import os
import random
from urllib.parse import urlparse

from squirrel_cf_bypass.app.core.models import HtmlResult

logger = logging.getLogger(__name__)

OPERATING_SYSTEMS = ("windows", "macos", "linux")
SCREEN_RESOLUTIONS = (
    (1920, 1080),
    (1920, 1200),
    (2560, 1440),
    (1680, 1050),
    (1600, 900),
    (1366, 768),
    (1440, 900),
    (1536, 864),
    (2560, 1600),
    (3840, 2160),
)
INITIAL_WAIT_MAX = 5.0
BYPASS_CHECK_INTERVAL = 0.5
COOKIE_SET_WAIT = 2.0


class BrowserSolver:
    ready = True

    def __init__(self):
        self._browser_entries = {}
        self._locks = {}

    @staticmethod
    def _key(url: str, proxy: str | None) -> tuple[str, str | None]:
        hostname = str(urlparse(url).hostname or "").strip().lower()
        return hostname, proxy or None

    def _lock_for(self, key: tuple[str, str | None]) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    @staticmethod
    def _resolve_browser_os(user_agent: str | None) -> str:
        ua_lower = str(user_agent or "").lower()
        if "windows" in ua_lower:
            return "windows"
        if "macintosh" in ua_lower or "mac os" in ua_lower:
            return "macos"
        if "linux" in ua_lower or "x11" in ua_lower:
            return "linux"
        return random.choice(OPERATING_SYSTEMS)

    @staticmethod
    def _build_browser_config(user_agent: str | None, selected_os: str, lang: str = "en-US") -> dict:
        firefox_version = random.randint(140, 145)
        screen_width, screen_height = random.choice(SCREEN_RESOLUTIONS)
        toolbar_height = random.randint(70, 100)
        languages = [lang]
        if lang != "en-US" and not lang.startswith("en"):
            languages.append("en-US")

        config = {
            "window.outerHeight": screen_height,
            "window.outerWidth": screen_width,
            "window.innerHeight": screen_height - toolbar_height,
            "window.innerWidth": screen_width,
            "window.history.length": random.randint(2, 8),
            "navigator.appCodeName": "Mozilla",
            "navigator.appName": "Netscape",
            "navigator.hardwareConcurrency": random.choice([2, 4, 6, 8, 12, 16, 20, 24]),
            "navigator.product": "Gecko",
            "navigator.productSub": "20100101",
            "navigator.language": lang,
            "navigator.languages": languages,
        }

        if selected_os == "windows":
            win_version = random.choice(("Windows NT 10.0; Win64; x64", "Windows NT 11.0; Win64; x64"))
            config.update({
                "navigator.userAgent": user_agent or f"Mozilla/5.0 ({win_version}; rv:{firefox_version}.0) Gecko/20100101 Firefox/{firefox_version}.0",
                "navigator.appVersion": f"5.0 ({win_version})",
                "navigator.oscpu": win_version,
                "navigator.platform": "Win32",
                "navigator.maxTouchPoints": random.choice([0, 10]),
            })
            return config

        if selected_os == "macos":
            mac_ver_underscore, mac_ver_dot = random.choice((("13_0", "13.0"), ("14_0", "14.0"), ("15_0", "15.0")))
            config.update({
                "navigator.userAgent": user_agent or f"Mozilla/5.0 (Macintosh; Intel Mac OS X {mac_ver_underscore}; rv:{firefox_version}.0) Gecko/20100101 Firefox/{firefox_version}.0",
                "navigator.appVersion": "5.0 (Macintosh)",
                "navigator.oscpu": f"Intel Mac OS X {mac_ver_dot}",
                "navigator.platform": "MacIntel",
                "navigator.maxTouchPoints": 0,
            })
            return config

        linux_distro = random.choice((
            "X11; Linux x86_64",
            "X11; Ubuntu; Linux x86_64",
            "X11; Fedora; Linux x86_64",
            "X11; Debian; Linux x86_64",
            "X11; CentOS; Linux x86_64",
            "X11; Arch Linux; Linux x86_64",
            "X11; openSUSE; Linux x86_64",
            "X11; Manjaro; Linux x86_64",
        ))
        config.update({
            "navigator.userAgent": user_agent or f"Mozilla/5.0 ({linux_distro}; rv:{firefox_version}.0) Gecko/20100101 Firefox/{firefox_version}.0",
            "navigator.appVersion": "5.0 (X11)",
            "navigator.oscpu": "Linux x86_64",
            "navigator.platform": "Linux x86_64",
            "navigator.maxTouchPoints": 0,
        })
        return config

    def _build_camoufox_kwargs(self, proxy: str | None, cached_record=None) -> dict:
        from playwright_captcha.utils.camoufox_add_init_script.add_init_script import get_addon_path

        user_agent = getattr(cached_record, "user_agent", None)
        selected_os = getattr(cached_record, "browser_os", None) or self._resolve_browser_os(user_agent)
        browser_config = getattr(cached_record, "browser_config", None)
        if browser_config is None:
            browser_config = self._build_browser_config(user_agent=user_agent, selected_os=selected_os)

        return {
            "headless": True,
            "geoip": bool(proxy),
            "humanize": False,
            "os": selected_os,
            "locale": "en-US",
            "i_know_what_im_doing": True,
            "config": {"forceScopeAccess": True, **browser_config},
            "disable_coop": True,
            "main_world_eval": True,
            "addons": [os.path.abspath(get_addon_path())],
            "block_images": False,
            "block_webrtc": True,
            "enable_cache": False,
        }

    @staticmethod
    def _extract_browser_identity(camoufox_kwargs: dict) -> tuple[dict | None, str | None]:
        config = camoufox_kwargs.get("config")
        if isinstance(config, dict):
            browser_config = dict(config)
            browser_config.pop("forceScopeAccess", None)
        else:
            browser_config = None
        browser_os = camoufox_kwargs.get("os")
        return browser_config, browser_os if isinstance(browser_os, str) else None

    async def _restore_cached_cookies(self, context, url: str, record) -> None:
        cookies = [
            {"name": name, "value": value, "url": url}
            for name, value in record.cookies.items()
        ]
        if cookies:
            await context.add_cookies(cookies)

    @staticmethod
    def _is_challenge_page(title: str, html: str) -> bool:
        title_lower = title.lower()
        html_lower = html.lower()
        return "just a moment" in title_lower or "please complete the captcha" in html_lower

    async def _is_bypassed(self, page) -> bool:
        title = await page.title()
        html = await page.content()
        return not self._is_challenge_page(title, html)

    async def _wait_for_page_ready(self, page, max_wait: float = INITIAL_WAIT_MAX) -> bool:
        elapsed = 0.0
        while elapsed < max_wait:
            if await self._is_bypassed(page):
                return True
            await asyncio.sleep(BYPASS_CHECK_INTERVAL)
            elapsed += BYPASS_CHECK_INTERVAL
        return False

    def _determine_challenge_type(self, title: str, html: str):
        from playwright_captcha import CaptchaType

        title_lower = title.lower()
        html_lower = html.lower()
        if "please complete the captcha" in html_lower:
            return CaptchaType.CLOUDFLARE_TURNSTILE
        if "just a moment" in title_lower:
            return CaptchaType.CLOUDFLARE_INTERSTITIAL
        return self._detect_captcha_type(html)

    @staticmethod
    def _detect_captcha_type(html: str):
        from playwright_captcha import CaptchaType

        html_lower = html.lower()
        turnstile_markers = (
            "cf-turnstile-response",
            "cf-turnstile",
            "challenges.cloudflare.com/turnstile/v0",
        )
        if any(marker in html_lower for marker in turnstile_markers):
            return CaptchaType.CLOUDFLARE_TURNSTILE

        interstitial_markers = (
            "/cdn-cgi/challenge-platform/",
            "cf_chl_",
        )
        if any(marker in html_lower for marker in interstitial_markers):
            return CaptchaType.CLOUDFLARE_INTERSTITIAL

        return None

    async def _detect_captcha_type_from_page(self, page, html: str):
        from playwright_captcha import CaptchaType

        detected_type = self._detect_captcha_type(html)
        if detected_type is CaptchaType.CLOUDFLARE_TURNSTILE:
            return detected_type

        # Managed challenge pages can inject Turnstile markers after the initial HTML snapshot.
        live_turnstile_selectors = (
            'input[name="cf-turnstile-response"]',
            'script[src*="challenges.cloudflare.com/turnstile/v0"]',
        )
        for selector in live_turnstile_selectors:
            try:
                if await page.locator(selector).count():
                    return CaptchaType.CLOUDFLARE_TURNSTILE
            except Exception:
                continue

        if detected_type is not None:
            return detected_type

        try:
            if await page.locator('script[src*="/cdn-cgi/challenge-platform/"]').count():
                return CaptchaType.CLOUDFLARE_INTERSTITIAL
        except Exception:
            return None

        return None

    async def _find_turnstile_container_box(self, page):
        script = """
() => {
  const input = document.querySelector('input[name="cf-turnstile-response"]');
  if (!input) {
    return null;
  }

  let current = input.parentElement;
  while (current) {
    const rect = current.getBoundingClientRect();
    if (rect.width >= 40 && rect.height >= 20) {
      return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
    }
    current = current.parentElement;
  }

  return null;
}
"""
        try:
            result = await page.evaluate(script)
        except Exception:
            return None
        return result if isinstance(result, dict) else None

    async def _attempt_manual_turnstile_click(self, page) -> bool:
        box = await self._find_turnstile_container_box(page)
        if not box:
            return False

        click_ratios = (0.26, 0.30, 0.34)
        y_ratio = 0.5

        for ratio in click_ratios:
            x = box["x"] + box["width"] * ratio
            y = box["y"] + box["height"] * y_ratio
            try:
                await page.mouse.move(x - 20, y, steps=12)
                await page.mouse.move(x, y, steps=8)
                await page.mouse.down()
                await asyncio.sleep(0.15)
                await page.mouse.up()
            except Exception:
                continue

            await asyncio.sleep(2)
            title = await page.title()
            html = await page.content()
            if not self._is_challenge_page(title, html):
                return True

        return False

    async def _read_result_from_page(self, context, page, browser_config, browser_os, source: str) -> HtmlResult:
        cookies = {
            cookie["name"]: cookie["value"]
            for cookie in await context.cookies()
        }
        user_agent = await page.evaluate("navigator.userAgent")
        return HtmlResult(
            html=await page.content(),
            final_url=page.url,
            status_code=200,
            cookies=cookies,
            user_agent=user_agent,
            browser_config=browser_config,
            browser_os=browser_os,
            source=source,
        )

    async def _close_entry(self, key: tuple[str, str | None]) -> None:
        entry = self._browser_entries.pop(key, None)
        if not entry:
            return
        manager = entry.get("manager")
        if manager is not None:
            await manager.__aexit__(None, None, None)

    async def clear_runtime_state(self) -> None:
        keys = list(self._browser_entries)
        for key in keys:
            await self._close_entry(key)

    async def _fetch_with_entry(self, key, url: str, custom_headers: dict[str, str] | None):
        entry = self._browser_entries.get(key)
        if not entry:
            return None

        page = entry["page"]
        context = entry["context"]
        if custom_headers:
            await page.set_extra_http_headers(custom_headers)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            if not await self._wait_for_page_ready(page):
                title = await page.title()
                html = await page.content()
                if self._is_challenge_page(title, html):
                    await self._close_entry(key)
                    return None
            return await self._read_result_from_page(
                context,
                page,
                entry.get("browser_config"),
                entry.get("browser_os"),
                "browser-cache",
            )
        except Exception:
            logger.warning("Cached browser context failed for %s", url, exc_info=True)
            await self._close_entry(key)
            return None

    async def fetch_html(
        self,
        url: str,
        proxy: str | None = None,
        cached_record=None,
        custom_headers: dict[str, str] | None = None,
    ) -> HtmlResult | None:
        from camoufox.async_api import AsyncCamoufox
        from playwright_captcha import CaptchaType, ClickSolver, FrameworkType

        key = self._key(url, proxy)
        async with self._lock_for(key):
            cached_result = await self._fetch_with_entry(key, url, custom_headers)
            if cached_result is not None:
                return cached_result

            camoufox_kwargs = self._build_camoufox_kwargs(proxy=proxy, cached_record=cached_record)
            browser_config, browser_os = self._extract_browser_identity(camoufox_kwargs)
            camoufox = AsyncCamoufox(**camoufox_kwargs)
            browser = await camoufox.__aenter__()
            context_kwargs = {"proxy": {"server": proxy}} if proxy else {}
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            if cached_record is not None:
                await self._restore_cached_cookies(context, url, cached_record)
            if custom_headers:
                await page.set_extra_http_headers(custom_headers)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                title = await page.title()
                html = await page.content()
            except Exception:
                logger.warning("Browser navigation failed for %s", url, exc_info=True)
                await camoufox.__aexit__(None, None, None)
                return None

            if self._is_challenge_page(title, html):
                if await self._wait_for_page_ready(page):
                    title = await page.title()
                    html = await page.content()
                else:
                    title = await page.title()
                    html = await page.content()
                    captcha_type = self._determine_challenge_type(title, html) or CaptchaType.CLOUDFLARE_INTERSTITIAL

                    if captcha_type is CaptchaType.CLOUDFLARE_TURNSTILE:
                        manually_solved = await self._attempt_manual_turnstile_click(page)
                        if manually_solved:
                            title = await page.title()
                            html = await page.content()
                        else:
                            logger.info("Manual Turnstile click fallback did not bypass %s", url)

                    if self._is_challenge_page(title, html):
                        try:
                            async with ClickSolver(framework=FrameworkType.CAMOUFOX, page=page, max_attempts=2, attempt_delay=1) as solver:
                                await asyncio.wait_for(
                                    solver.solve_captcha(
                                        captcha_container=page,
                                        captcha_type=captcha_type,
                                        expected_content_selector="#root",
                                    ),
                                    timeout=60,
                                )
                        except Exception:
                            logger.warning("Captcha solving failed for %s", url, exc_info=True)
                            await camoufox.__aexit__(None, None, None)
                            return None

                    await self._wait_for_page_ready(page)
                    await asyncio.sleep(COOKIE_SET_WAIT)
                    try:
                        title = await page.title()
                        html = await page.content()
                    except Exception:
                        await camoufox.__aexit__(None, None, None)
                        return None
                if self._is_challenge_page(title, html):
                    await camoufox.__aexit__(None, None, None)
                    return None

            self._browser_entries[key] = {
                "manager": camoufox,
                "browser": browser,
                "context": context,
                "page": page,
                "browser_config": browser_config,
                "browser_os": browser_os,
            }
            return await self._read_result_from_page(context, page, browser_config, browser_os, "solver")
