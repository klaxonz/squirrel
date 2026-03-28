# Plugin Refactor Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Finish the plugin refactor by removing the remaining in-process compatibility artifacts while keeping Runtime V2 behavior covered by tests.

**Architecture:** Treat Runtime V2 as the only supported host path. First add or tighten regression coverage around gateway-driven runtime calls, then remove plugin-package import side effects, then delete backend-only compatibility code, and finally narrow the SDK legacy registry to passive compatibility plus updated docs.

**Tech Stack:** Python 3.11, FastAPI, pytest, Pipenv, Runtime V2 plugin packages, backend plugin manager/gateway

---

> 当前仓库状态：Runtime V2 主链路已落地并通过 `tests/plugins/*`；剩余工作集中在 `plugins_ext`、插件包 `__init__.py` 兼容副作用、以及 SDK legacy registry 的收口。

### Task 1: Lock Runtime V2 Regression Coverage Before Deleting Compat Code

**Files:**
- Create: `squirrel-backend/tests/services/test_site_login_status_service.py`
- Modify: `squirrel-backend/tests/services/test_video_service.py`
- Modify: `squirrel-backend/tests/services/test_subscription_service.py`
- Modify: `squirrel-backend/tests/services/test_subscription_update_strategy.py`
- Modify: `squirrel-backend/tests/core/test_extractor_factory.py`

**Step 1: Write the failing login-status service test**

Add a new test file that covers:

- `get_supported_sites()` reading from `PluginManager.get_snapshot().registrations`
- `test_site_login_status()` returning the fallback payload when no route exists
- `test_site_login_status()` returning normalized runtime payload when the gateway returns `{ logged_in, message, extra }`

Minimal test shape:

```python
def test_test_site_login_status_returns_runtime_payload(monkeypatch):
    class FakeGateway:
        def resolve_route(self, capability, site_name=None, domain=None):
            return object()

        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            return SimpleNamespace(ok=True, error=None, data={'logged_in': True, 'message': 'ok', 'extra': {}})

    monkeypatch.setattr(service, 'get_plugin_manager', lambda: SimpleNamespace(
        gateway=FakeGateway(),
        get_snapshot=lambda: SimpleNamespace(registrations=[]),
    ))

    payload = service.test_site_login_status('youtube')
    assert payload['supported'] is True
    assert payload['logged_in'] is True
```

**Step 2: Extend gateway-focused tests for existing V2 flows**

In the existing service tests, make the fake gateway assertions explicit:

- `test_video_service.py` must assert `resolve_playback`
- `test_subscription_service.py` must assert `import_subscriptions` and `resolve_subscription`
- `test_subscription_update_strategy.py` must assert `sync_subscription`
- `test_extractor_factory.py` must assert `extract_video`

The point is to freeze the runtime capability names and payload shape before removing compatibility code.

**Step 3: Run the targeted backend tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\services\test_site_login_status_service.py tests\services\test_video_service.py tests\services\test_subscription_service.py tests\services\test_subscription_update_strategy.py tests\core\test_extractor_factory.py -q
```

Expected: all tests pass.

**Step 4: Commit**

```powershell
git add squirrel-backend/tests/services/test_site_login_status_service.py squirrel-backend/tests/services/test_video_service.py squirrel-backend/tests/services/test_subscription_service.py squirrel-backend/tests/services/test_subscription_update_strategy.py squirrel-backend/tests/core/test_extractor_factory.py
git commit -m "test: lock runtime v2 plugin gateway coverage"
```

### Task 2: Remove Plugin Package Import Side Effects

**Files:**
- Modify: `squirrel-plugins/youtube/src/squirrel_youtube/__init__.py`
- Modify: `squirrel-plugins/javdb/src/squirrel_javdb/__init__.py`
- Modify: `squirrel-plugins/pornhub/src/squirrel_pornhub/__init__.py`
- Modify: `squirrel-plugins/bilibili/src/squirrel_bilibili/__init__.py`

**Step 1: Write the failing import smoke test**

Add or extend a backend-side smoke test that imports each workspace plugin package and verifies the import surface is minimal:

- exposes `PLUGIN_NAME`
- exposes `PLUGIN_VERSION`
- exposes `PLUGIN_DESCRIPTION`
- exposes `get_plugin_runtime`
- does not require `plugins.registry`

Recommended location:

`squirrel-backend/tests/plugins/test_workspace_plugin_imports.py`

Minimal shape:

```python
@pytest.mark.parametrize('module_name', [
    'squirrel_bilibili',
    'squirrel_javdb',
    'squirrel_pornhub',
    'squirrel_youtube',
])
def test_workspace_plugin_imports_are_runtime_only(module_name):
    module = importlib.import_module(module_name)
    assert callable(module.get_plugin_runtime)
