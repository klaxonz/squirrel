# Cloudflare Bypass Sidecar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repo-local `squirrel-cf-bypass` sidecar service that replaces the external Cloudflare bypass dependency while keeping `squirrel-backend` as a client-only consumer.

**Architecture:** Add a new top-level Python service project that exposes `health`, `cache/clear`, `html`, and mirrored request endpoints. Keep browser solving, clearance caching, and request-session reuse inside the sidecar, and make only the minimum backend and deployment changes needed to point existing bypass flows at the new process.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, pytest, curl_cffi, camoufox/Playwright-compatible solver abstraction, httpx

---

## File Map

### New sidecar project

- Create: `squirrel-cf-bypass/pyproject.toml`
- Create: `squirrel-cf-bypass/README.md`
- Create: `squirrel-cf-bypass/Dockerfile`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/__init__.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/__init__.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/main.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/__init__.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/routes.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/__init__.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/settings.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/models.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/cache.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/session_pool.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/solver.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/browser_solver.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/service.py`
- Create: `squirrel-cf-bypass/tests/test_health.py`
- Create: `squirrel-cf-bypass/tests/test_cache.py`
- Create: `squirrel-cf-bypass/tests/test_html_route.py`
- Create: `squirrel-cf-bypass/tests/test_mirror_route.py`
- Create: `squirrel-cf-bypass/tests/test_browser_solver.py`

### Existing backend and repo integration

- Modify: `squirrel-backend/utils/cloudflare_bypass.py`
- Modify: `squirrel-backend/schedule/tasks/cloudflare_heartbeat_task.py`
- Create: `squirrel-backend/tests/utils/test_cloudflare_bypass.py`
- Create: `squirrel-backend/tests/schedule/test_cloudflare_heartbeat_task.py`
- Modify: `docker-compose.yaml`
- Modify: `env.example`
- Modify: `README.md`

## Task 1: Scaffold the sidecar project and health endpoint

**Files:**
- Create: `squirrel-cf-bypass/pyproject.toml`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/__init__.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/__init__.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/main.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/__init__.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/routes.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/__init__.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/settings.py`
- Create: `squirrel-cf-bypass/tests/test_health.py`

- [ ] **Step 1: Write the failing health-route test**

```python
from fastapi.testclient import TestClient

from squirrel_cf_bypass.app.main import create_app


def test_health_reports_ok_defaults():
    client = TestClient(create_app())

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {
        'status': 'ok',
        'version': '0.1.0',
        'solver_ready': False,
        'cache_entries': 0,
        'session_entries': 0,
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
python -m pytest tests\test_health.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'squirrel_cf_bypass'`.

- [ ] **Step 3: Create the package skeleton and minimal FastAPI app**

`squirrel-cf-bypass/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "squirrel-cf-bypass"
version = "0.1.0"
description = "Repo-local Cloudflare bypass sidecar for Squirrel"
requires-python = ">=3.11"
dependencies = [
  "fastapi==0.111.0",
  "uvicorn==0.30.1",
  "pydantic-settings>=2.2.1",
  "httpx==0.27.0",
  "curl-cffi>=0.7.0",
  "camoufox>=0.4.11",
  "playwright-captcha>=0.5.1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
]

[tool.setuptools.packages.find]
where = ["src"]
```

`squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/settings.py`

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CF_BYPASS_HOST: str = '0.0.0.0'
    CF_BYPASS_PORT: int = 8001
    CF_BYPASS_LOG_LEVEL: str = 'INFO'


settings = Settings()
```

`squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/routes.py`

```python
from fastapi import APIRouter

router = APIRouter()


@router.get('/health')
def health():
    return {
        'status': 'ok',
        'version': '0.1.0',
        'solver_ready': False,
        'cache_entries': 0,
        'session_entries': 0,
    }
```

`squirrel-cf-bypass/src/squirrel_cf_bypass/app/main.py`

```python
from fastapi import FastAPI

from squirrel_cf_bypass.app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title='squirrel-cf-bypass')
    app.include_router(router)
    return app


