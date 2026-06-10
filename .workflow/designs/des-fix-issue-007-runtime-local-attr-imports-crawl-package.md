---
type: fix
name: issue-007
status: implemented
related_requirement:
related_issue: issues/issue-007-runtime-local-attr-imports-crawl-package.md
---

# Fix Design: runtime local attribute loader imports crawl package

## Root Cause

The shared SDK helper `load_local_attr()` uses the SDK package name when composing a sibling module import. Because the helper is exported from `crawl`, all plugin runtime calls resolve to `crawl.<module>` instead of the caller's plugin package.

## Fix Approach

1. Resolve the caller module package from the Python frame that invoked `load_local_attr()`.
2. Import the requested sibling module from that caller package.
3. Add a regression test with a synthetic plugin package that imports `load_local_attr` from `crawl` and loads its own sibling module.

## Files

- `squirrel-sdk/src/crawl/runtime_helpers.py`: resolve sibling imports relative to the caller package.
- `squirrel-site-runtimes/tests/test_sdk_shared_helpers.py`: cover plugin-local sibling imports.

## Risks

The helper is only used by site runtime packages for plugin-local modules. Existing runtime calls all pass simple sibling module names.

## Similar Issues

All current site runtime packages use this helper for local `auth`, `importer`, `subscription`, `extractor`, `proxy`, or `subtitles` modules, so one SDK fix covers all affected runtimes.

## Verification Results

Verification: lint Y  type-check SKIP  test Y  manual Y

- Lint: `pipenv run ruff check ..\squirrel-sdk\src\crawl\runtime_helpers.py ..\squirrel-site-runtimes\tests\test_sdk_shared_helpers.py tests/processes/test_crawl_worker_runtime.py` passed.
- Test: `pipenv run pytest ..\squirrel-site-runtimes\tests\test_sdk_shared_helpers.py tests/services/test_crawl_executors.py tests/processes/test_crawl_worker_runtime.py` passed with `24 passed`.
- Manual: `ENV=dev pipenv run python -c "import crawl; import crawl.runtime_helpers as rh; print(crawl.__file__); print(rh.__file__)"` confirms the worker environment imports the SDK from `D:\Code\init\squirrel\squirrel-sdk\src\crawl`.
