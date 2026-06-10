---
type: fix
name: issue-005
status: implemented
related_requirement:
related_issue: issues/issue-005-subscription-outbox-site-resolution.md
---

# Fix Design: subscription outbox site resolution failure

## Root Cause

The subscription update layer depends on a private resolver attribute on `subscription_sync_state_service`, but that service no longer exposes `_resolve_site`. Tests patched the missing attribute with `create=True`, so the production `AttributeError` was not covered.

## Fix Approach

1. Import `resolve_site` from `utils.url_helper` in the subscription update modules that need URL-to-site metadata.
2. Replace calls to `subscription_sync_state_service._resolve_site()` with the direct resolver call.
3. Update focused tests to patch or exercise the real resolver import instead of creating a missing service attribute.

## Files

- `squirrel-backend/services/subscription_update/scheduler.py`: use `utils.url_helper.resolve_site` for scheduler site resolution.
- `squirrel-backend/services/subscription_update/strategies/base.py`: use the direct resolver when appending request events.
- `squirrel-backend/services/subscription_update/strategies/default_strategy.py`: use the direct resolver for enqueue metrics and events.
- `squirrel-backend/tests/services/test_outbox_event_service.py`: stop monkeypatching the missing service attribute.
- `squirrel-backend/tests/services/test_subscription_update_scheduler.py`: stop monkeypatching the missing service attribute in scheduler tests.
- `squirrel-backend/tests/services/test_subscription_update_strategy.py`: patch the direct resolver where tests need deterministic site labels.

## Risks

The behavior remains the same for valid URLs because the code uses the existing resolver. The main risk is test setup drift around URL-derived site labels.

## Similar Issues

Search found the same missing `_resolve_site` dependency in scheduler and subscription update strategy modules only. Other `_resolve_site` names are local methods for unrelated services or icon helpers.

## Verification Results

Verification: lint Y  type-check SKIP  test Y  manual Y

- Lint: `pipenv run ruff check services/subscription_update/scheduler.py services/subscription_update/strategies/base.py services/subscription_update/strategies/default_strategy.py tests/services/test_outbox_event_service.py tests/services/test_subscription_update_scheduler.py tests/services/test_subscription_update_strategy.py` passed.
- Test: `pipenv run pytest tests/services/test_outbox_event_service.py tests/services/test_subscription_update_scheduler.py tests/services/test_subscription_update_strategy.py` passed with `24 passed`.
- Manual: `rg _resolve_site` confirms subscription update production code no longer calls the missing service attribute; only `orchestrator.py` keeps its unrelated local `_resolve_site` method.
