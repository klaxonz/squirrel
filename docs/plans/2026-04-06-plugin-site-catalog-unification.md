# Plugin Site Catalog Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove backend hardcoded site defaults and make plugin-provided site definitions the only source of truth, with `config/sites.json` storing override-only data.

**Architecture:** Backend builds a plugin base catalog from plugin manifests, loads a separate override catalog from `config/sites.json`, and exposes a single effective catalog merged at read time. Frontend reads the effective catalog but saves only explicit overrides, and the site editor stops editing plugin-owned fields such as `domains`.

**Tech Stack:** FastAPI, Python dataclasses, Vue 3 Composition API, existing plugin runtime manifests, pytest

---

### Task 1: Build Plugin Base Catalog and Remove Hardcoded Defaults

**Files:**
- Modify: `squirrel-backend/utils/site_catalog.py`
- Modify: `squirrel-backend/core/site_config_manager.py`
- Delete: `squirrel-backend/core/site_config_defaults.py`
- Test: `squirrel-backend/tests/plugins/test_site_catalog_runtime_models.py`
- Test: `squirrel-backend/tests/core/test_site_config_manager.py`

- [ ] **Step 1: Write the failing tests for plugin-owned defaults**

Add a runtime manifest test that proves plugin metadata becomes default site config:

```python
def test_site_catalog_builds_site_defaults_from_manifest_metadata(monkeypatch):
    manifest = PluginManifest(
        plugin_id='youtube',
        version='0.1.0',
        display_name='YouTube',
        capabilities=[PluginCapability(name='extract_video')],
        sites=[
            PluginSiteManifest(
                site_name='youtube',
                domains=['youtube.com', 'youtu.be'],
                test_url='https://www.youtube.com',
                features=['extract_video'],
                metadata={
                    'label': 'YouTube',
                    'aliases': ['yt'],
                    'http': {'headers': {'User-Agent': 'UA'}},
                    'rate_limit': {'enabled': True, 'min_interval': 2.0, 'max_interval': 5.0},
                    'metadata': {'requires_cookies': False},
                },
            )
        ],
    )
    monkeypatch.setattr(
        'utils.site_catalog.get_plugin_manager',
        lambda: SimpleNamespace(
            get_snapshot=lambda: SimpleNamespace(
                records=[SimpleNamespace(enabled=True, manifest=manifest.to_dict())]
            )
        ),
    )

    catalog = SiteCatalog.build_plugin_site_catalog()

    assert catalog['youtube']['label'] == 'YouTube'
    assert catalog['youtube']['aliases'] == ['yt']
    assert catalog['youtube']['http']['headers']['User-Agent'] == 'UA'
    assert catalog['youtube']['domains'] == ['youtube.com', 'youtu.be']
```

Replace the current hardcoded-defaults test in `test_site_config_manager.py` with a merge test:

```python
def test_get_effective_site_catalog_merges_plugin_defaults_with_overrides(monkeypatch):
    monkeypatch.setattr(
        site_config_manager,
        'build_plugin_site_catalog',
        lambda: {
            'youporn': {
                'label': 'YouPorn',
                'domains': ['youporn.com'],
                'enabled': True,
                'proxy': {'read_timeout': 180.0},
            }
        },
    )

    catalog = site_config_manager.get_effective_site_catalog({
        'youporn': {
            'enabled': False,
            'proxy': {'read_timeout': 240.0},
        }
    })

    assert catalog['youporn']['enabled'] is False
    assert catalog['youporn']['proxy']['read_timeout'] == 240.0
    assert catalog['youporn']['domains'] == ['youporn.com']
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd squirrel-backend
pipenv run pytest tests/plugins/test_site_catalog_runtime_models.py tests/core/test_site_config_manager.py -q
```

Expected:

```text
FAILED tests/plugins/test_site_catalog_runtime_models.py::test_site_catalog_builds_site_defaults_from_manifest_metadata
FAILED tests/core/test_site_config_manager.py::test_get_effective_site_catalog_merges_plugin_defaults_with_overrides
```

- [ ] **Step 3: Implement plugin base catalog and effective merge**

In `squirrel-backend/utils/site_catalog.py`, add explicit catalog loaders and stop using `get_catalog()` as the semantic source:

