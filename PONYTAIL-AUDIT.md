# Ponytail Audit — `squirrel-backend`

Repo-wide simplicity audit, backend-scoped. Tags follow `ponytail-review`:
- `delete:` dead code, unused flexibility, speculative feature. Replacement: nothing.
- `stdlib:` hand-rolled thing the standard library ships. Name the function.
- `native:` dependency or code doing what the platform already does. Name the feature.
- `yagni:` abstraction with one implementation, config nobody sets, layer with one caller.
- `shrink:` same logic, fewer lines. Show the shorter form.

Ranked biggest cut first. All references confirmed via repo-wide grep + reading the code.

---

## delete (dead code — largest cuts)

1. **delete** Whole consumer half of the messaging framework — `@queue_listener`/`ConsumerRegistry`/`ConsumerSpec`/`RedisStreamConsumer` are wired but **never used**: no `@queue_listener` is applied anywhere in the repo, and `runner.start()` imports a `messaging.handlers` package that does not exist (`runner.py:70`). Only the producer half (`RedisStreamProducer.xadd`) is live. Drop `decorators.py`, `registry.py`, `consumer.py`, the consumer-start body of `runner.py` (lines 68–106), and `ConsumerOptions.max_delivery` default. Replacement: nothing. ~350 LOC. `infrastructure/messaging/framework/decorators.py`; `registry.py`; `consumer.py`; `runner.py:68`

2. **delete** Whole `strategies/` indirection. `StrategyRegistry` (41 LOC) + `update_strategy` decorator never register (zero `@update_strategy`); `orchestrator._select_strategy` (`orchestrator.py:295`) always falls through to `default_strategy`. Fold `DefaultUpdateStrategy`'s 3 methods into `SubscriptionOrchestrator` and delete `strategies/base.py`, `registry.py`, `__init__.py`. Replacement: nothing. ~120 LOC. `domains/subscription/application/services/core/update/strategies/`

3. **delete** Whole `infrastructure/site_catalog/cache.py` module (66 LOC) — `SiteCatalogCache`, `get_cached_site_catalog`, `format_datetime`, `parse_datetime` have zero references outside the file (the test mentioned in `.pytest_cache/lastfailed` no longer exists; `_parse_datetime` in rss is unrelated). Replacement: nothing. `infrastructure/site_catalog/cache.py`

4. **delete** `ExtractorFactory`'s 5 unreferenced methods: `get_test_url`, `get_all_sites`, `get_all_domains`, `get_extractor_by_site`, `clear_cache`. `reset_factory` (line 160) is only used by one test. Replacement: nothing. `infrastructure/extraction/factory.py:122`

5. **delete** `BaseResultHandler` base class + module-level `video_extraction_handler` singleton — the singleton is never imported, and `VideoExtractionHandler` is the only `BaseResultHandler` subclass and only its own `.process()` is called. Replacement: nothing. `infrastructure/extraction/handlers/video_handler.py:118`; `infrastructure/extraction/base.py`

6. **delete** `ExtractionTask.to_dict`, `ExtractionTask.can_retry`, `PipelineContext.to_dict`, `ExtractionResult.to_dict` — zero callers; `max_retries`/`retry_count` fields exist only to feed unused `can_retry`. Replacement: nothing. `infrastructure/extraction/contracts.py:47`; `infrastructure/extraction/pipeline/context.py:52`

7. **delete** `TaskProcessor` and `ResultHandler` `runtime_checkable` Protocols — nothing is checked against them and `can_process` is never called. Pure speculative abstraction. Replacement: nothing. `infrastructure/extraction/contracts.py:125`

8. **delete** `redis_client.get_redis_client`, `set_redis_client`, `get_distributed_lock` — zero callers; `get_distributed_lock` drags in the **`python-redis-lock`** dependency (`Pipfile:28`) whose only use is this dead function. Removing it lets you **drop 1 dep**. Replacement: nothing. `infrastructure/cache/redis_client.py:51`

