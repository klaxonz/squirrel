---
title: Site runtime local attribute loader imports crawl package
status: fixed
severity: high
category: runtime
locations:
  - squirrel-sdk/src/crawl/runtime_helpers.py
  - squirrel-site-runtimes/tests/test_sdk_shared_helpers.py
source: manual
fixed_by: designs/des-fix-issue-007-runtime-local-attr-imports-crawl-package.md
---

# Site runtime local attribute loader imports crawl package

## Phenomenon

Subscription sync for YouTube fails after the worker reaches the site runtime invocation path.

## Reproduction Evidence

Runtime state for `sync_state_id=1545` shows the latest real sync failure:

```text
No module named 'crawl.subscription'
```

The earlier `Failed to claim sync state` errors were stale retry attempts from an older crawl task whose queue token no longer matched the sync state.

## Current Findings

- Site runtimes call `crawl.load_local_attr("subscription", "...")` from runtime module lambdas.
- `crawl.load_local_attr()` builds imports from the SDK package name, so it attempts `crawl.subscription`.
- The local runtime modules live under plugin packages such as `squirrel_youtube.subscription`.
- No `crawl.subscription` module exists in the SDK.

## Impact

Runtime V2 subscription sync cannot load plugin-local subscription implementations, so subscription sync tasks fail before fetching videos.

## Fix Attempts

- Updated `crawl.load_local_attr()` to import sibling modules from the caller package instead of the SDK `crawl` package.
- Added a regression test with a synthetic runtime package that loads its own `subscription` sibling module.
- Verified the current virtualenv imports `crawl` from `squirrel-sdk/src/crawl`, so the fix is picked up by local runtime processes after restart.