```python
class SiteCatalog:
    @classmethod
    def build_plugin_site_catalog(cls) -> Dict[str, dict]:
        catalog: Dict[str, dict] = {}
        snapshot = get_plugin_manager().get_snapshot()
        for record in snapshot.records:
            manifest = PluginManifest.from_dict(record.manifest)
            for site in manifest.sites:
                slug = site.site_name.strip().lower()
                defaults = dict(site.metadata or {})
                entry = catalog.setdefault(slug, {
                    'label': defaults.get('label') or site.site_name,
                    'domains': [],
                    'aliases': list(defaults.get('aliases') or []),
                    'enabled': record.enabled,
                    'features': [],
                })
                entry['enabled'] = bool(defaults.get('enabled', entry.get('enabled', True))) and record.enabled
                entry['label'] = defaults.get('label') or entry.get('label') or site.site_name
                if site.test_url:
                    entry['test_url'] = site.test_url
                for key in ('http', 'proxy', 'login', 'rate_limit', 'cookie', 'metadata', 'icon_url'):
                    if defaults.get(key) is not None:
                        entry[key] = defaults[key]
                for domain in site.domains:
                    normalized = str(domain).strip().lower()
                    if normalized and normalized not in entry['domains']:
                        entry['domains'].append(normalized)
                for feature in site.features:
                    if feature not in entry['features']:
                        entry['features'].append(feature)
        return catalog
```

In `squirrel-backend/core/site_config_manager.py`, remove `SITE_CONFIG_DEFAULTS` and merge against plugin defaults:

```python
from utils.site_catalog import SiteCatalog

def build_plugin_site_catalog() -> Dict[str, dict]:
    return SiteCatalog.build_plugin_site_catalog()

def get_effective_site_catalog(stored_catalog: Dict[str, dict] | None = None) -> Dict[str, dict]:
    overrides = stored_catalog if stored_catalog is not None else SiteCatalog.load_override_catalog()
    effective = {slug: deepcopy(info) for slug, info in build_plugin_site_catalog().items()}
    for slug, override in (overrides or {}).items():
        if slug not in effective:
            continue
        effective[slug] = _deep_merge(effective[slug], override)
    return effective
```

Delete `squirrel-backend/core/site_config_defaults.py` and remove imports that depend on it.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd squirrel-backend
pipenv run pytest tests/plugins/test_site_catalog_runtime_models.py tests/core/test_site_config_manager.py -q
```

Expected:

```text
....                                                                     [100%]
```

- [ ] **Step 5: Commit**

```bash
git add squirrel-backend/utils/site_catalog.py squirrel-backend/core/site_config_manager.py squirrel-backend/tests/plugins/test_site_catalog_runtime_models.py squirrel-backend/tests/core/test_site_config_manager.py
git rm squirrel-backend/core/site_config_defaults.py
git commit -m "refactor: remove hardcoded site defaults"
```

### Task 2: Move Plugin Default Site Config into Plugin Manifests

**Files:**
- Modify: `squirrel-plugins/youtube/src/squirrel_youtube/runtime.py`
- Modify: `squirrel-plugins/bilibili/src/squirrel_bilibili/runtime.py`
- Modify: `squirrel-plugins/pornhub/src/squirrel_pornhub/runtime.py`
- Modify: `squirrel-plugins/javdb/src/squirrel_javdb/runtime.py`
- Modify: `squirrel-plugins/youporn/src/squirrel_youporn/runtime.py`
- Modify: `squirrel-plugins/youtube/plugin-runtime.json`
- Modify: `squirrel-plugins/bilibili/plugin-runtime.json`
- Modify: `squirrel-plugins/pornhub/plugin-runtime.json`
- Modify: `squirrel-plugins/javdb/plugin-runtime.json`
- Modify: `squirrel-plugins/youporn/plugin-runtime.json`
- Test: `squirrel-plugins/tests/test_runtime_v2_packages.py`

- [ ] **Step 1: Write the failing manifest test**

Add an assertion in `squirrel-plugins/tests/test_runtime_v2_packages.py` that each plugin site manifest exposes metadata defaults:

```python
def test_runtime_manifest_sites_include_default_site_config_metadata():
    runtime = load_runtime_from_package('squirrel_youtube', 'youtube')
    manifest = runtime.manifest().to_dict()
    site = manifest['sites'][0]

    assert site['metadata']['label'] == 'YouTube'
    assert site['metadata']['aliases'] == ['yt']
    assert site['metadata']['http']['headers']['User-Agent']
    assert 'rate_limit' in site['metadata']
```

Duplicate this pattern for `bilibili`, `pornhub`, `javdb`, and `youporn` with their actual expected labels and key defaults.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest squirrel-plugins.tests.test_runtime_v2_packages
```

