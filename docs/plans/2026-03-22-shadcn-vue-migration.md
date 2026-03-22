# Shadcn-vue Migration + Sync Center UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `squirrel-frontend` 安装 `shadcn-vue`，将全站主题 token 切到 shadcn contract，并把“同步中心”改造成 shadcn 风格 UI；同时移除旧 `src/components/common/*`，不保留兼容导出、不做套壳。

**Architecture:** shadcn-vue 组件本地生成到 `src/components/ui/*`，业务页面直接依赖这些组件。主题通过 `src/styles/index.css` 的 shadcn CSS variables 驱动，`tailwind.config.ts` 映射到 `bg-background` / `text-foreground` / `border-border` 等语义类。

**Tech Stack:** Vue 3 + Vite + TailwindCSS + shadcn-vue (radix-vue) + TypeScript

---

## Task 0: Create A Dedicated Worktree (Recommended)

**Files:**
- None

**Step 1: Create worktree**

Run (from repo root):
```powershell
git worktree add .worktrees/shadcn-vue-migrate -b feat/shadcn-vue-migrate
```

Expected:
- New directory `.worktrees/shadcn-vue-migrate` exists
- `git branch --show-current` prints `feat/shadcn-vue-migrate` when you `cd` into it

**Step 2: Enter worktree**

Run:
```powershell
cd .worktrees/shadcn-vue-migrate
```

**Step 3: Baseline verify (before changes)**

