from __future__ import annotations

import json
import urllib.request
from typing import Optional


class SiteRuntimeTransportClient:
    def request_json(
        self,
        endpoint: str,
        path: str,
        payload: Optional[dict] = None,
        timeout: float = 5.0,
    ) -> dict:
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(
            f'{endpoint}{path}',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST' if payload is not None else 'GET',
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            raw_body = response.read().decode('utf-8')
        parsed = json.loads(raw_body or '{}')
        return parsed if isinstance(parsed, dict) else {}