Expected:

```text
FAIL: test_runtime_manifest_sites_include_default_site_config_metadata
```

- [ ] **Step 3: Write minimal manifest metadata**

In each plugin runtime, attach default site config to `PluginSiteManifest.metadata`:

```python
PluginSiteManifest(
    site_name='youtube',
    domains=['youtube.com', 'youtu.be'],
    test_url='https://www.youtube.com',
    features=[...],
    metadata={
        'label': 'YouTube',
        'aliases': ['yt'],
        'http': {
            'headers': {
                'User-Agent': 'Mozilla/5.0 ...',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        },
        'rate_limit': {
            'enabled': True,
            'min_interval': 2.0,
            'max_interval': 5.0,
        },
        'proxy': {
            'connect_timeout': 30.0,
            'read_timeout': 180.0,
            'write_timeout': 30.0,
            'pool_timeout': 30.0,
            'keepalive_expiry': 60.0,
            'max_connections': 100,
            'max_keepalive_connections': 50,
            'chunk_size': 2 * 1024 * 1024,
            'max_retries': 5,
            'enable_http2': True,
            'follow_redirects': True,
        },
        'login': {
            'check_url': 'https://www.youtube.com/feed/channels',
            'headers': {
                'User-Agent': 'Mozilla/5.0 ...',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            'timeout': 20.0,
        },
        'metadata': {
            'requires_cookies': False,
        },
    },
)
```

Mirror the same values into each `plugin-runtime.json` so backend manifest loading and package tests stay aligned.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest squirrel-plugins.tests.test_runtime_v2_packages
```

Expected:

```text
OK
```

- [ ] **Step 5: Commit**

```bash
git add squirrel-plugins/youtube/src/squirrel_youtube/runtime.py squirrel-plugins/bilibili/src/squirrel_bilibili/runtime.py squirrel-plugins/pornhub/src/squirrel_pornhub/runtime.py squirrel-plugins/javdb/src/squirrel_javdb/runtime.py squirrel-plugins/youporn/src/squirrel_youporn/runtime.py squirrel-plugins/youtube/plugin-runtime.json squirrel-plugins/bilibili/plugin-runtime.json squirrel-plugins/pornhub/plugin-runtime.json squirrel-plugins/javdb/plugin-runtime.json squirrel-plugins/youporn/plugin-runtime.json squirrel-plugins/tests/test_runtime_v2_packages.py
git commit -m "refactor: move site defaults into plugin manifests"
```

### Task 3: Replace Override Persistence and Update `/api/sites`

**Files:**
- Modify: `squirrel-backend/services/site_catalog_service.py`
- Modify: `squirrel-backend/routes/video.py`
- Modify: `squirrel-backend/utils/site_catalog.py`
- Test: `squirrel-backend/tests/services/test_site_catalog_service.py`
- Test: `squirrel-backend/tests/routes/test_video_route.py`

- [ ] **Step 1: Write the failing tests for override-only persistence**

Replace the old full-catalog save test with an override-only test:

```python
def test_save_site_overrides_persists_override_only(monkeypatch, tmp_path):
    config_path = tmp_path / 'sites.json'
    monkeypatch.setattr(site_catalog_service, '_config_path', lambda: config_path)
    monkeypatch.setattr(
        site_catalog_service,
        'build_plugin_site_catalog',
        lambda: {
            'youtube': {
                'label': 'YouTube',
                'domains': ['youtube.com', 'youtu.be'],
                'enabled': True,
                'proxy': {'read_timeout': 180.0},
            }
        },
    )
    monkeypatch.setattr(site_catalog_service, 'apply_site_config_overrides', lambda catalog=None: None)

    result = site_catalog_service.save_site_overrides({
        'youtube': {
            'enabled': False,
            'proxy': {'read_timeout': 240.0},
        }
    })

    assert result['youtube']['enabled'] is False
    saved = json.loads(config_path.read_text(encoding='utf-8'))
    assert saved == {'youtube': {'enabled': False, 'proxy': {'read_timeout': 240.0}}}
```

Add a route test for the new request body:

```python
def test_update_sites_catalog_accepts_override_payload(monkeypatch):
    monkeypatch.setattr(
        'routes.video.save_site_overrides',
        lambda payload: {'youtube': {'enabled': False, 'domains': ['youtube.com']}},
    )
    client = TestClient(app)

    response = client.put('/api/sites', json={'sites': {'youtube': {'enabled': False}}})

    assert response.status_code == 200
    assert response.json()['data']['youtube']['enabled'] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd squirrel-backend
