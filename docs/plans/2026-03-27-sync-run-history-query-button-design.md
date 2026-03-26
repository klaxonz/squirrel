# Sync Run History Query Button Design

## Goal

Add an explicit query button to the sync run history filter bar and switch filtering from auto-fetch to manual submit.

## Scope

- `squirrel-frontend/src/components/sync-center/SyncRunHistoryPanel.vue`
- `squirrel-frontend/src/components/sync-center/SyncAnalysisWorkspace.vue`
- `squirrel-frontend/src/views/SyncCenter.vue`

## Approach

- Keep the visible filters unchanged.
- Add a `查询` button beside the date range control.
- Store edits in a local draft state inside the run history panel.
- Submit the whole draft only when the user clicks `查询`.
- Keep parent-driven filter changes and pagination behavior intact.

## Verification

- Run `npm run build:check` in `squirrel-frontend`.
- Confirm changing filters does not fetch immediately.
- Confirm clicking `查询` applies current draft filters and reloads the list.