app = create_app()
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
pip install -e .[dev]
python -m pytest tests\test_health.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add squirrel-cf-bypass/pyproject.toml squirrel-cf-bypass/src/squirrel_cf_bypass squirrel-cf-bypass/tests/test_health.py
git commit -m "feat: scaffold cloudflare bypass sidecar"
```

## Task 2: Add clearance cache and mirrored session-pool primitives

**Files:**
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/models.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/cache.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/session_pool.py`
- Create: `squirrel-cf-bypass/tests/test_cache.py`

- [ ] **Step 1: Write the failing cache and session-pool tests**

```python
import time

from squirrel_cf_bypass.app.core.cache import ClearanceCache
from squirrel_cf_bypass.app.core.models import ClearanceRecord
from squirrel_cf_bypass.app.core.session_pool import SessionPool


class DummySession:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


def test_clearance_cache_expires_entries():
    cache = ClearanceCache(ttl_seconds=0.01)
    record = ClearanceRecord(
        cookies={'cf_clearance': 'demo'},
        user_agent='UA',
        created_at=time.time(),
        expires_at=time.time() + 0.01,
    )
    cache.set('javdb.com', None, record)

    assert cache.get('javdb.com', None) is not None
    time.sleep(0.02)
    assert cache.get('javdb.com', None) is None


def test_session_pool_reuses_and_clears_sessions():
    pool = SessionPool(ttl_seconds=60, max_sessions=8)
    session = DummySession()

    pool.store('javdb.com', None, session)

    assert pool.get('javdb.com', None) is session
    pool.clear_sync()
    assert session.closed is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
python -m pytest tests\test_cache.py -q
```

Expected: FAIL because `ClearanceCache`, `ClearanceRecord`, and `SessionPool` do not exist.

- [ ] **Step 3: Implement the cache models and session pool**

`squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/models.py`

```python
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ClearanceRecord:
    cookies: dict[str, str]
    user_agent: str
    created_at: float
    expires_at: float


@dataclass(slots=True)
class HtmlResult:
    html: str
    final_url: str
    status_code: int
    cookies: dict[str, str]
    user_agent: str


@dataclass(slots=True)
class MirrorResult:
    status_code: int
    headers: dict[str, str]
    body: bytes


@dataclass(slots=True)
class SessionRecord:
    session: Any
    created_at: float
```

`squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/cache.py`

```python
import time

from squirrel_cf_bypass.app.core.models import ClearanceRecord


class ClearanceCache:
    def __init__(self, ttl_seconds: float):
        self._ttl_seconds = ttl_seconds
        self._items: dict[tuple[str, str | None], ClearanceRecord] = {}

    @staticmethod
    def _key(hostname: str, proxy: str | None) -> tuple[str, str | None]:
        return hostname.strip().lower(), proxy or None

    def get(self, hostname: str, proxy: str | None) -> ClearanceRecord | None:
        record = self._items.get(self._key(hostname, proxy))
        if record is None:
            return None
        if record.expires_at <= time.time():
            self._items.pop(self._key(hostname, proxy), None)
            return None
        return record

    def set(self, hostname: str, proxy: str | None, record: ClearanceRecord) -> None:
        self._items[self._key(hostname, proxy)] = record

    def invalidate(self, hostname: str, proxy: str | None) -> None:
        self._items.pop(self._key(hostname, proxy), None)

    def clear(self) -> None:
        self._items.clear()

    def size(self) -> int:
        return len(self._items)
```

`squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/session_pool.py`

