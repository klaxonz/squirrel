Plugin Runtime V2
=================

The backend now uses a runtime V2 plugin model:

- plugins are discovered from runtime metadata plus backend-managed install records
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

Install and activation
----------------------

Plugin installation is handled by the backend plugin API. Upload a plugin zip that
contains `plugin-runtime.json`; once validated, the backend stages the package,
creates a dedicated virtual environment, installs the plugin together with the
runtime bridge package, starts the runtime, registers capabilities, and makes the
plugin effective without restarting the service.

For workspace development, plugins under `../squirrel-plugins/<site>/plugin-runtime.json`
are auto-discovered and bootstrapped as local runtime V2 plugins. Workspace plugins
still use the backend interpreter as a development convenience; uploaded plugins use
their own isolated Python environment.
Installed plugin subprocesses receive a reduced inherited environment and explicit
`SQUIRREL_PLUGIN_*` variables for plugin id, version, granted permissions, and
data directory.

Operators can also define `manifest.metadata.runtime_policy` and
`manifest.metadata.network_policy` to control runtime limits and outbound
network access. Runtime stdout/stderr and audit events are written under the
plugin data directory.

Permissions and trust model
---------------------------

Runtime V2 assumes plugins may be untrusted. The host tracks declared permissions
from the manifest and only routes requests through explicit capabilities such as:

- `extract_video`
- `resolve_playback`
- `sync_subscription`
- `import_subscriptions`
- `resolve_subscription`
- `check_login_status`
- `fetch_subtitles`
- `build_mpd`
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



