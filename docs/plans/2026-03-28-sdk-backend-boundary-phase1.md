# SDK Backend Boundary Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move backend-owned runtime injection responsibilities out of `squirrel-sdk` and into `squirrel-backend` without changing Runtime V2 plugin behavior.

**Architecture:** Keep `squirrel-sdk` as the plugin-facing contract and helper package for now, but stop using it as the backend's mutable runtime container. In this phase, backend startup and worker bootstrap will configure backend-local runtime state for Cloudflare bypass, site config projection, rate-limit toggles, and cookie resolution, while plugin-facing DTOs and Runtime V2 contracts remain unchanged.

**Tech Stack:** Python 3.11, FastAPI, pytest, requests/httpx, Runtime V2 plugin packages

---

### Task 1: Add backend-owned runtime support modules

**Files:**
- Create: `squirrel-backend/utils/runtime_http.py`
- Create: `squirrel-backend/utils/runtime_site_config.py`
- Create: `squirrel-backend/tests/utils/test_runtime_http.py`
- Create: `squirrel-backend/tests/utils/test_runtime_site_config.py`

**Step 1: Write the failing Cloudflare bypass state tests**

```python
from utils import runtime_http


class DummyClient:
    pass


def test_set_and_get_cloudflare_bypass_client():
    client = DummyClient()

    runtime_http.set_cloudflare_bypass_client(client)

    assert runtime_http.get_cloudflare_bypass_client() is client


def test_get_cloudflare_bypass_client_defaults_to_none():
    runtime_http.reset_runtime_http_state()

    assert runtime_http.get_cloudflare_bypass_client() is None
```

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\utils\test_runtime_http.py -q
```

Expected: FAIL because `utils.runtime_http` does not exist.

**Step 3: Write the minimal runtime HTTP state module**

```python
_cloudflare_bypass_client = None


def set_cloudflare_bypass_client(client: object | None) -> None:
    global _cloudflare_bypass_client
    _cloudflare_bypass_client = client


def get_cloudflare_bypass_client() -> object | None:
    return _cloudflare_bypass_client


def reset_runtime_http_state() -> None:
    set_cloudflare_bypass_client(None)
```

**Step 4: Write the failing site config state tests**

```python
from utils import runtime_site_config


def test_replace_site_configs_and_read_nested_sections():
    runtime_site_config.reset_runtime_site_state()
    runtime_site_config.set_site_configs({
        'youtube': {
            'http': {'headers': {'User-Agent': 'UA'}},
            'proxy': {'enabled': True},
            'rate_limit': {'enabled': False},
        }
    })

    assert runtime_site_config.get_http_headers('youtube', {'Accept': 'json'}) == {
        'Accept': 'json',
        'User-Agent': 'UA',
    }
    assert runtime_site_config.get_proxy_config('youtube')['enabled'] is True
    assert runtime_site_config.get_rate_limit_config('youtube')['enabled'] is False
```

**Step 5: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\utils\test_runtime_site_config.py -q
```

Expected: FAIL because `utils.runtime_site_config` does not exist.

**Step 6: Write the minimal runtime site config module**

```python
_site_configs: dict[str, dict] = {}


def set_site_configs(configs: dict | None) -> None:
    _site_configs.clear()
    for slug, cfg in (configs or {}).items():
        _site_configs[str(slug).strip().lower()] = dict(cfg or {})


def get_site_config(slug: str | None) -> dict:
    if not slug:
        return {}
    return _site_configs.get(str(slug).strip().lower(), {})


def get_http_headers(slug: str, base: dict[str, str] | None = None) -> dict[str, str]:
    headers = dict(base or {})
    headers.update(get_site_config(slug).get('http', {}).get('headers', {}))
    return headers
```

Also implement:

- `get_login_config()`
- `get_login_headers()`
- `get_proxy_config()`
- `get_rate_limit_config()`
- `reset_runtime_site_state()`