```python
import asyncio
import time

from squirrel_cf_bypass.app.core.models import SessionRecord


class SessionPool:
    def __init__(self, ttl_seconds: float, max_sessions: int):
        self._ttl_seconds = ttl_seconds
        self._max_sessions = max_sessions
        self._items: dict[tuple[str, str | None], SessionRecord] = {}

    @staticmethod
    def _key(hostname: str, proxy: str | None) -> tuple[str, str | None]:
        return hostname.strip().lower(), proxy or None

    def get(self, hostname: str, proxy: str | None):
        record = self._items.get(self._key(hostname, proxy))
        if record is None:
            return None
        if record.created_at + self._ttl_seconds <= time.time():
            self._items.pop(self._key(hostname, proxy), None)
            return None
        return record.session

    def store(self, hostname: str, proxy: str | None, session) -> None:
        if len(self._items) >= self._max_sessions:
            oldest_key = min(self._items, key=lambda key: self._items[key].created_at)
            self._items.pop(oldest_key, None)
        self._items[self._key(hostname, proxy)] = SessionRecord(session=session, created_at=time.time())

    async def clear(self) -> None:
        items = list(self._items.values())
        self._items.clear()
        for record in items:
            close_fn = getattr(record.session, 'close', None)
            if callable(close_fn):
                result = close_fn()
                if asyncio.iscoroutine(result):
                    await result

    def clear_sync(self) -> None:
        asyncio.run(self.clear())

    def size(self) -> int:
        return len(self._items)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
python -m pytest tests\test_cache.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/models.py squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/cache.py squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/session_pool.py squirrel-cf-bypass/tests/test_cache.py
git commit -m "feat: add sidecar cache and session pool"
```

## Task 3: Add the service layer and the `/html` plus `/cache/clear` endpoints

**Files:**
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/solver.py`
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/service.py`
- Modify: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/routes.py`
- Modify: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/main.py`
- Create: `squirrel-cf-bypass/tests/test_html_route.py`

- [ ] **Step 1: Write the failing HTML-route tests**

```python
from fastapi.testclient import TestClient

from squirrel_cf_bypass.app.main import create_app
from squirrel_cf_bypass.app.core.models import HtmlResult


class FakeSolver:
    def __init__(self):
        self.calls = []

    async def fetch_html(self, url, proxy=None, cached_record=None, custom_headers=None):
        self.calls.append({
            'url': url,
            'proxy': proxy,
            'cached_record': cached_record,
            'custom_headers': custom_headers,
        })
        return HtmlResult(
            html='<html>ok</html>',
            final_url='https://javdb.com/?via=solver',
            status_code=200,
            cookies={'cf_clearance': 'demo'},
            user_agent='UA',
        )


def test_html_route_returns_solver_result_headers():
    solver = FakeSolver()
    client = TestClient(create_app(solver=solver))

    response = client.get('/html', params={'url': 'https://javdb.com'})

    assert response.status_code == 200
    assert response.text == '<html>ok</html>'
    assert response.headers['x-cf-bypasser-final-url'] == 'https://javdb.com/?via=solver'
    assert response.headers['x-cf-bypasser-user-agent'] == 'UA'
    assert solver.calls[0]['url'] == 'https://javdb.com'


def test_cache_clear_endpoint_empties_runtime_state():
    solver = FakeSolver()
    client = TestClient(create_app(solver=solver))

    response = client.post('/cache/clear')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
python -m pytest tests\test_html_route.py -q
```

Expected: FAIL because `create_app()` does not accept injected dependencies and the routes do not exist.

- [ ] **Step 3: Add the solver protocol, service layer, and HTML route**

`squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/solver.py`

```python
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
```

`squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/service.py`

```python
import time
from urllib.parse import urlparse

from squirrel_cf_bypass.app.core.cache import ClearanceCache
from squirrel_cf_bypass.app.core.models import ClearanceRecord
from squirrel_cf_bypass.app.core.session_pool import SessionPool


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

    async def fetch_html(self, url: str, proxy: str | None = None, custom_headers: dict[str, str] | None = None):
        hostname = str(urlparse(url).hostname or '').strip().lower()
        cached_record = self._cache.get(hostname, proxy)
        result = await self._solver.fetch_html(url, proxy=proxy, cached_record=cached_record, custom_headers=custom_headers)
        if result is None:
            return None
        record = ClearanceRecord(
            cookies=result.cookies,
            user_agent=result.user_agent,
            created_at=time.time(),
            expires_at=time.time() + self._ttl_seconds,
        )
        self._cache.set(hostname, proxy, record)
        return result
```

`squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/routes.py`

