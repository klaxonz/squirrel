Site Plugins
============

The backend uses first-party site plugins from this monorepo:

- plugin metadata and capability handlers live under `../squirrel-site-runtimes`
- backend routing goes through `infrastructure.site_plugins.registry`
- plugin calls are in-process Python calls
- the backend does not accept uploaded plugin packages
- plugin enablement and site settings come from `config/sites.json`

Supported capabilities:

- `extract_video`
- `sync_subscription`
- `import_subscriptions`
- `resolve_subscription`
- `check_login_status`
- `fetch_subtitles`
- `resolve_proxy_config`
- `rewrite_proxy_playlist`

The only retained process boundary is inside plugins that actually need one,
such as YouTube's Node `youtubei` worker. There is no backend site-runtime
supervisor, bridge server, gateway, store, health check, or runtime discovery
layer.

Development setup
-----------------

```bash
pipenv install
```
