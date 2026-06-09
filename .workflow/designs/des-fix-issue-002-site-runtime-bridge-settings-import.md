---
type: fix
name: issue-002
status: implemented
related_requirement:
related_issue: issues/issue-002-site-runtime-bridge-settings-import.md
---

# Fix Design: site runtime bridge imports backend settings before startup

## Root Cause

Running `python -m site_runtimes.runtime_bridge` executes `site_runtimes/__init__.py` before the bridge module. The package initializer eagerly imports `manager` and `paths`, which imports `core.config.settings`. Runtime subprocesses intentionally receive a narrow environment, so backend-only settings such as `ENV` and `JWT_SECRET_KEY` are absent and settings validation fails before the bridge can start.

## Fix Approach

Make `site_runtimes/__init__.py` side-effect free. Backend code already imports concrete modules such as `site_runtimes.manager`, `site_runtimes.gateway`, and `site_runtimes.runtime_bridge`, so package initialization does not need to re-export manager/store/supervisor symbols.

## Files

- `squirrel-backend/site_runtimes/__init__.py`: remove eager imports that initialize backend settings during package import.

## Risks

Low inside this repo. `rg` found backend code imports concrete `site_runtimes.*` modules; the only package-level import is `from site_runtimes import runtime_bridge`, which Python supports without package-level re-exports.

## Similar Issues

No other package initializer in this startup path was found importing backend settings before the runtime bridge starts.

## Verification Results

Verification: lint Y  type-check SKIP  test Y  manual Y

- Lint: `pipenv run ruff check site_runtimes/__init__.py site_runtimes/supervisor.py tests/site_runtimes/test_supervisor.py` passed.
- Test: `pipenv run pytest tests/site_runtimes/test_supervisor.py tests/test_app_runtime_bootstrap.py -q` passed.
- Manual: with temporary process env `ENV=dev` and `JWT_SECRET_KEY=test-secret-for-runtime-bootstrap-validation`, `bootstrap_site_runtimes()` started `['bilibili', 'javdb', 'pornhub', 'youporn', 'youtube']`, then `shutdown_site_runtimes()` completed.