```python
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get('/health')
async def health(request: Request):
    return request.app.state.bypass_service.health_payload()


@router.post('/cache/clear')
async def clear_cache(request: Request):
    await request.app.state.bypass_service.clear_runtime_state()
    return {'status': 'ok'}


@router.get('/html')
async def html(request: Request, url: str):
    result = await request.app.state.bypass_service.fetch_html(url)
    if result is None:
        raise HTTPException(status_code=502, detail='Failed to bypass Cloudflare protection')
    return HTMLResponse(
        content=result.html,
        status_code=result.status_code,
        headers={
            'x-cf-bypasser-cookies': str(len(result.cookies)),
            'x-cf-bypasser-user-agent': result.user_agent,
            'x-cf-bypasser-final-url': result.final_url,
        },
    )
```

`squirrel-cf-bypass/src/squirrel_cf_bypass/app/main.py`

```python
from fastapi import FastAPI

from squirrel_cf_bypass.app.api.routes import router
from squirrel_cf_bypass.app.core.cache import ClearanceCache
from squirrel_cf_bypass.app.core.service import CloudflareBypassService
from squirrel_cf_bypass.app.core.session_pool import SessionPool


class _MissingSolver:
    ready = False

    async def fetch_html(self, *args, **kwargs):
        return None


def create_app(solver=None) -> FastAPI:
    app = FastAPI(title='squirrel-cf-bypass')
    app.state.bypass_service = CloudflareBypassService(
        solver=solver or _MissingSolver(),
        cache=ClearanceCache(ttl_seconds=900),
        session_pool=SessionPool(ttl_seconds=300, max_sessions=32),
        ttl_seconds=900,
    )
    app.include_router(router)
    return app
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
python -m pytest tests\test_health.py tests\test_html_route.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/solver.py squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/service.py squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/routes.py squirrel-cf-bypass/src/squirrel_cf_bypass/app/main.py squirrel-cf-bypass/tests/test_html_route.py
git commit -m "feat: add html and cache control endpoints"
```

## Task 4: Add mirrored request handling with cookie merge and stale-clearance invalidation

**Files:**
- Modify: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/service.py`
- Modify: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/routes.py`
- Create: `squirrel-cf-bypass/tests/test_mirror_route.py`

- [ ] **Step 1: Write the failing mirror-route tests**

```python
from fastapi.testclient import TestClient

from squirrel_cf_bypass.app.main import create_app
from squirrel_cf_bypass.app.core.models import MirrorResult


class FakeSolver:
    async def fetch_html(self, *args, **kwargs):
        return None


class FakeService:
    def __init__(self):
        self.calls = []

    def health_payload(self):
        return {
            'status': 'ok',
            'version': '0.1.0',
            'solver_ready': True,
            'cache_entries': 0,
            'session_entries': 0,
        }

    async def clear_runtime_state(self):
        return None

    async def fetch_html(self, url, proxy=None, custom_headers=None):
        return None

    async def mirror_request(self, method, path, query_string, headers, body):
        self.calls.append({
            'method': method,
            'path': path,
            'query_string': query_string,
            'headers': headers,
            'body': body,
        })
        return MirrorResult(
            status_code=206,
            headers={'content-type': 'video/mp2t'},
            body=b'chunk',
        )


def test_mirror_route_requires_x_hostname():
    app = create_app(solver=FakeSolver())
    client = TestClient(app)

    response = client.get('/segments/demo.ts')

    assert response.status_code == 400
    assert response.json() == {'detail': 'x-hostname header is required'}


def test_mirror_route_proxies_any_path():
    app = create_app(solver=FakeSolver())
    app.state.bypass_service = FakeService()
    client = TestClient(app)

    response = client.get('/segments/demo.ts?token=1', headers={'x-hostname': 'surrit.com'})

    assert response.status_code == 206
    assert response.content == b'chunk'
    assert app.state.bypass_service.calls == [{
        'method': 'GET',
        'path': '/segments/demo.ts',
        'query_string': 'token=1',
        'headers': {'host': 'testserver', 'x-hostname': 'surrit.com'},
        'body': b'',
    }]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
python -m pytest tests\test_mirror_route.py -q
```

