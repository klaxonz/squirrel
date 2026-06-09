---
type: fix
name: issue-001
status: implemented
related_requirement:
related_issue: issues/issue-001-auth-middleware-import.md
---

# Fix Design: auth middleware import prevents backend startup

## Root Cause

The authentication middleware class is defined as `AuthenticationMiddleware`, but the app factory and its focused middleware test still import and register the stale name `AuthMiddleware`. The import is evaluated during application creation, so the backend exits before startup completes.

## Fix Approach

Use the existing `AuthenticationMiddleware` class name at the app registration site and in the focused middleware test. Do not add an alias or fallback name because this project forbids compatibility and patch code.

## Files

- `squirrel-backend/routes/base.py`: import and register `AuthenticationMiddleware`.
- `squirrel-backend/tests/routes/test_auth_cookie_middleware.py`: import and register `AuthenticationMiddleware` in the test app.

## Risks

Low. The middleware implementation and behavior stay unchanged; only stale references are corrected.

## Similar Issues

`rg` found the stale `AuthMiddleware` reference only in the app factory and the focused auth-cookie middleware test.

## Verification Results

Verification: lint Y  type-check SKIP  test Y  manual Y

- Lint: `pipenv run ruff check routes/base.py tests/routes/test_auth_cookie_middleware.py` passed.
- Test: `pipenv run pytest tests/routes/test_auth_cookie_middleware.py tests/routes/test_auth_middleware.py` passed.
- Manual: with temporary process env `ENV=dev` and `JWT_SECRET_KEY=test-secret-for-import-validation`, `from main import create_application; app = create_application()` returned a `FastAPI` app with 194 routes.
