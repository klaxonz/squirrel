---
type: fix
name: issue-018
status: implemented
related_requirement:
related_issue: issues/issue-018-unused-backend-code.md
---

# Fix Design: Remove unused backend modules

## Root Cause

Earlier refactors left modules behind after implementations moved elsewhere. The package exports remained, so the files still looked like supported APIs even though no backend code imports them.

## Fix Approach

1. Delete unused split music modules that are not imported by `services.music`, routes, or tests.
2. Delete unused raw video SQL helpers and remove them from `sql.__all__`.
3. Delete unused repository base package.
4. Delete unused queue duplicate checker and remove it from `queues.__all__`.
5. Run backend lint and focused tests for the touched packages.

## Files

- `squirrel-backend/services/music/*.py`: remove unused split modules while keeping `__init__.py`, `_client.py`, and `_normalizers.py`.
- `squirrel-backend/sql/__init__.py`: stop exporting deleted `video_sql`.
- `squirrel-backend/sql/video_sql.py`: delete unused raw SQL helpers.
- `squirrel-backend/core/repository/*`: delete unused repository base.
- `squirrel-backend/queues/__init__.py`: stop exporting duplicate checker symbols.
- `squirrel-backend/queues/duplicate_checker.py`: delete unused duplicate checker.

## Risks

External code importing backend internals could break, but the repository has no such call sites and backend internals are not treated as a public API.

## Verification Results

Verification: lint Y  type-check SKIP  test Y  manual SKIP

- Reference check: `rg` found no remaining references to deleted modules or symbols.
- Lint: `pipenv run ruff check queues sql services/music` passed.
- Test: `pipenv run pytest tests/services/test_music_service.py tests/queues/test_consumer.py tests/services/test_subscription_service.py` passed with `97 passed`.
