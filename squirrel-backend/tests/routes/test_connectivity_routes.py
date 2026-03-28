import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes import connectivity as connectivity_route


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


def test_connectivity_uses_bypass_after_restricted_status(monkeypatch):
    bypass_calls = []

    class _BypassClient:
        def html(self, url, headers=None):
            bypass_calls.append({'url': url, 'headers': headers})
            return SimpleNamespace(
                status_code=200,
                url='https://javdb.com/?via=bypass',
                headers={'content-type': 'text/html', 'server': 'cloudflare-bypass'},
            )

    monkeypatch.setattr(connectivity_route.socket, 'gethostbyname', lambda _host: '198.18.0.69')
    monkeypatch.setattr(
        connectivity_route.httpx,
        'AsyncClient',
        lambda **_kwargs: _FakeAsyncClient([
            _response(403),
            _response(403),
        ]),
    )
    monkeypatch.setattr(connectivity_route, 'get_cloudflare_bypass_client', lambda: _BypassClient())

    result = asyncio.run(connectivity_route.test_site_connectivity('https://javdb.com'))

    assert result.status == 'success'
    assert result.accessible is True
    assert result.status_code == 200
    assert str(result.final_url) == 'https://javdb.com/?via=bypass'
    assert bypass_calls == [{
        'url': 'https://javdb.com',
        'headers': connectivity_route.build_browser_headers('https://javdb.com', aggressive=True),
    }]


def test_connectivity_preserves_restricted_status_when_bypass_cannot_help(monkeypatch):
    class _BypassClient:
        def html(self, url, headers=None):
            return SimpleNamespace(
                status_code=403,
                url=url,
                headers={'content-type': 'text/html'},
            )

    monkeypatch.setattr(connectivity_route.socket, 'gethostbyname', lambda _host: '198.18.0.69')
    monkeypatch.setattr(
        connectivity_route.httpx,
        'AsyncClient',
        lambda **_kwargs: _FakeAsyncClient([
            _response(403),
            _response(403),
        ]),
    )
    monkeypatch.setattr(connectivity_route, 'get_cloudflare_bypass_client', lambda: _BypassClient())

    result = asyncio.run(connectivity_route.test_site_connectivity('https://javdb.com'))

    assert result.status == 'restricted'
    assert result.accessible is True
    assert result.status_code == 403