```

**Step 2: Make each plugin `__init__.py` runtime-only**

Align all four packages with the existing bilibili style:

- import only `get_plugin_runtime`
- keep metadata constants
- export a small `__all__`
- remove eager imports of handler/proxy/subscription modules
- remove `register_plugin` compatibility blocks

Do not change runtime handlers in `runtime.py` in this task.

**Step 3: Run import and plugin behavior checks**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\plugins\test_workspace_plugin_imports.py tests\plugins_ext\test_javdb_proxy.py -q
```

Expected:

- imports pass
- proxy behavior test still passes
- warning summary no longer includes `LegacyRegistryApiWarning`

**Step 4: Commit**

```powershell
git add squirrel-plugins/youtube/src/squirrel_youtube/__init__.py squirrel-plugins/javdb/src/squirrel_javdb/__init__.py squirrel-plugins/pornhub/src/squirrel_pornhub/__init__.py squirrel-plugins/bilibili/src/squirrel_bilibili/__init__.py squirrel-backend/tests/plugins/test_workspace_plugin_imports.py
git commit -m "refactor: remove plugin package registry side effects"
```

### Task 3: Delete Backend Legacy Registry Coupling From ExtractorFactory

**Files:**
- Modify: `squirrel-backend/core/extraction/factory.py`
- Modify: `squirrel-backend/tests/core/test_extractor_factory.py`

**Step 1: Write the failing factory cleanup test**

Add a focused assertion that `get_extractor_factory()` works without calling the SDK extractor registry helper. The easiest way is to monkeypatch the local helper to raise and then remove the helper entirely.

Minimal test shape:

```python
def test_get_extractor_factory_does_not_touch_legacy_sdk_registry(monkeypatch):
    monkeypatch.setattr(factory_module, 'get_extractor_registry', lambda: (_ for _ in ()).throw(AssertionError('legacy registry should not be used')))
    factory_module.reset_factory()
    factory = factory_module.get_extractor_factory()
    assert factory is not None
```

Then remove the helper and update the test to assert the simplified constructor path.

**Step 2: Simplify `ExtractorFactory`**

In `factory.py`:

- remove the `registry` constructor argument
- remove `get_extractor_registry()`
- stop importing the SDK legacy registry from `crawl`
- keep `register()` as a no-op compatibility sink only if other code still imports it

The final class should rely only on `PluginManager` and `SiteCatalog`.

