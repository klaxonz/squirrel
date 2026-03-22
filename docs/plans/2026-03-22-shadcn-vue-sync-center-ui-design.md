# shadcn-vue + Sync Center UI Migration Design

Date: 2026-03-22
Owner: repo agents
Scope: `squirrel-frontend`

## 1. Goal

- Install `shadcn-vue` in `squirrel-frontend` and migrate the UI system to shadcn-style components.
- Replace the existing custom design tokens (`--bg-*`, `--text-*`, etc.) with shadcn theme tokens (`--background`, `--foreground`, ...).
- Refactor "Sync Center" (`/sync-center`) to use shadcn-vue primitives and patterns (Sheet/Table/Tabs, etc.).
- Remove legacy `src/components/common/*` usage; no compatibility exports, no wrapper/shim layers.

## 2. Non-goals

- No backend API changes.
- No behavior changes to data flow and business logic in composables (`useSyncCenter`, `useSyncHistory`, `useSyncTrends`), except what is required by UI refactors.
- No attempt to keep old token names or old component import paths working.
- No global light/dark toggle UI in this iteration (but tokens will support it structurally).

## 3. Current State (Observed)

- Frontend uses Tailwind with a custom token system defined in `src/styles/index.css`:
  - `--bg-primary/--text-primary/...` and Tailwind colors like `bg-bg-primary`, `text-text-muted`, `border-border-primary`.
- UI components are centralized under `src/components/common/*` with an index barrel `src/components/common/index.ts`.
- Sync Center is implemented at:
  - `src/views/SyncCenter.vue`
  - `src/components/sync-center/*`
  - It already has a modern layout (toolbar + signal matrix + run history + detail drawer).

## 4. Approach Options

### Option A: Full Migration (Recommended)

- Switch theme tokens to shadcn tokens globally.
- Generate shadcn-vue local components under `src/components/ui/*`.
- Replace all usages of `src/components/common/*` with shadcn-vue `src/components/ui/*` imports across the app.
- Remove `src/components/common/*` (or at minimum remove all imports and stop exporting them).

Pros:
- Clean architecture, minimal long-term maintenance cost.
- Aligns with "no compatibility layer" requirement.

Cons:
- Large diff; requires careful verification.

### Option B: Partial Migration

- Only migrate Sync Center to shadcn components while leaving other pages on the legacy token system.

Rejected because:
- Token systems conflict.
- Without shims, the app will fragment and incur debt quickly.

## 5. Detailed Design

### 5.1 Dependencies and shadcn-vue Setup

- Run `shadcn-vue` init in `squirrel-frontend` (Vue 3 + Vite).
- Components generated locally to `squirrel-frontend/src/components/ui/`.
- Add `src/lib/utils.ts` with `cn()` helper (tailwind-merge + clsx).

Notes:
- This repository uses Tailwind already; shadcn-vue will extend config, not replace build tooling.

### 5.2 Theme Tokens: Switch to shadcn Token Contract

#### CSS variables

- Update `squirrel-frontend/src/styles/index.css`:
  - Replace `--bg-*`, `--text-*`, `--color-*`, `--border-*`, `--radius-*`, etc. with shadcn variables.
  - Provide both `:root` (light) and `.dark` (dark) blocks, but default the app to dark mode.

Default theme behavior:
- Set `<html class="dark">` in `squirrel-frontend/index.html`.

Token list (baseline):
- `--background`, `--foreground`
- `--card`, `--card-foreground`
- `--popover`, `--popover-foreground`
- `--primary`, `--primary-foreground`
- `--secondary`, `--secondary-foreground`
- `--muted`, `--muted-foreground`
- `--accent`, `--accent-foreground`
- `--destructive`, `--destructive-foreground`
- `--border`, `--input`, `--ring`
- `--radius`

#### Tailwind mapping

- Update `squirrel-frontend/tailwind.config.ts` to shadcn conventions:
  - `colors.background`, `colors.foreground`, `colors.primary`, `colors.muted`, `colors.border`, etc.
  - Add `tailwindcss-animate` plugin if used by shadcn components.
  - Keep existing `content` globs.

### 5.3 Component Migration (No Shims)

Rules:
- Do not maintain `@/components/common` as an alias or compatibility export.
- Replace imports across the app to point to `@/components/ui/*` (shadcn components).
- Remove usage of legacy components.

Mapping guidance:
- `Button.vue` -> `ui/button`
- `Card.vue` -> `ui/card`
- `Input.vue`, `Textarea.vue` -> `ui/input`, `ui/textarea`
- `Select.vue` -> `ui/select` (or `ui/combobox`/`ui/select` depending on shadcn-vue supported component set)
- `Tooltip.vue` -> `ui/tooltip`
- `ToggleSwitch.vue` -> `ui/switch`
- `StatusBadge.vue` -> `ui/badge` + semantic variants
- `InlineAlert.vue` -> `ui/alert`
- `DataTable.vue` -> `ui/table` (and/or a local composition around Table primitives, but still using shadcn UI building blocks, not an adapter to old API)

### 5.4 Sync Center UI Refactor

Goal: keep logic the same; improve layout consistency and accessibility with shadcn primitives.

Targets:
- `src/components/sync-center/SyncControlBar.vue`
  - Use `Tabs` or `ToggleGroup` for lens options.
  - Use `Switch` for auto-refresh.
  - Use `Button` for actions.
  - Use `Badge` for summary and updated-at chips.

- `src/components/sync-center/SyncSignalMatrix.vue`
  - Use `Card` and shadcn typography spacing.
  - Use semantic colors:
    - error -> `destructive`
    - warning -> `warning` (if implemented) or `accent` + custom token
    - info -> `primary`/`ring`
    - success -> add `--success` token only if required; prefer sticking to shadcn baseline where possible.

- `src/components/sync-center/SyncRunHistoryPanel.vue`
  - Replace `<table>` styling with `ui/table`.
  - Filters: use `Select`, `Input`, and `Popover` if needed.
  - Keep current behavior (filter debounce is in parent view).

- `src/components/sync-center/SyncRunDetailDrawer.vue`
  - Replace Teleport + custom transition with shadcn `Sheet` component.
  - Preserve open/close semantics and content structure.

Note:
- `SyncSubscriptionSelect.vue` is currently a custom searchable dropdown.
  - It should be migrated to shadcn `Combobox` (Popover + Command) for consistency and keyboard support.

## 6. Risks and Mitigations

- Risk: global token swap breaks existing pages.
  - Mitigation: migrate common components and key views in the same change set; run `npm run typecheck` and `npm run build:check`.

- Risk: shadcn-vue component set mismatch (Select/Combobox differences).
  - Mitigation: use shadcn recommended primitives for Vue (`radix-vue` based) and implement missing UX using the same primitives (Popover + Command) rather than legacy components.

- Risk: dark theme readability regressions.
  - Mitigation: keep base typography and spacing consistent; verify major pages (`/`, `/subscribed`, `/sync-center`, `/settings`, `/scheduled-tasks`, `/monitoring`).

## 7. Verification

From `squirrel-frontend`:

- `npm run typecheck`
- `npm run build:check`
- (Optional) `npm run dev` and manual sanity check of key routes:
  - `/sync-center`
  - `/subscribed`
  - `/settings`
  - `/scheduled-tasks`
  - `/monitoring`

## 8. Rollout Plan

- Single PR-style change (preferred) to avoid long-lived half-migration state.
- After migration, delete unused legacy files under `src/components/common/*` and remove imports.

