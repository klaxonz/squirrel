Site Runtime
============

The backend owns a site runtime system for first-party site adapters:

- site runtimes are discovered from workspace runtime metadata
- each runtime exposes a `create_site_runtime()` entrypoint through the SDK contract
- host-side routing goes through `SiteRuntimeManager` and `SiteRuntimeGateway`
- runtime capabilities are declared in the manifest instead of inferred from SDK registries
- the old `plugins_ext` compatibility tree has been removed from the backend repository

Runtime packages are expected to ship a `site-runtime.json` file containing:

- `entrypoint`
- `manifest.runtime_id`
- `manifest.version`
- `manifest.capabilities`
- `manifest.sites`
- `manifest.permissions`

The backend owns runtime bootstrap state for the host process, including
Cloudflare bypass client wiring, site config projection, backend rate-limit
policy, and backend-side cookie resolution. `squirrel-sdk` remains the plugin
runtime contract and helper package, but backend runtime startup should not depend on
SDK-global mutable state.

Discovery and activation
------------------------

Site runtime packages under `../squirrel-site-runtimes/<site>/site-runtime.json` are
auto-discovered and bootstrapped as local site runtimes. The backend no longer
accepts uploaded zip packages or provisions per-runtime virtual environments. Runtime subprocesses use
the backend interpreter and receive explicit `SQUIRREL_SITE_RUNTIME_*` variables for
runtime id, version, granted permissions, and data directory.

Operators can define `manifest.metadata.runtime_policy` and
`manifest.metadata.network_policy`; these values are passed into the runtime
context. Runtime stdout/stderr and audit events are written under the runtime data
directory when one is configured.

Permissions and trust model
---------------------------

Site runtime requests go through explicit capabilities declared by each manifest:

- `extract_video`
- `sync_subscription`
- `import_subscriptions`
- `resolve_subscription`
- `check_login_status`
- `fetch_subtitles`
- `resolve_proxy_config`
- `rewrite_proxy_playlist`

Legacy in-process SDK registries remain only as a compatibility layer for code that
has not yet been migrated. New backend integrations should not use host-side
registry lookups as their primary path.

Development setup
-----------------

```bash
pipenv install
pipenv run pip install -e ../squirrel-sdk
```

For production environments, install the SDK from the local package path or wheel:

```bash
pip install /path/to/squirrel-sdk
```