9. **delete** Dead params on 6 functions in `_completion.py` — `_complete_sync_success_in_session`, `mark_sync_success`, `continue_full_sync_batch`, `mark_sync_skipped`, `mark_sync_failed`, `defer_sync_state`, `decrement_pending_video_count` all accept `run_id`/`request_id`/`trace_id`/`trigger`/`videos_enqueued`/`source_video_count` but never read them. Trim all signatures. Replacement: nothing. `domains/subscription/application/services/core/sync/state/_completion.py:23`

10. **delete** `session_factory` + `get_type_mapping` ctor params on both `CrawlExecutorService` classes — stored as `self.*`, never referenced in body or call sites (always `None`). Replacement: nothing. `domains/subscription/application/services/crawl/executors/video_extract_executor.py:13`; `subscription_sync_executor.py:19`

11. **delete** `domains/user/application/services/search/suggestions/listings.py` — 5 functions fully superseded by `pools.py`, zero imports anywhere incl. tests. Replacement: nothing. `domains/user/application/services/search/suggestions/listings.py`

12. **delete** `with_trace()` decorator — only referenced in its own docstring examples, never applied. Replacement: nothing. `shared_kernel/infrastructure/trace.py:94`

13. **delete** `workers/bootstrap.py:wait_for_shutdown()` (line 102) — defined but never called; process files run their own `while not event.is_set()` loop. Replacement: nothing.

14. **delete** 6 task `shutdown()` classmethods — `cloudflare_heartbeat`, `meili_reindex`, `subscription_auto_import`, `full_update`, `incremental_update`, `pending_reconcile` each have a `@classmethod shutdown()` with only `logger.info("...shutdown")` and zero call sites. Replacement: nothing. `workers/scheduling/tasks/`

15. **delete** Duplicate `_parse_trigger` — verbatim in both `subscription_sync_executor._parse_trigger` and `_gap._parse_trigger`. Hoist into `update/models.py`, delete one. Replacement: shared helper. `domains/subscription/application/services/crawl/executors/subscription_sync_executor.py:87`; `core/sync/state/_gap.py:212`

16. **delete** Duplicate constants block — `DEFAULT_LIMIT`/`MAX_LIMIT`/`SUGGESTION_POOL_TTL_SECONDS`/`SUGGESTION_RESULT_TTL_SECONDS`/`SUGGESTION_POOL_MAX_ITEMS` already defined and used in `suggestion_service.py`+`formatting.py`; `pools.py`'s copies are never read. Replacement: nothing. `domains/user/application/services/search/suggestions/pools.py:16`

17. **delete** `RATE_LIMITS` scaffolding — `RateLimiter.DEFAULT_LIMITS = {}` is never populated (site configs go through `add_rate_limit`), so `.get(sld, DEFAULT_RATE_LIMIT)` is just `DEFAULT_RATE_LIMIT`. Collapse to one constant. Replacement: nothing. `shared_kernel/infrastructure/rate_limiter.py:30`

18. **delete** `cookiecloud_sync_task` redundant `interval`/`unit`/`start_immediately` class attrs (9–13) — `@TaskRegistry.register` already sets them; only one source is read. Replacement: pick one. `workers/scheduling/tasks/cookiecloud_sync_task.py:9`

19. **delete** `messaging/worker.py:_worker_threads` — assigned but never iterated for join; daemon-thread pattern confirms nothing waits on it. Replacement: nothing. `workers/messaging/worker.py:11`

## yagni (one-impl / pass-through indirection)

20. **yagni** `StageConfig.critical` flag + `PipelineConfig.critical_stages` — written (`config.py:57`) but never read; `ExtractionPipeline._should_continue_after_error` hardcodes its own critical set (`base.py:173`). Replacement: pipeline's local set. `infrastructure/extraction/pipeline/config.py:16`

21. **yagni** `NsfwPolicy` class — one `@staticmethod` instantiated as a singleton and re-exported as a module function. Replacement: plain module function. `domains/video/application/services/moderation/nsfw_policy.py:6`