pipenv run pytest tests/services/test_site_catalog_service.py tests/routes/test_video_route.py -q
```

Expected:

```text
FAILED tests/services/test_site_catalog_service.py::test_save_site_overrides_persists_override_only
FAILED tests/routes/test_video_route.py::test_update_sites_catalog_accepts_override_payload
```

- [ ] **Step 3: Implement override-only storage**

In `squirrel-backend/services/site_catalog_service.py`, replace `save_sites()` with `save_site_overrides()`:

```python
ALLOWED_OVERRIDE_KEYS = {
    'enabled', 'aliases', 'http', 'proxy', 'login', 'rate_limit',
    'metadata', 'cookie', 'test_url', 'icon_url', 'label',
}

def save_site_overrides(overrides: Dict[str, dict]) -> Dict[str, dict]:
    plugin_catalog = build_plugin_site_catalog()
    cleaned: Dict[str, dict] = {}
    for slug, raw in (overrides or {}).items():
        normalized_slug = str(slug or '').strip().lower()
        if normalized_slug not in plugin_catalog:
            raise ValueError(f"未知站点: {normalized_slug}")
        cleaned_entry = _normalize_override_entry(raw)
        if cleaned_entry:
            cleaned[normalized_slug] = cleaned_entry

    config_path = _config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
    SiteCatalog.set_override_catalog(cleaned)
    apply_site_config_overrides(cleaned)
    return get_effective_site_catalog(cleaned)
```

In `squirrel-backend/routes/video.py`, update the PUT handler:

```python
@router.put('/api/sites')
def update_sites_catalog(payload: dict = Body(...)):
    sites_payload = payload.get('sites') if isinstance(payload, dict) else None
    if not isinstance(sites_payload, dict):
        return response.param_error('sites 必须为对象')
    try:
        catalog = save_site_overrides(sites_payload)
        return response.success(catalog, msg='站点配置已更新')
    except ValueError as exc:
        return response.param_error(str(exc))
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd squirrel-backend
pipenv run pytest tests/services/test_site_catalog_service.py tests/routes/test_video_route.py -q
```

Expected:

```text
....                                                                     [100%]
```

- [ ] **Step 5: Commit**

```bash
git add squirrel-backend/services/site_catalog_service.py squirrel-backend/routes/video.py squirrel-backend/utils/site_catalog.py squirrel-backend/tests/services/test_site_catalog_service.py squirrel-backend/tests/routes/test_video_route.py
git commit -m "refactor: make site config persistence override-only"
```

### Task 4: Switch All Backend Consumers to Effective Catalog

**Files:**
- Modify: `squirrel-backend/routes/plugins.py`
- Modify: `squirrel-backend/utils/cookie.py`
- Modify: `squirrel-backend/services/site_login_status_service.py`
- Modify: any remaining `SiteCatalog.get_catalog()` consumers found by ripgrep
- Test: `squirrel-backend/tests/routes/test_plugin_routes.py`
- Test: `squirrel-backend/tests/utils/test_cookie.py`
- Test: `squirrel-backend/tests/services/test_site_login_status_service.py`

- [ ] **Step 1: Write the failing regression tests**

Add a cookie regression test that only plugin defaults define `youporn`:

```python
def test_resolve_cookie_file_for_url_uses_plugin_defined_site(tmp_path, monkeypatch):
    cookie_file = tmp_path / 'youporn.txt'
    cookie_file.write_text('', encoding='utf-8')
    monkeypatch.setattr(cookie, '_get_cookie_site_catalog', lambda: {
        'youporn': {'domains': ['youporn.com']}
    }, raising=False)
    monkeypatch.setattr(cookie, 'get_site_cookies_file_path', lambda slug: cookie_file)

    assert cookie.resolve_cookie_file_for_url('https://www.youporn.com/') == str(cookie_file)
```

Add a login-status service test that reads from the effective catalog entry even when no file catalog exists:

```python
def test_get_supported_sites_stays_driven_by_plugin_routes(monkeypatch):
    monkeypatch.setattr(
        site_login_status_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(
            get_snapshot=lambda: SimpleNamespace(
                registrations=[SimpleNamespace(capability='check_login_status', site_name='youporn')]
            )
        ),
    )
    assert site_login_status_service.get_supported_sites() == {'youporn'}
```

Keep the existing route tests for runtime-only `youporn` cookies upload and update them if helper names change.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd squirrel-backend
pipenv run pytest tests/routes/test_plugin_routes.py tests/utils/test_cookie.py tests/services/test_site_login_status_service.py -q
```

