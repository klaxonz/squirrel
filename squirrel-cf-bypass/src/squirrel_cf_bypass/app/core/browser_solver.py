import asyncio

from squirrel_cf_bypass.app.core.models import HtmlResult


class BrowserSolver:
    ready = True

    async def _restore_cached_cookies(self, context, url: str, record) -> None:
        cookies = [
            {'name': name, 'value': value, 'url': url}
            for name, value in record.cookies.items()
        ]
        if cookies:
            await context.add_cookies(cookies)

    @staticmethod
    def _is_challenge_page(title: str, html: str) -> bool:
        title_lower = title.lower()
        html_lower = html.lower()
        return 'just a moment' in title_lower or 'please complete the captcha' in html_lower

    async def fetch_html(
        self,
        url: str,
        proxy: str | None = None,
        cached_record=None,
        custom_headers: dict[str, str] | None = None,
    ) -> HtmlResult | None:
        from camoufox.async_api import AsyncCamoufox
        from playwright_captcha import ClickSolver
        from playwright_captcha import FrameworkType

        camoufox = AsyncCamoufox(headless=True, humanize=False, i_know_what_im_doing=True)
        async with camoufox as browser:
            context_kwargs = {'proxy': {'server': proxy}} if proxy else {}
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            if cached_record is not None:
                await self._restore_cached_cookies(context, url, cached_record)
            if custom_headers:
                await page.set_extra_http_headers(custom_headers)

            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            title = await page.title()
            html = await page.content()

            if self._is_challenge_page(title, html):
                async with ClickSolver(framework=FrameworkType.CAMOUFOX, page=page, max_attempts=2, attempt_delay=1) as solver:
                    await asyncio.wait_for(
                        solver.solve_captcha(
                            captcha_container=page,
                            expected_content_selector='body',
                        ),
                        timeout=60,
                    )
                await asyncio.sleep(2)
                html = await page.content()

            cookies = {
                cookie['name']: cookie['value']
                for cookie in await context.cookies()
            }
            user_agent = await page.evaluate('navigator.userAgent')
            return HtmlResult(
                html=html,
                final_url=page.url,
                status_code=200,
                cookies=cookies,
                user_agent=user_agent,
            )
