---
title: Auth middleware import prevents backend startup
status: fixed
severity: high
category: startup
locations:
  - squirrel-backend/routes/base.py
  - squirrel-backend/tests/routes/test_auth_cookie_middleware.py
source: manual
fixed_by: designs/des-fix-issue-001-auth-middleware-import.md
---

# Auth middleware import prevents backend startup

## Phenomenon

Starting `squirrel-backend/main.py` fails during FastAPI application creation:

```text
ImportError: cannot import name 'AuthMiddleware' from 'routes.middleware.auth'
```

## Impact

The backend process exits before Uvicorn can serve requests.

## Reproduction

Run:

```bash
C:\Users\klaxon\.virtualenvs\squirrel-backend-KHpoIo2r\Scripts\python.exe D:\Code\init\squirrel\squirrel-backend\main.py
```

## Fix Attempts

- Fixed stale `AuthMiddleware` references to use the existing `AuthenticationMiddleware` class.