Expected:

```text
At least one FAIL in the new effective-catalog regression tests
```

- [ ] **Step 3: Replace remaining direct catalog reads**

In each backend consumer, replace direct `SiteCatalog.get_catalog()` usage with explicit effective-catalog access:

```python
from core.site_config_manager import get_effective_site_catalog

def _get_cookie_site_catalog() -> dict:
    return get_effective_site_catalog()
```

For route consumers:

```python
catalog = get_effective_site_catalog()
site_info = build_site_info(site_name, catalog)
```

Use:

```bash
rg -n "SiteCatalog.get_catalog\\(" squirrel-backend
```

Expected remaining matches after cleanup:

```text
Only tests or explicit override-loader internals
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd squirrel-backend
pipenv run pytest tests/routes/test_plugin_routes.py tests/utils/test_cookie.py tests/services/test_site_login_status_service.py -q
```

Expected:

```text
............                                                             [100%]
```

- [ ] **Step 5: Commit**

```bash
git add squirrel-backend/routes/plugins.py squirrel-backend/utils/cookie.py squirrel-backend/services/site_login_status_service.py squirrel-backend/tests/routes/test_plugin_routes.py squirrel-backend/tests/utils/test_cookie.py squirrel-backend/tests/services/test_site_login_status_service.py
git commit -m "refactor: unify backend site config consumers"
```

### Task 5: Convert Frontend Site Settings to Override-Only Editing

**Files:**
- Modify: `squirrel-frontend/src/api/sites.ts`
- Modify: `squirrel-frontend/src/composables/useSites.ts`
- Modify: `squirrel-frontend/src/components/settings/SiteConfigSection.vue`
- Modify: `squirrel-frontend/src/components/settings/SiteConfigEditorDialog.vue`
- Optional Create: `squirrel-frontend/src/utils/siteOverrides.ts`
- Test: manual browser validation

- [ ] **Step 1: Write the failing frontend behavior note and add helper-level unit-free guard**

Create a small pure helper in `useSites.ts` or `utils/siteOverrides.ts` and drive it from a local assertion-style function:

```ts
export const buildSiteOverridePayload = (
  baseCatalog: SitesResponse,
  draftCatalog: SitesResponse,
): Record<string, Record<string, unknown>> => {
  // returns only changed allowed keys per slug
}
```

Use an inline temporary assertion block while implementing:

```ts
const payload = buildSiteOverridePayload(
  { youtube: { label: 'YouTube', domains: ['youtube.com'], enabled: true } },
  { youtube: { label: 'YouTube', domains: ['youtube.com'], enabled: false } },
)
console.assert(JSON.stringify(payload) === JSON.stringify({ youtube: { enabled: false } }))
```

- [ ] **Step 2: Run frontend type/build check to establish baseline**

Run:

```bash
cd squirrel-frontend
npm run build:check
```

Expected:

```text
Build fails or stays green before edits; record current status before changing behavior
```

- [ ] **Step 3: Implement override-only frontend save flow**

In `useSites.ts`, replace array payload generation with override diff logic:

```ts
const buildSiteOverridePayload = (baseCatalog: SitesResponse, updatedCatalog: SitesResponse) => {
  const overrides: Record<string, Record<string, unknown>> = {}
  for (const [slug, updated] of Object.entries(updatedCatalog)) {
    const base = baseCatalog[slug] || {}
    const entry: Record<string, unknown> = {}
    for (const key of ['enabled', 'label', 'aliases', 'http', 'proxy', 'login', 'rate_limit', 'metadata', 'cookie', 'test_url', 'icon_url']) {
      if (JSON.stringify(updated?.[key]) !== JSON.stringify(base?.[key])) {
        entry[key] = updated?.[key]
      }
    }
    if (Object.keys(entry).length) {
      overrides[slug] = entry
    }
  }
  return overrides
}
```

In `SiteConfigSection.vue`, keep an immutable `baseCatalogSnapshot` and pass only changed site payloads to `saveCatalog`.

In `SiteConfigEditorDialog.vue`, remove plugin-owned fields:

```vue
<!-- Remove domains and test_url editing from the form -->
<!-- Keep enabled, aliases, headers, proxy, login, rate_limit, metadata, label, icon_url -->
```

At save time, emit only allowed override fields:

