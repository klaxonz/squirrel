# Sync Control Bar Size Consistency Design

## Goal

Unify the visual size and proportions of the action controls in the sync center header so the time tabs, auto-refresh toggle, action buttons, and timestamp pill read as a single control group.

## Scope

- Modify `squirrel-frontend/src/components/sync-center/SyncControlBar.vue`.
- Keep behavior, copy, and layout order unchanged.
- Do not change shared UI primitives globally.

## Approach

Use a local sizing system inside the sync control bar:

- Standardize the action row to a single control height.
- Align text size and horizontal padding across tabs, buttons, toggle label, and timestamp.
- Leave the summary badge and main title logic untouched.

## Verification

- Run `npm run build:check` in `squirrel-frontend`.
- Visually confirm the right-side controls no longer appear mixed in height.
