from typing import Protocol

from squirrel_cf_bypass.app.core.models import ClearanceRecord
from squirrel_cf_bypass.app.core.models import HtmlResult


class Solver(Protocol):
    async def fetch_html(
        self,
        url: str,
        proxy: str | None = None,
        cached_record: ClearanceRecord | None = None,
        custom_headers: dict[str, str] | None = None,
    ) -> HtmlResult | None:
        ...