```ts
emit('save', {
  slug,
  sitePayload: {
    enabled: !!siteEditorForm.value.enabled,
    label,
    aliases,
    metadata: { ... },
    proxy: proxyPayload,
    login: loginPayload,
    rate_limit: rateLimitPayload,
    http: Object.keys(httpHeaders).length ? { headers: httpHeaders } : undefined,
    icon_url: iconUrl || undefined,
  },
})
```

- [ ] **Step 4: Run frontend verification**

Run:

```bash
cd squirrel-frontend
npm run build:check
```

Expected:

```text
Build completes without type or Vite errors
```

Then validate manually:

```text
1. Open settings page
2. Confirm plugin-provided sites appear without manual registration
3. Edit only enabled/proxy/login-related fields
4. Save and confirm backend writes override-only payload
```

- [ ] **Step 5: Commit**

```bash
git add squirrel-frontend/src/api/sites.ts squirrel-frontend/src/composables/useSites.ts squirrel-frontend/src/components/settings/SiteConfigSection.vue squirrel-frontend/src/components/settings/SiteConfigEditorDialog.vue
git commit -m "refactor: make site settings save overrides only"
```

### Task 6: End-to-End Cleanup and Final Verification

**Files:**
- Modify: any remaining direct `SiteCatalog.get_catalog()` callers
- Modify: `config/sites.json` during manual validation only
- Test: `squirrel-backend/tests/routes/test_plugin_routes.py`
- Test: `squirrel-backend/tests/utils/test_cookie.py`
- Test: `squirrel-backend/tests/core/test_site_config_manager.py`
- Test: `squirrel-backend/tests/services/test_site_catalog_service.py`
- Test: `squirrel-backend/tests/plugins/test_site_catalog_runtime_models.py`
- Test: `squirrel-plugins/tests/test_runtime_v2_packages.py`

- [ ] **Step 1: Run the full targeted backend and plugin suite**

Run:

```bash
cd squirrel-backend
pipenv run pytest tests/routes/test_plugin_routes.py tests/utils/test_cookie.py tests/core/test_site_config_manager.py tests/services/test_site_catalog_service.py tests/plugins/test_site_catalog_runtime_models.py tests/services/test_site_login_status_service.py tests/routes/test_video_route.py -q
cd ../
python -m unittest squirrel-plugins.tests.test_runtime_v2_packages
```

Expected:

```text
All targeted backend tests pass
OK
```

- [ ] **Step 2: Run compile/build verification**

Run:

```bash
python -m compileall squirrel-backend squirrel-plugins
cd squirrel-frontend
npm run build:check
```

Expected:

```text
Python files compile successfully
Frontend build succeeds
```

- [ ] **Step 3: Run repository grep to prove old architecture is gone**

Run:

```bash
rg -n "SITE_CONFIG_DEFAULTS|save_sites\\(|sites_payload = payload.get\\(\"sites\"\\).*list|SiteCatalog.get_catalog\\(" squirrel-backend squirrel-frontend
```

Expected:

```text
No production matches for SITE_CONFIG_DEFAULTS
No production matches for save_sites(
No production matches for direct SiteCatalog.get_catalog() consumers
```

- [ ] **Step 4: Manually verify YouPorn as the regression case**

Run:

```bash
cd squirrel-backend
pipenv run python -c "from utils.cookie import filter_cookies_to_query_string; print(bool(filter_cookies_to_query_string('https://www.youporn.com/')))"
pipenv run python -c "from services.site_login_status_service import test_site_login_status; import json; print(json.dumps(test_site_login_status('youporn'), ensure_ascii=False))"
```

Expected:

```text
True
{"site_name": "youporn", "supported": true, ...}
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: unify plugin-defined site catalog architecture"
```

## Self-Review

### Spec coverage

The plan covers:

1. Removing backend hardcoded defaults in Task 1
2. Making plugin manifests the only site-definition source in Task 2
3. Converting `config/sites.json` to override-only in Task 3
4. Unifying backend consumers on effective catalog in Task 4
5. Updating frontend save behavior to override-only in Task 5
6. Validating the `YouPorn` cookie/login regression path in Task 6

### Placeholder scan

No `TODO`, `TBD`, or implicit “write tests later” steps remain. Every task has explicit files, commands, and concrete code direction.

### Type consistency

The plan consistently uses:

1. `build_plugin_site_catalog()` for plugin defaults
2. `load_override_catalog()` / `set_override_catalog()` semantics for file-backed overrides
3. `get_effective_site_catalog()` as the only runtime consumer entry
4. `save_site_overrides()` as the replacement for `save_sites()`