**Step 7: Run the tests to verify they pass**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\utils\test_runtime_http.py tests\utils\test_runtime_site_config.py -q
```

Expected: PASS

**Step 8: Commit**

```powershell
git add squirrel-backend/utils/runtime_http.py squirrel-backend/utils/runtime_site_config.py squirrel-backend/tests/utils/test_runtime_http.py squirrel-backend/tests/utils/test_runtime_site_config.py
git commit -m "refactor: add backend-owned runtime support state"
```

### Task 2: Move backend startup/bootstrap off SDK mutable runtime APIs

**Files:**
- Modify: `squirrel-backend/main.py`
- Modify: `squirrel-backend/processes/service_runtime.py`
- Modify: `squirrel-backend/core/site_config_manager.py`
- Create: `squirrel-backend/tests/core/test_site_config_manager.py`
- Create: `squirrel-backend/tests/test_app_runtime_bootstrap.py`

**Step 1: Write the failing site config manager test**

```python
from core import site_config_manager
from utils import runtime_site_config


def test_apply_site_config_overrides_updates_backend_runtime_state(monkeypatch):
    monkeypatch.setattr(
        site_config_manager,
        'get_effective_site_catalog',
        lambda catalog=None: {
            'youtube': {
                'domains': ['youtube.com'],
                'http': {'headers': {'User-Agent': 'UA'}},
                'rate_limit': {'enabled': False},
            }
        },
    )

    runtime_site_config.reset_runtime_site_state()
    site_config_manager.apply_site_config_overrides()

    assert runtime_site_config.get_http_headers('youtube') == {'User-Agent': 'UA'}
    assert runtime_site_config.get_rate_limit_config('youtube')['enabled'] is False
```

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\core\test_site_config_manager.py -q
```

Expected: FAIL because `apply_site_config_overrides()` still writes into `crawl.config`.

**Step 3: Update `site_config_manager.py` to write only backend-owned state**

Replace:

```python
from crawl import configure_rate_limit, configure_rate_limit_enabled, set_site_configs
```

With:

```python
from utils.runtime_site_config import set_site_configs
from utils.rate_limiter import rate_limiter as backend_rate_limiter
```

Then remove SDK rate-limit mutation calls and keep only backend rate limiter updates:

```python
backend_rate_limiter.set_domain_enabled(domain, rate_limit_enabled)
if rate_limit_enabled and min_value is not None and max_value is not None:
    backend_rate_limiter.add_rate_limit(domain, min_value, max_value)
```

**Step 4: Write the failing runtime bootstrap test**

```python
from types import SimpleNamespace

import main as app_main
from utils import runtime_http


def test_lifespan_configures_backend_runtime_http_state(monkeypatch):
    runtime_http.reset_runtime_http_state()
    dummy_client = object()

    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: dummy_client)
    monkeypatch.setattr(app_main, 'bootstrap_plugin_runtime', lambda: None)

    async def run_once():
        async with app_main.lifespan(SimpleNamespace()):
            assert runtime_http.get_cloudflare_bypass_client() is dummy_client
```

Do the same for `processes/service_runtime.py` by asserting `bootstrap_runtime()` sets backend runtime HTTP state.

**Step 5: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\test_app_runtime_bootstrap.py -q
```

Expected: FAIL because startup still imports `configure_cloudflare_bypass_client` from `crawl`.

**Step 6: Update startup/bootstrap imports**

In `main.py` and `processes/service_runtime.py`, replace:

```python
from crawl import configure_cloudflare_bypass_client
from utils.cloudflare_bypass import get_default_client
configure_cloudflare_bypass_client(get_default_client())
```

With:

```python
from utils.cloudflare_bypass import get_default_client
from utils.runtime_http import set_cloudflare_bypass_client
set_cloudflare_bypass_client(get_default_client())
```

**Step 7: Run the focused tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\core\test_site_config_manager.py tests\test_app_runtime_bootstrap.py -q
```

Expected: PASS

**Step 8: Commit**

```powershell
git add squirrel-backend/main.py squirrel-backend/processes/service_runtime.py squirrel-backend/core/site_config_manager.py squirrel-backend/tests/core/test_site_config_manager.py squirrel-backend/tests/test_app_runtime_bootstrap.py
git commit -m "refactor: move backend runtime injection off sdk globals"
```

### Task 3: Move backend cookie resolver ownership out of SDK injection

**Files:**
- Modify: `squirrel-backend/utils/cookie.py`
- Modify: `squirrel-sdk/src/crawl/utils.py`
- Create: `squirrel-backend/tests/utils/test_cookie.py`

**Step 1: Write the failing backend cookie wrapper test**