22. **yagni** `VideoListService.video_extra_profiles`/`merge_profiles` staticmethods only call the already-imported module-level `_video_extra_profiles`/`_merge_profiles`, then re-exported — no caller uses the class attrs (grep confirms). Replacement: re-export from the imported names directly. `domains/video/application/services/listing/service.py:649`

23. **yagni** `VideoInteractionService` / `VideoClipMarkerService` / `ActorProcessorService` — class instantiated as a singleton then re-exported as module-function aliases; callers could import the function directly. Lower priority (real logic lives here). `domains/video/application/services/engagement/interaction.py:57`; `clip_marker.py:202`; `extraction/actor_processor.py:12`

24. **yagni** `RedisStreamProducer.__init__` is empty and every call site is `RedisStreamProducer().send(...)`. Replacement: `send` as a module function/`@staticmethod`; drop the per-call instantiation. `infrastructure/messaging/framework/producer.py:13`

25. **yagni** `CrawlDispatcherPolicy.is_task_type_available`/`is_site_available` — two-line predicates each called once in `_try_claim_candidate`. Replacement: inline at call site. `domains/subscription/application/services/crawl/dispatcher/policy.py:33`

## stdlib / native / shrink

26. **native** `get_distributed_lock` hand-rolls a distributed lock via `redis_lock.Lock` — `redis.Redis.lock(name, timeout=…)` ships built-in (redis-py ≥4). Only relevant if the dead path is revived; replace with `redis_client.lock(key, timeout=…, blocking=True)`. `infrastructure/cache/redis_client.py:61`

27. **shrink** `RedisStreamProducer.send` hand-rolled linear-backoff retry (`producer.py:40–56`) — re-raises anyway after sleeping 0.1–0.4s. Replacement: call `redis_client.xadd(...)` directly and let caller decide. ~15 LOC → 1. `infrastructure/messaging/framework/producer.py:40`

28. **shrink** `MusicCommentsMixin` — 5 paginated comment methods byte-for-byte identical except for endpoint path + param key (~22 LOC each). Replacement: one `_paginated_comments(path, id_field, ...)` helper; each call site becomes one line. ~80 LOC. `domains/music/application/services/_comments.py:10`

29. **shrink** `_filter_and_paginate` vs `_filter_and_offset_paginate` in `VideoListService` — near-duplicate ~30-line methods differing only on `page_ids` slice vs OFFSET+cursor re-encode. Replacement: one `_paginate(filtered_ids, …, *, mode)`. `domains/video/application/services/listing/service.py:162`

30. **shrink** Duplicate `to_bool` — module-level `to_bool` in `system_config.py` reimplements `SystemConfigService._to_bool` (identical `TRUE_SET`/`FALSE_SET`). Replacement: one shared helper. `domains/system/interfaces/http/system_config.py:16` vs `config_service.py:23`

31. **shrink** Duplicate `normalize_query` verbatim in `suggestions/formatting.py:9` and `suggestions/text.py:4`. Replacement: keep one. `domains/user/application/services/search/suggestions/`

---

## Checked and deliberately NOT flagged

- `TaskRegistry` (scheduling/base.py) — load-bearing: `TaskRegistry.tasks` is read by production `bootstrap.py:26`. Kept.
- `TaskFactory` single-impl — real runtime instantiation hub, not worth the churn.
- All 49 alembic migrations — linear chain to head `f6c4027dbf73`, no orphans.
- `create_client` RSS factory — 3 real providers, not YAGNI.
- music `normalizers/*` and mixins — do genuinely distinct endpoint transforms.

---

**Net: ~-550 lines, -1 dependency possible** (`python-redis-lock`, unlocked by dropping `get_distributed_lock`). The three biggest cuts — the dead consumer framework, the `strategies/` indirection, the `SiteCatalogCache` module —account for ~50% of the deletion size if you want a fast first pass.

## Execution log

Executed in two commits on branch `fix/bug`. Baseline preserved throughout: **360 tests pass, ruff clean** (matches pre-audit baseline).