Expected: FAIL because the catch-all route and `mirror_request()` are missing.

- [ ] **Step 3: Implement the mirrored request path**

Add this method to `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/service.py`:

```python
from urllib.parse import urljoin

from curl_cffi.requests import AsyncSession

from squirrel_cf_bypass.app.core.models import MirrorResult


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
        pairs = {}
        for item in existing_cookie.split(';'):
            if '=' in item:
                name, value = item.split('=', 1)
                pairs[name.strip()] = value.strip()
        pairs.update(cf_cookies)
        return '; '.join(f'{name}={value}' for name, value in pairs.items())

    async def mirror_request(self, method: str, path: str, query_string: str, headers: dict[str, str], body: bytes):
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

        session = self._session_pool.get(hostname, proxy)
        if session is None:
            proxies = {'http': proxy, 'https': proxy} if proxy else None
            session = AsyncSession(impersonate='firefox', proxies=proxies, timeout=30)
            self._session_pool.store(hostname, proxy, session)

        target_url = urljoin(f'https://{hostname}', path)
        if query_string:
            target_url = f'{target_url}?{query_string}'

        upstream_headers = self._strip_control_headers(headers)
        upstream_headers['user-agent'] = cached_record.user_agent
        upstream_headers['cookie'] = self._merge_cookie_header(upstream_headers.get('cookie', ''), cached_record.cookies)

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
```

Add this catch-all route to `squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/routes.py` after the specific routes:

```python
from fastapi.responses import Response


@router.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'])
async def mirror(request: Request, path: str):
    headers = {key.lower(): value for key, value in request.headers.items()}
    if 'x-hostname' not in headers:
        raise HTTPException(status_code=400, detail='x-hostname header is required')
    body = await request.body()
    result = await request.app.state.bypass_service.mirror_request(
        method=request.method,
        path='/' + path,
        query_string=request.url.query,
        headers=headers,
        body=body,
    )
    return Response(content=result.body, status_code=result.status_code, headers=result.headers)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
python -m pytest tests\test_mirror_route.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/service.py squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/routes.py squirrel-cf-bypass/tests/test_mirror_route.py
git commit -m "feat: add mirrored request handling"
```

## Task 5: Implement the browser-backed solver and route-level coverage

**Files:**
- Create: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/browser_solver.py`
- Create: `squirrel-cf-bypass/tests/test_browser_solver.py`
- Modify: `squirrel-cf-bypass/src/squirrel_cf_bypass/app/main.py`

- [ ] **Step 1: Write the failing solver helper tests**

```python
from squirrel_cf_bypass.app.core.browser_solver import BrowserSolver
from squirrel_cf_bypass.app.core.models import ClearanceRecord


class FakeContext:
    def __init__(self):
        self.calls = []

    async def add_cookies(self, cookies):
        self.calls.append(cookies)


def test_restore_cached_cookies_uses_target_url():
    solver = BrowserSolver()
    context = FakeContext()
    record = ClearanceRecord(
        cookies={'cf_clearance': 'demo', '__cf_bm': 'bm'},
        user_agent='UA',
        created_at=0.0,
        expires_at=1.0,
    )

    import asyncio
    asyncio.run(solver._restore_cached_cookies(context, 'https://javdb.com/video', record))

    assert context.calls == [[
        {'name': 'cf_clearance', 'value': 'demo', 'url': 'https://javdb.com/video'},
        {'name': '__cf_bm', 'value': 'bm', 'url': 'https://javdb.com/video'},
    ]]


def test_is_challenge_page_matches_known_titles():
    solver = BrowserSolver()

    assert solver._is_challenge_page('Just a moment...', '<html></html>') is True
    assert solver._is_challenge_page('Welcome', '<html>Please complete the captcha</html>') is True
    assert solver._is_challenge_page('Welcome', '<html>ready</html>') is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
python -m pytest tests\test_browser_solver.py -q
```

Expected: FAIL because `BrowserSolver` does not exist.

- [ ] **Step 3: Implement the browser solver**

`squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/browser_solver.py`

```python
import asyncio