Run:
```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

Expected: both commands exit with code 0.

**Step 4: Commit nothing**

No commit; this is just baseline evidence.

---

## Task 1: Initialize shadcn-vue

**Files:**
- Create: `squirrel-frontend/components.json` (expected)
- Create: `squirrel-frontend/src/lib/utils.ts` (expected)
- Modify: `squirrel-frontend/tailwind.config.ts` (expected)
- Modify: `squirrel-frontend/src/styles/index.css` (expected)

**Step 1: Ensure dependencies are in place**

Run:
```powershell
cd squirrel-frontend
npm install
```

Expected: `node_modules` present; `npm` exits 0.

**Step 2: Run shadcn-vue init**

Run:
```powershell
cd squirrel-frontend
npx shadcn-vue@latest init
```

When prompted, use these choices (adjust only if CLI wording differs):
- Framework: `Vite`
- TypeScript: `Yes`
- Tailwind config: `tailwind.config.ts`
- Global CSS file: `src/styles/index.css`
- Components directory: `src/components`
- UI directory: `src/components/ui`
- Utils directory: `src/lib`
- Import alias: `@`
- CSS variables: `Yes`
- Base color: `Neutral` (or closest)
- Style: `New York` (or closest)

Expected:
- `components.json` created at `squirrel-frontend/components.json`
- `src/lib/utils.ts` created

**Step 3: Add animation plugin dependency (if init did not)**

Run:
```powershell
cd squirrel-frontend
npm install -D tailwindcss-animate
```

Expected: `tailwindcss-animate` appears in `devDependencies`.

**Step 4: Commit**

```powershell
git add squirrel-frontend/components.json squirrel-frontend/src/lib/utils.ts squirrel-frontend/package.json squirrel-frontend/package-lock.json
git commit -m "feat(frontend): init shadcn-vue"
```

---

## Task 2: Switch Theme Tokens To shadcn Contract (Dark Default)

**Files:**
- Modify: `squirrel-frontend/index.html`
- Modify: `squirrel-frontend/src/styles/index.css`

**Step 1: Set dark mode as default**

Modify: `squirrel-frontend/index.html`
- Change `<html lang="en">` to `<html lang="en" class="dark">`.

**Step 2: Replace token block in global CSS**

Modify: `squirrel-frontend/src/styles/index.css`
- Keep `@tailwind ...` and the non-token base rules (mobile tap highlight, scrollbars, focus ring) but replace the token variables under `:root` with shadcn variables.

Minimal token scaffold (example; tune exact HSL values during implementation):
```css
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;

    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;

    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;

    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;

    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;

    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;

    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;

    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;

    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;

    --radius: 0.75rem;
  }

  .dark {
    --background: 0 0% 7%;
    --foreground: 210 40% 98%;

    --card: 0 0% 10%;
    --card-foreground: 210 40% 98%;

    --popover: 0 0% 10%;
    --popover-foreground: 210 40% 98%;

    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;

    --secondary: 0 0% 14%;
    --secondary-foreground: 210 40% 98%;

    --muted: 0 0% 16%;
    --muted-foreground: 215 20.2% 65.1%;

    --accent: 0 0% 16%;
    --accent-foreground: 210 40% 98%;

    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;

    --border: 0 0% 18%;
    --input: 0 0% 18%;
    --ring: 212.7 26.8% 83.9%;
  }
}
```

Also update base `body` defaults:
- `background-color: hsl(var(--background));`
- `color: hsl(var(--foreground));`

**Step 3: Run typecheck/build**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

Expected: both commands exit 0 (UI may look broken at this step; build must pass).

**Step 4: Commit**

```powershell
git add squirrel-frontend/index.html squirrel-frontend/src/styles/index.css
git commit -m "feat(frontend): switch theme tokens to shadcn contract"
```

---

## Task 3: Update Tailwind Config To shadcn Conventions

**Files:**
- Modify: `squirrel-frontend/tailwind.config.ts`

**Step 1: Replace custom color names**

Modify `tailwind.config.ts`:
- Remove the current `colors` entries for `bg-*`, `text-*`, `color-*`, `border-*`, `overlay-*`.
- Add shadcn color mapping:
  - `background`, `foreground`
  - `card`, `popover`
  - `primary`, `secondary`, `muted`, `accent`, `destructive`
  - `border`, `input`, `ring`

Example (shape only, exact object should follow shadcn template):
```ts
colors: {
  background: "hsl(var(--background))",
  foreground: "hsl(var(--foreground))",
  card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
  popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
  primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
  secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
  muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
  accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
  destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
  border: "hsl(var(--border))",
  input: "hsl(var(--input))",
  ring: "hsl(var(--ring))",
}
```

**Step 2: Remove legacy Tailwind plugin utilities that encode old tokens**

- The current `plugins` section injects `.btn-*` and `.input-*` component classes referencing old token names.
- Before removing, search for usages:
```powershell
cd squirrel-frontend
rg -n "\\.btn-(base|xs|sm|md|lg|pill)|\\.input-(base|sm|md|lg)" src
```
- If no usages: delete those plugin definitions.
- If there are usages: replace those usages with shadcn components or Tailwind classes (no shims).

**Step 3: Add `tailwindcss-animate` plugin**

- Ensure `tailwindcss-animate` is included in Tailwind plugins (per shadcn template).

**Step 4: Verify**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

**Step 5: Commit**

```powershell
git add squirrel-frontend/tailwind.config.ts
git commit -m "chore(frontend): align tailwind config with shadcn tokens"
```

---

## Task 4: Add Required shadcn UI Components

**Files:**
- Create: `squirrel-frontend/src/components/ui/*` (multiple)

**Step 1: Add baseline primitives**

Run (adjust component names to what CLI supports):
```powershell
cd squirrel-frontend
npx shadcn-vue@latest add button card badge alert input textarea separator table tabs switch tooltip sheet dialog dropdown-menu popover command
```

Expected:
- `src/components/ui/` contains the generated components
- No TypeScript errors introduced

**Step 2: Verify**

```powershell
npm run typecheck
```

**Step 3: Commit**

```powershell
git add squirrel-frontend/src/components/ui squirrel-frontend/package.json squirrel-frontend/package-lock.json
git commit -m "feat(frontend): add shadcn ui primitives"
```

---

## Task 5: Migrate Sync Center Components To shadcn UI

**Files:**
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncControlBar.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncSignalMatrix.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncRunHistoryPanel.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncRunDetailDrawer.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncEventTimeline.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncSubscriptionSelect.vue`

**Step 1: Replace imports away from `@/components/common`**

- Convert to `@/components/ui/*` imports.

**Step 2: Control bar**

- Lens switch: implement with `Tabs` (3 tabs: now/24h/7d) or `ToggleGroup`.
- Auto refresh: use `Switch` with `@update:checked` (or `v-model:checked`) and emit boolean.
- Action buttons: shadcn `Button` variants:
  - refresh: `secondary`
  - retry: `default` or `destructive` only if semantics demand
  - reconcile: `outline`/`ghost`
- Summary and updated-at: `Badge` + `Separator` as needed.

**Step 3: Drawer -> Sheet**

- Replace `Teleport` overlay with shadcn `Sheet`.
- Keep click-outside close and close button.
- Ensure keyboard escape works (radix default).

**Step 4: Run history table**

- Replace raw `<table>` with shadcn `Table` primitives.
- Filter section: `Select` + `Input` aligned; keep existing filter emit logic.

**Step 5: Subscription select -> Combobox**

- Replace custom dropdown with shadcn `Popover` + `Command` based combobox.
- Must support:
  - search
  - select "all" option
  - keyboard navigation
  - avatar rendering

**Step 6: Verify**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

**Step 7: Commit**

```powershell
git add squirrel-frontend/src/views/SyncCenter.vue squirrel-frontend/src/components/sync-center
git commit -m "refactor(frontend): migrate sync center ui to shadcn components"
```

---

## Task 6: Migrate Remaining Pages Off `src/components/common/*` (No Shims)

**Files:**
- Modify (from current usages):
  - `squirrel-frontend/src/views/LatestVideos.vue`
  - `squirrel-frontend/src/views/LogViewer.vue`
  - `squirrel-frontend/src/views/PluginManager.vue`
  - `squirrel-frontend/src/views/Monitoring.vue`
  - `squirrel-frontend/src/views/ScheduledTasks.vue`
  - `squirrel-frontend/src/views/Settings.vue`
  - `squirrel-frontend/src/views/Subscribed.vue`
  - `squirrel-frontend/src/components/dialogs/ImportSubscriptionDialog.vue`
  - `squirrel-frontend/src/components/dialogs/AddChannelDialog.vue`
  - `squirrel-frontend/src/components/settings/SiteConfigSection.vue`
  - `squirrel-frontend/src/components/settings/SiteConfigEditorDialog.vue`
  - `squirrel-frontend/src/components/layout/SidebarMenuItem.vue`

**Step 1: Replace imports**

- Remove `import { ... } from '@/components/common'`.
- Use direct imports from `@/components/ui/*`.

**Step 2: Replace legacy components usage**

- `InlineAlert` -> `Alert` (variant mapping: success/warning/error -> default/destructive + styling)
- `ToggleSwitch` -> `Switch`
- `StatusBadge` -> `Badge`
- `StatsCard` -> inline `Card` layout (no wrapper; avoid reintroducing a "common" layer)
- `DataTable` -> use shadcn `Table` in place

**Step 3: Verify**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

**Step 4: Commit**

```powershell
git add squirrel-frontend/src/views squirrel-frontend/src/components
git commit -m "refactor(frontend): remove legacy common components usage"
```

---

## Task 7: Remove Legacy `src/components/common/*` And Update Any Stragglers

**Files:**
- Delete: `squirrel-frontend/src/components/common/*`
- Delete: `squirrel-frontend/src/components/common/index.ts`

**Step 1: Ensure no remaining imports**

Run:
```powershell
cd squirrel-frontend
rg -n "from '@/components/common'|@/components/common" src
```

Expected: no matches.

**Step 2: Delete legacy directory**

Run:
```powershell
git rm -r squirrel-frontend/src/components/common
```

**Step 3: Verify**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

**Step 4: Commit**

```powershell
git commit -m "chore(frontend): remove legacy common components"
```

---

## Task 8: Migrate Legacy Tailwind Class Names To shadcn Class Names

Background:
- Current codebase heavily uses `bg-bg-*`, `text-text-*`, `border-border-*`, `text-color-*` etc.
- After tailwind config switch, these classes will break.

**Files:**
- Modify: multiple `squirrel-frontend/src/**/*.{vue,js,ts,css}`

**Step 1: Inventory counts**

Run:
```powershell
cd squirrel-frontend
(rg -n "bg-bg-" src | measure-object -Line).Lines
(rg -n "text-text-" src | measure-object -Line).Lines
(rg -n "border-border-" src | measure-object -Line).Lines
(rg -n "text-color-|bg-color-" src | measure-object -Line).Lines
```

**Step 2: Implement a codemod (recommended)**

Create: `squirrel-frontend/scripts/migrate-tokens.mjs`
- Read all files under `src` with extensions `.vue/.ts/.js/.css`
- Apply deterministic replacements for the most common classnames, for example:
  - `bg-bg-primary` -> `bg-background`
  - `text-text-primary` -> `text-foreground`
  - `text-text-muted` -> `text-muted-foreground`
  - `border-border-primary` -> `border-border`
  - `bg-bg-secondary` / `bg-bg-card` -> `bg-card`
  - `bg-bg-tertiary` / `bg-bg-elevated` -> `bg-muted` (then manually fix exceptions)
  - `text-color-error` -> `text-destructive`
  - `bg-color-primary` -> `bg-primary`
  - `bg-color-error` -> `bg-destructive`

Then run:
```powershell
node squirrel-frontend/scripts/migrate-tokens.mjs
```

Expected:
- Many files modified
- No runtime logic changes (string replacements only)

**Step 3: Manual fix pass**

Run:
```powershell
cd squirrel-frontend
rg -n "bg-bg-|text-text-|border-border-|text-color-|bg-color-" src
```

Expected: remaining matches are reviewed and fixed manually.

**Step 4: Verify + Commit**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check

git add squirrel-frontend/src squirrel-frontend/scripts/migrate-tokens.mjs
git commit -m "refactor(frontend): migrate legacy tailwind token classes to shadcn"
```

---

## Task 9: Final Verification (Manual)

**Step 1: Run dev**

```powershell
cd squirrel-frontend
npm run dev
```

**Step 2: Manual checklist**

- `/sync-center`:
  - lens 切换正常触发数据刷新
  - 自动刷新开关可用
  - 运行历史筛选、分页可用
  - 打开 run 详情为 Sheet，事件时间线可滚动
- `/settings`、`/subscribed`、`/scheduled-tasks`、`/monitoring` 基本可用（无明显错位/不可读）

**Step 3: Final commit (optional)**

If any small fixes:
```powershell
git add -A
git commit -m "fix(frontend): ui polish after shadcn migration"
```