- [x] **1** (revised) messaging consumer glue — `decorators.py`, `registry.py` deleted; `runner.py` consumer-start body removed (WorkerRunner kept as no-op, live entrypoint preserved); `consumer.py` kept (tested primitive). Original finding over-reached: `WorkerRunner.start()` IS live (called by the worker process entrypoint), only the consumer-dispatch half was dead.
- [x] **2** strategies/ indirection — `UpdateStrategy` ABC + `StrategyRegistry` + `update_strategy` decorator deleted; `execute()` folded into concrete `DefaultUpdateStrategy`; orchestrator simplified to call it directly. `default_strategy.py` kept (tests import it directly).
- [x] **3** SiteCatalogCache module deleted.
- [x] **4** ExtractorFactory: 5 dead methods deleted; `reset_factory` simplified (kept as test helper).
- [x] **5** BaseResultHandler base deleted; `video_extraction_handler` singleton + dead `handle_failure` override removed; `VideoExtractionHandler` now a plain class.
- [x] **6** `ExtractionTask.to_dict`/`can_retry`, `ExtractionResult.to_dict`, `PipelineContext.to_dict` deleted.
- [x] **7** `TaskProcessor`/`ResultHandler` Protocols deleted; `TaskPriority.LOW/URGENT` removed.
- [x] **8** redis_client: `get_redis_client`/`set_redis_client`/`get_distributed_lock` deleted; **`python-redis-lock` dependency dropped** (Pipfile + Pipfile.lock regenerated).
- [~] **9** _completion.py dead params — **DEFERRED**. 10+ callers across orchestrator/executors, pure cosmetic with no functional gain and high miss-risk. Worth a dedicated PR if pursued.
- [x] **10** CrawlExecutor ctor params (`session_factory`/`get_type_mapping`) removed on both classes + test helpers updated.
- [x] **11** suggestions/listings.py deleted; duplicate constants in pools.py removed (CREATOR_FEED_WINDOW kept — it IS used internally).
- [x] **12** `with_trace` decorator + now-unused imports deleted; `wait_for_shutdown` deleted; 6 task `shutdown()` classmethods deleted.
- [x] **15** duplicate `_parse_trigger` hoisted to `update/models.py:parse_trigger`; `RATE_LIMITS` empty-dict scaffolding collapsed.
- [~] **30** to_bool — **DONE in round 2** (see below). The round-1 skip理由 was over-cautious: a single `to_bool(val, default: bool | None = None)` module function in `config_service.py` satisfies both old signatures (`bool|None` unknown-return via the default, `default`-returning via the explicit arg). `SystemConfigService._to_bool` removed; `system_config.py:to_bool` replaced with an import.
- [~] **31** normalize_query — **DEFERRED, intentionally**. Each copy (`suggestions/formatting.py:9`, `suggestions/text.py:4`) is used only within its own module; merging a 1-line `' '.join(str(value or '').strip().split())` would create cross-module coupling for trivial dedupe. Re-confirmed round 2: not worth it.

Deferred item **9** remains documented above for a future PR — high caller-count (orchestrator/commands/coordinator/progress_service) on failure-path code, pure cosmetic, low ROI vs. miss-risk.

---

## Round 2 — re-audit findings (2026-06-19)

Re-scanned `infrastructure/`, `domains/`, `workers/` for new bloat since round 1, plus Pipfile dep audit. Every finding below was confirmed by reading the code (not just grep).

### 32. **delete** 5 dead Pipfile dependencies — zero source importers (confirmed via repo-wide grep): `jinja2`, `pathvalidate`, `feedparser`, `yt-dlp` (no `yt_dlp`/`YoutubeDL` anywhere), `bgutil-ytdlp-pot-provider`. Drop from `Pipfile`. `squirrel-backend/Pipfile:9,10,20,21,22`

### 33. **delete** `RateLimitError` exception class — never raised anywhere (extraction stages raise `NetworkError`/`PermissionError`/`VipError`/`ResourceNotFoundError`). `PipelineError` is NOT dead — it is the parent of live `StageExecutionError` — so only `RateLimitError` was cut. `infrastructure/extraction/exceptions.py:82`