from camoufox.async_api import AsyncCamoufox
from playwright_captcha import ClickSolver
from playwright_captcha import FrameworkType

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

    async def fetch_html(self, url: str, proxy: str | None = None, cached_record=None, custom_headers=None):
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
```

Update `squirrel-cf-bypass/src/squirrel_cf_bypass/app/main.py` to default to the real solver:

```python
from squirrel_cf_bypass.app.core.browser_solver import BrowserSolver


def create_app(solver=None) -> FastAPI:
    app = FastAPI(title='squirrel-cf-bypass')
    app.state.bypass_service = CloudflareBypassService(
        solver=solver or BrowserSolver(),
        cache=ClearanceCache(ttl_seconds=900),
        session_pool=SessionPool(ttl_seconds=300, max_sessions=32),
        ttl_seconds=900,
    )
    app.include_router(router)
    return app
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
python -m pytest tests\test_browser_solver.py tests\test_html_route.py tests\test_mirror_route.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/browser_solver.py squirrel-cf-bypass/src/squirrel_cf_bypass/app/main.py squirrel-cf-bypass/tests/test_browser_solver.py
git commit -m "feat: add browser-backed cloudflare solver"
```

## Task 6: Integrate the sidecar into backend config, health checking, and Docker Compose

**Files:**
- Create: `squirrel-cf-bypass/README.md`
- Create: `squirrel-cf-bypass/Dockerfile`
- Modify: `squirrel-backend/utils/cloudflare_bypass.py`
- Modify: `squirrel-backend/schedule/tasks/cloudflare_heartbeat_task.py`
- Create: `squirrel-backend/tests/utils/test_cloudflare_bypass.py`
- Create: `squirrel-backend/tests/schedule/test_cloudflare_heartbeat_task.py`
- Modify: `docker-compose.yaml`
- Modify: `env.example`
- Modify: `README.md`

- [ ] **Step 1: Write the failing backend client and heartbeat tests**

```python
import asyncio

from utils.cloudflare_bypass import CloudflareMirrorClient
from schedule.tasks.cloudflare_heartbeat_task import CloudflareHeartbeatTask


class _FakeAsyncClient:
    def __init__(self):
        self.calls = []

    def build_request(self, method, url, params=None, headers=None):
        self.calls.append({
            'method': method,
            'url': url,
            'params': params,
            'headers': headers,
        })
        return object()

    async def send(self, request, stream=False, follow_redirects=True):
        self.calls.append({
            'stream': stream,
            'follow_redirects': follow_redirects,
        })
        return object()


def test_health_uses_sidecar_health_endpoint():
    client = CloudflareMirrorClient('http://localhost:8001')
    fake_http_client = _FakeAsyncClient()
    client._client = fake_http_client

    asyncio.run(client.health())

    assert fake_http_client.calls[0]['method'] == 'GET'
    assert fake_http_client.calls[0]['url'] == 'http://localhost:8001/health'


def test_heartbeat_checks_health_instead_of_clearing_cache(monkeypatch):
    calls = []

    class _BypassClient:
        async def health(self):
            calls.append('health')

    monkeypatch.setattr('schedule.tasks.cloudflare_heartbeat_task.get_default_client', lambda: _BypassClient())

    CloudflareHeartbeatTask.run()

    assert calls == ['health']
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\utils\test_cloudflare_bypass.py tests\schedule\test_cloudflare_heartbeat_task.py -q
```

Expected: FAIL because `CloudflareMirrorClient.health()` does not exist and heartbeat still calls `clear_cache()`.

- [ ] **Step 3: Update the backend client and heartbeat behavior**

In `squirrel-backend/utils/cloudflare_bypass.py`, add:

```python
    async def health(self):
        return await self._send(
            'GET',
            f'{self.service_url}/health',
        )
```

In `squirrel-backend/schedule/tasks/cloudflare_heartbeat_task.py`, replace:

```python
            asyncio.run(client.clear_cache())
            logger.info("CloudflareHeartbeatTask started")
