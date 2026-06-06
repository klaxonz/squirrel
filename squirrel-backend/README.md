Plugin Runtime V2
=================

The backend now uses a runtime V2 plugin model:

- plugins are discovered from workspace runtime metadata
- each plugin exposes a `create_plugin_runtime()` entrypoint
- host-side routing goes through `PluginManager` and `PluginGateway`
- plugin capabilities are declared in the manifest instead of inferred from SDK registries
- the old `plugins_ext` compatibility tree has been removed from the backend repository

Runtime V2 packages are expected to ship a `plugin-runtime.json` file containing:

- `entrypoint`
- `manifest.plugin_id`
- `manifest.version`
- `manifest.capabilities`
- `manifest.sites`
- `manifest.permissions`

The backend owns runtime bootstrap state for the host process, including
Cloudflare bypass client wiring, site config projection, backend rate-limit
policy, and backend-side cookie resolution. `squirrel-sdk` remains the plugin
contract and helper package, but backend runtime startup should not depend on
SDK-global mutable state.

Discovery and activation
------------------------

Plugins under `../squirrel-plugins/<site>/plugin-runtime.json` are auto-discovered
and bootstrapped as local runtime V2 plugins. The backend no longer accepts plugin
zip uploads or provisions per-plugin virtual environments. Runtime subprocesses use
the backend interpreter and receive explicit `SQUIRREL_PLUGIN_*` variables for
plugin id, version, granted permissions, and data directory.

Operators can define `manifest.metadata.runtime_policy` and
`manifest.metadata.network_policy`; these values are passed into the runtime
context. Runtime stdout/stderr and audit events are written under the plugin data
directory when one is configured.

Permissions and trust model
---------------------------

Runtime V2 routes requests through explicit capabilities declared by each manifest:

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