```python
from utils import cookie


def test_filter_cookies_to_query_string_reads_matching_domain_cookies(tmp_path, monkeypatch):
    cookie_file = tmp_path / 'cookies.txt'
    cookie_file.write_text(
        '# Netscape HTTP Cookie File\n'
        '.youtube.com\tTRUE\t/\tFALSE\t2147483647\tSID\tabc123\n',
        encoding='utf-8',
    )

    monkeypatch.setattr(cookie, 'resolve_cookie_file_for_url', lambda url: str(cookie_file))

    assert cookie.filter_cookies_to_query_string('https://m.youtube.com/watch?v=1') == 'SID=abc123'
```

**Step 2: Run test to verify it fails**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\utils\test_cookie.py -q
```

Expected: FAIL because `utils.cookie` still depends on SDK-global resolver injection.

**Step 3: Refactor `utils/cookie.py` to own cookie resolution**

Remove:

```python
from crawl import (
    filter_cookies_to_query_string as sdk_filter_cookies_to_query_string,
    configure_cookie_file_resolver,
)
configure_cookie_file_resolver(resolve_cookie_file_for_url)
```

Replace with backend-local helpers:

```python
def _read_cookie_file_as_query_string(path: str | None) -> str:
    if not path:
        return ''
    ...


def filter_cookies_to_query_string(target_url: str) -> str:
    cookie_file = resolve_cookie_file_for_url(target_url)
    return _read_cookie_file_as_query_string(cookie_file)
```

Use the existing Netscape parsing logic already present in the SDK as reference, but keep backend ownership inside `utils/cookie.py`.

**Step 4: Narrow SDK utils to explicit helper behavior only**

In `squirrel-sdk/src/crawl/utils.py`:

- keep `resolve_cookie_file_path()` and `filter_cookies_to_query_string()`
- mark `configure_cookie_file_resolver()` as legacy compatibility only in the docstring
- do not add new backend callers

This task is a demotion, not a removal.

**Step 5: Run the focused tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\utils\test_cookie.py tests\plugins\test_javdb_proxy_runtime.py -q
```

Expected: PASS

**Step 6: Commit**

```powershell
git add squirrel-backend/utils/cookie.py squirrel-backend/tests/utils/test_cookie.py squirrel-sdk/src/crawl/utils.py
git commit -m "refactor: move backend cookie resolution ownership local"
```

### Task 4: Verify backend no longer treats SDK as mutable host runtime state

**Files:**
- Modify: `squirrel-sdk/README.md`
- Modify: `squirrel-backend/README.md`
- Modify: `squirrel-plugins/README.md`

**Step 1: Add a regression grep check**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel'
rg -n "configure_cloudflare_bypass_client|set_site_configs|configure_rate_limit|configure_rate_limit_enabled|configure_cookie_file_resolver" squirrel-backend
```

Expected after implementation:

- no backend runtime code uses `crawl.configure_cloudflare_bypass_client`
- no backend runtime code uses `crawl.set_site_configs`
- no backend runtime code uses `crawl.configure_rate_limit`
- no backend runtime code uses `crawl.configure_rate_limit_enabled`

One remaining backend reference to `configure_cookie_file_resolver` is acceptable only during the Task 3 transition; expected final state is zero runtime references.

**Step 2: Run targeted backend regression tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\plugins tests\services\test_site_login_status_service.py tests\services\test_video_service.py tests\services\test_subscription_service.py tests\services\test_subscription_update_strategy.py tests\core\test_extractor_factory.py tests\core\test_site_config_manager.py tests\utils\test_runtime_http.py tests\utils\test_runtime_site_config.py tests\utils\test_cookie.py -q
```

Expected: PASS

**Step 3: Update docs**

Update the READMEs so they all say the same thing:

- `squirrel-sdk` is the plugin-facing contract and helper package
- backend owns runtime bootstrap state and policy injection
- plugin packages may keep using SDK helpers, but backend must not depend on SDK global mutable state

**Step 4: Run final verification**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-sdk'
python -m compileall src

Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\plugins tests\core\test_site_config_manager.py tests\utils\test_runtime_http.py tests\utils\test_runtime_site_config.py tests\utils\test_cookie.py -q
```

Expected:

- SDK compile succeeds
- backend targeted tests pass

**Step 5: Commit**

```powershell
git add squirrel-sdk/README.md squirrel-backend/README.md squirrel-plugins/README.md
git commit -m "docs: clarify sdk and backend runtime ownership"
```
