Site integrations
=================

The backend hosts first-party site integrations from this monorepo:

- site packages live in-tree under `squirrel-backend/sites/`:
  `crawl` (shared interface layer) + `squirrel_youtube` / `squirrel_bilibili`
- backend routing goes through `infrastructure.site_registry.registry`
- site handlers run in-process (plain Python calls, no RPC gateway)
- site enablement and settings come from `config/sites.json`

Supported capabilities (the only five the registry routes):

- `extract_video`
- `sync_subscription`
- `import_subscriptions`
- `resolve_subscription`
- `check_login_status`

Invocation model
----------------

`infrastructure.site_registry.registry` loads each site's typed runtime object
(`get_site_runtime()`, cached) and consumers call the five methods directly:
`extract_video`, `sync_subscription`, `import_subscriptions`,
`resolve_subscription`, `check_login_status`. Sites raise the crawl exceptions
(`AuthError`/`NetworkError`/`ParseError`/`RateLimitError`).

`sync_subscription` additionally runs behind
a subprocess deadline boundary (`shared_kernel.infrastructure.deadline`,
`run_with_deadline`, 120s): a wedged crawl is terminated, then killed. The
other capabilities stay in-process — their HTTP calls carry their own
timeouts (httpx read_timeout up to 180s; the youtubei node worker enforces
its own 20s per request).

Inside the backend, site code consumes backend-owned state through the
`crawl` helpers: cookie resolution, Cloudflare bypass client, and effective
site config (manifest defaults overridden by `config/sites.json`). YouTube's
Node `youtubei` worker daemon runs as its own process, spawned by
`squirrel_youtube.youtubei_resolver`.

There is no HTTP gateway or bridge server and no discovery layer:
registration is the hardcoded slug -> module mapping in the registry module.

Service composition
-------------------

The web process composes application services in `application.app.create_app`
and exposes them to HTTP dependencies through `app.state`. Worker processes
compose an independent `SubscriptionService` graph. Shared dependencies such
as `CrawlTaskService` and `UserConfigService` are created once per graph and
passed explicitly to consumers; leaf service modules must not export mutable
process-wide service instances or method aliases bound to those instances.

Process-wide instances are reserved for resources whose identity is the
lifecycle boundary itself: the managed-thread registry, scheduler task manager,
and site runtime registry. Site runtimes are started during process bootstrap
and stopped during shutdown. Stateless helpers and database-backed services
remain classes or functions and are constructed by their owning composition
root.

Development setup
-----------------

```bash
pipenv install
```
