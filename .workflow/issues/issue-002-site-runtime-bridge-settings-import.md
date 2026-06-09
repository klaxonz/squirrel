---
title: Site runtime bridge imports backend settings before startup
status: fixed
severity: high
category: startup
locations:
  - squirrel-backend/site_runtimes/__init__.py
source: manual
fixed_by: designs/des-fix-issue-002-site-runtime-bridge-settings-import.md
---

# Site runtime bridge imports backend settings before startup

## Phenomenon

Backend startup reaches site runtime bootstrap, then fails because a runtime subprocess exits before becoming healthy:

```text
SiteRuntimeSupervisorError: Site runtime exited before becoming healthy
```

Runtime stderr shows the subprocess fails while executing `python -m site_runtimes.runtime_bridge`:

```text
pydantic_core._pydantic_core.ValidationError: 2 validation errors for Settings
POSTGRES_PASSWORD
JWT_SECRET_KEY
```

## Impact

The backend exits during application startup before it can serve requests.

## Reproduction

Start the backend with enabled workspace site runtimes.

## Fix Attempts

- Removed eager backend manager/settings imports from `site_runtimes/__init__.py`.