**Step 3: Run the focused tests**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\core\test_extractor_factory.py tests\services\test_video_service.py -q
```

Expected: all tests pass with no new warnings.

**Step 4: Commit**

```powershell
git add squirrel-backend/core/extraction/factory.py squirrel-backend/tests/core/test_extractor_factory.py
git commit -m "refactor: remove extractor factory legacy registry shim"
```

### Task 4: Retire `plugins_ext` After Coverage Is In Place

**Files:**
- Delete: `squirrel-backend/plugins_ext/bilibili`
- Delete: `squirrel-backend/plugins_ext/javdb`
- Delete: `squirrel-backend/plugins_ext/pornhub`
- Delete: `squirrel-backend/plugins_ext/youtube`
- Modify: `squirrel-backend/tests/plugins_ext/test_javdb_proxy.py`
- Move to: `squirrel-backend/tests/plugins/test_javdb_proxy_runtime.py`

**Step 1: Write the failing relocation change**

Move the JavDB proxy behavior test out of `tests/plugins_ext` and rename it to make the ownership clear: it validates workspace plugin runtime code, not backend compat code.

Before deleting `plugins_ext`, keep the exact assertions:

- handler builds proxy URL with upstream referer
- proxy builds upstream headers from referer
- proxy rewrites m3u8 entries with referer

**Step 2: Delete the backend compat tree**

Delete `squirrel-backend/plugins_ext/*` only after:

- no runtime path imports it
- the relocated test passes
- `rg "plugins_ext" squirrel-backend squirrel-plugin-runner squirrel-sdk squirrel-plugins` returns only documentation references you intentionally keep or zero results

**Step 3: Run the cleanup verification**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel'
rg -n "plugins_ext" squirrel-backend squirrel-plugin-runner squirrel-sdk squirrel-plugins

Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\plugins\test_javdb_proxy_runtime.py tests\plugins\test_installer.py tests\plugins\test_supervisor.py tests\plugins\test_runner_network_policy.py -q
```

Expected:

- ripgrep finds no runtime code references
- relocated proxy test passes
- Runtime V2 plugin tests still pass

**Step 4: Commit**

```powershell
git add squirrel-backend/tests/plugins/test_javdb_proxy_runtime.py squirrel-backend/tests/plugins squirrel-backend/plugins_ext
git commit -m "refactor: remove backend plugin compat tree"
```

### Task 5: Narrow SDK Legacy Registry To Passive Compatibility Only

**Files:**
- Modify: `squirrel-sdk/src/crawl/registry.py`
- Modify: `squirrel-sdk/src/crawl/registries.py`
- Modify: `squirrel-sdk/src/crawl/__init__.py`
- Modify: `squirrel-sdk/README.md`
- Modify: `squirrel-backend/README.md`
- Modify: `squirrel-plugins/README.md`

**Step 1: Write the failing warning test**

Add a small SDK or backend test that proves the supported Runtime V2 path does not emit `LegacyRegistryApiWarning`.

Recommended approach:

- run one plugin import smoke test
- run one gateway-backed extraction test
- fail the test if `LegacyRegistryApiWarning` is observed

If adding a code test is too awkward, enforce it in verification with `pytest -W error`.

**Step 2: Reduce the legacy API surface**

In the SDK:

- keep legacy helpers only for explicit compatibility
- remove them from primary doc examples
- make their docstrings clearly state “legacy compatibility only”
- avoid re-export emphasis from `crawl/__init__.py` if V2 exports are meant to be primary

Do not break existing callers in this task; the goal is demotion, not a hard removal.

**Step 3: Update docs to match the real end state**

Update the READMEs so they all say the same thing:

- Runtime V2 is the primary and supported path
- `plugins_ext` is gone
- workspace plugins load from `squirrel-plugins/*/plugin-runtime.json`
- legacy registry APIs exist only for compatibility and migration

**Step 4: Run final verification**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
pipenv run pytest tests\plugins tests\services\test_site_login_status_service.py tests\services\test_video_service.py tests\services\test_subscription_service.py tests\services\test_subscription_update_strategy.py tests\core\test_extractor_factory.py -W error -q

Set-Location 'D:\Code\init\squirrel\squirrel-sdk'
python -m compileall src
```

Expected:

- targeted backend tests pass
- no deprecation or legacy-registry warnings escape the supported V2 path
- SDK compile succeeds

**Step 5: Commit**

```powershell
git add squirrel-sdk/src/crawl/registry.py squirrel-sdk/src/crawl/registries.py squirrel-sdk/src/crawl/__init__.py squirrel-sdk/README.md squirrel-backend/README.md squirrel-plugins/README.md
git commit -m "refactor: finalize plugin refactor cleanup"
```