### 34. **delete** `VideoListPage.timings` field + 6 `perf_counter` blocks in `page_loader.load_page` — computed (videos_ms/history_ms/subscriptions_ms/creators_ms/thumbnails_ms/assemble_ms) but **never read**; `service.py` emits its own `recall_ms`/`filter_ms`/`page_ms` timings via `_EMPTY_TIMINGS` and ignores `page.timings`. `domains/video/application/services/listing/page_loader.py:19-110`

### 35. **delete** Duplicate dependency file `infrastructure/site_catalog/routes/site_cookies_dependencies.py` — byte-identical to `sites_dependencies.py` (same `get_catalog_service` + `get_login_service`). Its 2 callers (`site_cookies_bulk_import.py`, `site_cookies_single_upload.py`) re-pointed at `sites_dependencies`; file deleted. `infrastructure/site_catalog/routes/`

### 36. **delete** `CookieCloudSyncTask` redundant `interval`/`unit`/`start_immediately` class attrs (same as round-1 finding #18, applied now) — `@TaskRegistry.register(...)` already assigns them. `workers/scheduling/tasks/cookiecloud_sync_task.py:11-13`

### Round-2 items DEFERRED (functional decisions, not pure dead code)

- **write-only Redis Streams pipeline** — `RedisStreamProducer.send(QUEUE_SUBSCRIBE, ...)` is called from `import_service.py:210` and `manage.py:219`, but nothing consumes that stream (the `@queue_listener`/consumer half was already cut in round 1). The producer writes into a void. Either wire a consumer or delete the producer half + both call sites + `MqMessage` codec. **Deferred pending product decision** on whether the subscribe-queue was ever meant to be consumed. `infrastructure/messaging/framework/producer.py:13`

### Round-2 items REVERSED (agent findings disproven on code inspection)

- `RssService` class (services/service.py:23) flagged as a dead 140-line delegator — **WRONG**: it is the live FastAPI dependency injected via `Depends(get_rss_service)` into every rss http route (accounts/entries/feeds/sync). Not cut.
- `extraction/dto/validators.py` flagged as yagni wrappers — **WRONG**: all three (`validate_url`/`validate_not_empty`/`validate_duration`) are imported and used by `video_dto.py` pydantic validators. Not cut.
- `url.py` SLD helpers flagged as three-way duplication — **WRONG**: `extract_top_level_domain` has 12 callers, `extract_second_level_domain` has 3 callers (rate_limiter), `normalize_domain` has 5 callers (crud/persistence/history/query_filters). Distinct functions serving distinct call sites. Not cut.
- `_resolve_mode` flagged as a no-op — **PARTIALLY WRONG**: it collapses `UpdateMode.SMART` → `INCREMENTAL`, so it is not identity. It is however a duplicate of `command_payloads.py:9`. Low-ROI to dedupe; left in place.

## Round-2 execution log

Executed on branch `fix/bug`. Baseline preserved: **360 tests pass, ruff clean** (matches pre-round-2 baseline).

- [x] **32** 5 dead deps dropped from `Pipfile` (jinja2, pathvalidate, feedparser, yt-dlp, bgutil-ytdlp-pot-provider). `Pipfile.lock` left for a separate `pipenv lock` run (out of scope for this code-only commit).
- [x] **33** `RateLimitError` deleted from `exceptions.py`.
- [x] **34** `VideoListPage.timings` field + 6 perf_counter blocks removed from `page_loader.py`; `VideoListPage` now carries only `items`.
- [x] **35** Duplicate `site_cookies_dependencies.py` deleted; 2 callers re-pointed at `sites_dependencies.py`.
- [x] **36** `CookieCloudSyncTask` redundant class attrs removed.
- [~] **(write-only producer)** DEFERRED — functional decision (was the subscribe-queue ever meant to be consumed?). Documented above; needs product input before the producer + its 2 call sites + `MqMessage` codec are pulled.

**Round-2 net: ~-50 lines, -5 dependencies** (jinja2, pathvalidate, feedparser, yt-dlp, bgutil-ytdlp-pot-provider). Cumulative since round 1: ~-600 lines, -6 deps (round-1 `python-redis-lock` + round-2's five).

