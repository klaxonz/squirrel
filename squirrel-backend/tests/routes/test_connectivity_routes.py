import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import infrastructure.site_catalog.connectivity as connectivity_service


class _FakeAsyncClient:
    def __init__(self, responses):
        self._responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, _url, headers=None):
        assert headers is not None
        return self._responses.pop(0)


def _response(status_code, url='https://javdb.com', headers=None):
    return SimpleNamespace(
        status_code=status_code,
        url=url,
        headers=headers or {},
    )


def test_connectivity_reports_restricted_status(monkeypatch):
    monkeypatch.setattr(connectivity_service.socket, 'gethostbyname', lambda _host: '198.18.0.69')
    monkeypatch.setattr(
        connectivity_service.httpx,
        'AsyncClient',
        lambda **_kwargs: _FakeAsyncClient(
            [
                _response(403),
            ]
        ),
    )

    result = asyncio.run(connectivity_service.test_site_connectivity('https://javdb.com'))

    assert result.status == 'restricted'
    assert result.accessible is True
    assert result.status_code == 403