```

With:

```python
            asyncio.run(client.health())
            logger.info('CloudflareHeartbeatTask health check passed')
```

- [ ] **Step 4: Add sidecar Docker packaging and compose wiring**

`squirrel-cf-bypass/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8001

CMD ["uvicorn", "squirrel_cf_bypass.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

Add this service to `docker-compose.yaml`:

```yaml
  squirrel-cf-bypass:
    build:
      context: ./squirrel-cf-bypass
    container_name: squirrel-cf-bypass
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
    ports:
      - "8001:8001"
    networks:
      - squirrel-network
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health', timeout=5).read()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
```

Update `env.example`:

```dotenv
CLOUDFLARE_BYPASS_SERVICE_URL=http://squirrel-cf-bypass:8001
```

- [ ] **Step 5: Document the sidecar and repo startup flow**

`squirrel-cf-bypass/README.md`

````markdown
# squirrel-cf-bypass

Repo-local Cloudflare bypass sidecar for Squirrel.

## Run locally

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
pip install -e .[dev]
uvicorn squirrel_cf_bypass.app.main:app --host 0.0.0.0 --port 8001
```

## Endpoints

- `GET /health`
- `POST /cache/clear`
- `GET /html?url=...`
- `ANY /{path:path}` with `x-hostname`
````

In the repo `README.md`, add a short deployment note under the compose section:

```markdown
- `squirrel-cf-bypass` is now part of the local stack and serves the backend's Cloudflare bypass needs.
- `CLOUDFLARE_BYPASS_SERVICE_URL` should point to `http://squirrel-cf-bypass:8001` in containerized deployments.
```

- [ ] **Step 6: Run verification**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\utils\test_cloudflare_bypass.py tests\schedule\test_cloudflare_heartbeat_task.py tests\routes\test_connectivity_routes.py tests\core\test_streaming_proxy.py -q

Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
python -m pytest tests\test_health.py tests\test_cache.py tests\test_html_route.py tests\test_mirror_route.py tests\test_browser_solver.py -q

Set-Location 'D:\Code\init\squirrel'
docker compose config
```

Expected:

- backend bypass-related tests PASS
- sidecar test suite PASS
- `docker compose config` succeeds with the new `squirrel-cf-bypass` service included

- [ ] **Step 7: Commit**

```powershell
git add squirrel-cf-bypass/README.md squirrel-cf-bypass/Dockerfile squirrel-backend/utils/cloudflare_bypass.py squirrel-backend/schedule/tasks/cloudflare_heartbeat_task.py squirrel-backend/tests/utils/test_cloudflare_bypass.py squirrel-backend/tests/schedule/test_cloudflare_heartbeat_task.py docker-compose.yaml env.example README.md
git commit -m "feat: wire repo-local cloudflare bypass sidecar"
```

## Self-Review

### Spec coverage

- Separate-process sidecar: covered by Tasks 1 and 6.
- Repo-local implementation under `squirrel-cf-bypass`: covered by Tasks 1 through 5.
- `health`, `cache/clear`, `html`, and mirrored request API: covered by Tasks 1, 3, and 4.
- Clearance cache and session reuse: covered by Task 2 and exercised again in Task 4.
- Browser-backed solver kept out of backend: covered by Task 5 and Task 6.
- Backend remains client-only and keeps `CLOUDFLARE_BYPASS_SERVICE_URL`: covered by Task 6.
- Remove routine cache clearing in favor of health verification: covered by Task 6.

### Placeholder scan

- No `TODO`, `TBD`, or “similar to previous task” placeholders remain.
- Every code-changing step includes concrete code.
- Every validation step includes exact commands and expected outcomes.

### Type consistency

- `ClearanceRecord`, `HtmlResult`, and `MirrorResult` are defined once in Task 2 and reused consistently in Tasks 3 through 5.
- `CloudflareBypassService` owns `fetch_html()` and `mirror_request()` in Tasks 3 and 4.
- `BrowserSolver.fetch_html()` matches the `Solver` protocol introduced in Task 3.
