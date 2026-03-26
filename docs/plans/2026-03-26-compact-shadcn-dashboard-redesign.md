# Compact Shadcn Dashboard Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign `squirrel-frontend` into a compact `shadcn-vue` dashboard that unifies shell, content pages, system pages, and auth surfaces without changing core route and data behavior.

**Architecture:** Start by normalizing shared tokens and compact sizing rules, then rebuild the shell so every route inherits one dashboard contract. After the shell is stable, move route groups onto the same page-header, toolbar, dialog, and table/list semantics, preserving existing business logic and route structure unless minor structural UI changes are needed for clarity.

**Tech Stack:** Vue 3 + Vite + TailwindCSS + shadcn-vue + Vue Router + Pinia + TypeScript

---

## Task 0: Capture Baseline Frontend State

**Files:**
- None

**Step 1: Enter the frontend directory**

```powershell
cd D:\Code\init\squirrel\squirrel-frontend
```

**Step 2: Install dependencies if needed**

```powershell
npm install
```

Expected: command exits with code 0.

**Step 3: Run baseline verification**

```powershell
npm run typecheck
npm run build
```

Expected: both commands exit with code 0.

**Step 4: Record baseline notes**

Capture current screenshots or notes for:

- `/videos/all`
- `/subscribed`
- `/history`
- `/video/:id`
- `/sync-center`
- `/monitoring`
- `/settings`
- `/login`

Expected: there is a clear before-state reference for later verification.

**Step 5: No commit**

This task only captures baseline evidence.

---

## Task 1: Normalize Global Tokens For Compact Density

**Files:**
- Modify: `squirrel-frontend/src/styles/index.css`

**Step 1: Tighten the shared sizing scale**

Update `src/styles/index.css` so global variables bias toward compact surfaces:

```css
:root {
  --sidebar-width: 11rem;
  --sidebar-collapsed-width: 3.75rem;
  --radius: 0.65rem;
  --radius-lg: 0.75rem;
  --radius-xl: 0.875rem;
}
```

Also reduce any layout and component tokens that currently produce oversized controls, wide gutters, or heavy shadows.

**Step 2: Reduce decorative shell styling**

Remove or weaken:

- large radial glows
- thick floating shadows
- oversized shell rounding
- strong glass-like backdrops on routine app surfaces

Keep the background and surface palette neutral and restrained.

**Step 3: Keep semantic color contracts stable**

Do not change the meaning of:

- `--primary`
- `--destructive`
- `--muted`
- `--border`
- `--ring`

Only retune them if needed to align with the approved compact dashboard style.

**Step 4: Run verification**

```powershell
cd D:\Code\init\squirrel\squirrel-frontend
npm run typecheck
npm run build
```

Expected: both commands pass.

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/styles/index.css
git commit -m "refactor(frontend): tighten global dashboard tokens"
```

---

## Task 2: Tighten Shared Primitive Defaults

**Files:**
- Modify: `squirrel-frontend/src/components/ui/button/Button.vue`
- Modify: `squirrel-frontend/src/components/ui/input/Input.vue`
- Modify: `squirrel-frontend/src/components/ui/textarea/Textarea.vue`
- Modify: `squirrel-frontend/src/components/ui/select/SelectTrigger.vue`
- Modify: `squirrel-frontend/src/components/ui/tabs/TabsList.vue`
- Modify: `squirrel-frontend/src/components/ui/tabs/TabsTrigger.vue`
- Modify: `squirrel-frontend/src/components/ui/card/Card.vue`
- Modify: `squirrel-frontend/src/components/ui/badge/Badge.vue`
- Modify: `squirrel-frontend/src/components/ui/table/TableRow.vue`
- Modify: `squirrel-frontend/src/components/ui/dialog/DialogContent.vue`
- Modify: `squirrel-frontend/src/components/ui/sheet/SheetContent.vue`
- Modify: `squirrel-frontend/src/components/ui/dropdown-menu/DropdownMenuContent.vue`

**Step 1: Calibrate default compact sizes**

Adjust shared classes so primitives align to compact dashboard usage:

- default buttons feel close to `sm`
- inputs and selects are shorter
- tabs are tighter and more tool-like
- cards use quieter padding and less rounding
- dropdowns and dialogs are compact and structured

Representative target for a compact trigger:

```ts
'h-8 rounded-md border bg-background px-3 text-sm shadow-sm'
```

**Step 2: Standardize border and focus behavior**

Make sure these primitives share:

- restrained neutral borders
- visible but not oversized focus rings
- consistent hover behavior
- reduced reliance on large shadows

**Step 3: Keep APIs stable**

Do not break imports, exposed props, or variant names already used across the app unless every in-repo caller is updated in the same task.

**Step 4: Run verification**

```powershell
cd D:\Code\init\squirrel\squirrel-frontend
npm run typecheck
npm run build
```

Expected: both commands pass.

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/components/ui
git commit -m "refactor(frontend): compact shared shadcn primitives"
```

---

## Task 3: Rebuild The App Shell Around One Dashboard Contract

**Files:**
- Modify: `squirrel-frontend/src/App.vue`
- Modify: `squirrel-frontend/src/components/layout/Sidebar.vue`
- Modify: `squirrel-frontend/src/components/layout/SidebarMenuItem.vue`
- Modify: `squirrel-frontend/src/components/layout/GlobalSearchBar.vue`
- Modify: `squirrel-frontend/src/components/layout/MobileNav.vue`
- Modify: `squirrel-frontend/src/constants/sidebar.ts`

**Step 1: Replace the decorative shell with a compact dashboard shell**

Update `App.vue` so the app shell uses:

- thinner top bar
- smaller page gutters
- stable content width rules
- cleaner background treatment

Representative structure:

```vue
<div class="app-shell">
  <Sidebar />
  <main class="app-main">
    <header class="page-topbar">
      <GlobalSearchBar />
    </header>
    <section class="page-container">
      <router-view />
    </section>
  </main>
</div>
```

**Step 2: Reorganize navigation groups**

Update `src/constants/sidebar.ts` and related layout components so navigation reflects:

- Content
- Operations
- System

Ensure desktop and mobile navigation use the same grouping logic where practical.

**Step 3: Tighten sidebar and topbar interactions**

Adjust sidebar rows, collapse controls, and topbar actions so they feel compact:

- smaller row heights
- calmer active states
- reduced oversized icon containers
- consistent hover and selected patterns

**Step 4: Preserve current route behavior**

Do not break:

- global search event wiring
- video widescreen sidebar behavior
- mobile navigation routing
- flyout sidebar route states

**Step 5: Verify manually**

Run:

```powershell
cd D:\Code\init\squirrel\squirrel-frontend
npm run dev
```

Check:

- `/videos/all`
- `/subscribed`
- `/settings`
- `/video/:id`

Expected: shell works in fixed, collapsed, flyout, and mobile states.

**Step 6: Run automated verification**

```powershell
npm run typecheck
npm run build
```

Expected: both commands pass.

**Step 7: Commit**

```powershell
git add squirrel-frontend/src/App.vue squirrel-frontend/src/components/layout squirrel-frontend/src/constants/sidebar.ts
git commit -m "feat(frontend): rebuild compact dashboard shell"
```

---

## Task 4: Unify Page Header And Toolbar Patterns

**Files:**
- Modify: `squirrel-frontend/src/components/feed/FeedToolbar.vue`
- Modify: `squirrel-frontend/src/components/feed/TabBar.vue`
- Modify: `squirrel-frontend/src/components/feed/SortButton.vue`
- Modify: `squirrel-frontend/src/components/feed/SiteFilter.vue`
- Modify: `squirrel-frontend/src/components/feed/NsfwFilter.vue`
- Modify: `squirrel-frontend/src/components/feed/RefreshButton.vue`
- Modify: `squirrel-frontend/src/views/LatestVideos.vue`
- Modify: `squirrel-frontend/src/views/Subscribed.vue`
- Modify: `squirrel-frontend/src/views/History.vue`

**Step 1: Define one compact toolbar contract**

The toolbar pattern should support:

- tabs or segmented route filters on the left
- compact filter controls
- refresh and page actions on the right
- wrapping behavior on smaller screens without becoming oversized

Representative structure:

```vue
<section class="page-toolbar">
  <div class="page-toolbar__primary">
    <Tabs />
  </div>
  <div class="page-toolbar__actions">
    <SiteFilter />
    <SortButton />
    <RefreshButton />
  </div>
</section>
```

**Step 2: Keep current emits and business logic stable**

Do not change public emits or current route/filter behavior for:

- feed tabs
- site filter
- NSFW filter
- sort selection
- refresh
- search-driven list refresh

**Step 3: Apply the same header hierarchy to key content pages**

Each page should use:

- compact page title
- brief supporting text only if it adds context
- primary actions in one predictable area
- toolbar immediately below when needed

**Step 4: Run verification**

```powershell
cd D:\Code\init\squirrel\squirrel-frontend
npm run typecheck
npm run build
```

Manual:

- `/videos/all`
- `/subscribed`
- `/history`

Expected: toolbar behavior and route-driven state remain intact.

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/components/feed/FeedToolbar.vue squirrel-frontend/src/components/feed/TabBar.vue squirrel-frontend/src/components/feed/SortButton.vue squirrel-frontend/src/components/feed/SiteFilter.vue squirrel-frontend/src/components/feed/NsfwFilter.vue squirrel-frontend/src/components/feed/RefreshButton.vue squirrel-frontend/src/views/LatestVideos.vue squirrel-frontend/src/views/Subscribed.vue squirrel-frontend/src/views/History.vue
git commit -m "feat(frontend): unify compact page headers and toolbars"
```

---

## Task 5: Redesign Content Lists For Compact Browsing

**Files:**
- Modify: `squirrel-frontend/src/components/feed/VideoItem.vue`
- Modify: `squirrel-frontend/src/components/feed/VideoList.vue`
- Modify: `squirrel-frontend/src/components/feed/ContextMenu.vue`
- Modify: `squirrel-frontend/src/components/feed/ChannelHeader.vue`
- Modify: `squirrel-frontend/src/styles/components/LatestVideos.css`
- Modify: `squirrel-frontend/src/styles/components/video-card.css`

**Step 1: Tighten the video card/list presentation**

Retain content usefulness, but reduce excess visual weight:

- smaller metadata scale
- reduced card padding
- calmer hover treatment
- less decorative framing
- more efficient spacing between items

**Step 2: Align contextual actions to shared primitives**

Use `DropdownMenu`, compact buttons, and shared badges where applicable.

Do not leave one-off action chips or custom popup behavior unless required by current interactions.

**Step 3: Standardize loading, empty, and error states**

Prefer `Alert`, `Card`, or simple empty-state panels using shared styling rather than route-specific decorative blocks.

**Step 4: Verify**

```powershell
cd D:\Code\init\squirrel\squirrel-frontend
npm run typecheck
npm run build
```

Manual:

- `/videos/all`
- `/videos/unread`
- `/subscription/:id/all`

Check: click-through, refresh, context actions, and density.

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/components/feed/VideoItem.vue squirrel-frontend/src/components/feed/VideoList.vue squirrel-frontend/src/components/feed/ContextMenu.vue squirrel-frontend/src/components/feed/ChannelHeader.vue squirrel-frontend/src/styles/components/LatestVideos.css squirrel-frontend/src/styles/components/video-card.css
git commit -m "feat(frontend): compact content browsing surfaces"
```

---

## Task 6: Unify Playback Page With The Dashboard System

**Files:**
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`
- Modify: `squirrel-frontend/src/components/video-player/themes/variables.css`
- Modify: `squirrel-frontend/src/components/video-player/themes/light.css`
- Modify: `squirrel-frontend/src/components/video-player/themes/dark.css`

**Step 1: Keep player behavior intact**

Do not rewrite:

- playback orchestration
- reporting hooks
- widescreen mode behavior
- subtitle or related-video data flow

**Step 2: Tighten playback-adjacent chrome**

Bring metadata, action rows, related content, and side panels onto the same compact dashboard contract:

- smaller action controls
- shared badges and menus
- clearer metadata hierarchy
- less decorative spacing around non-player surfaces

**Step 3: Align player theming with the app**

Player theme variables should feel related to the shell without making the player look like an admin table.

Keep the player itself visually focused, but simplify surrounding surfaces.

**Step 4: Verify**

```powershell
cd D:\Code\init\squirrel\squirrel-frontend
npm run typecheck
npm run build
```

Manual:

- `/video/:id`
- toggle widescreen
- open overflow actions
- inspect related content panels

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/views/VideoPlay.vue squirrel-frontend/src/components/video-player/themes/variables.css squirrel-frontend/src/components/video-player/themes/light.css squirrel-frontend/src/components/video-player/themes/dark.css
git commit -m "feat(frontend): unify playback dashboard surfaces"
```

---

## Task 7: Convert Operational Pages To A Consistent Dashboard Layout

**Files:**
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`
- Modify: `squirrel-frontend/src/views/Monitoring.vue`
- Modify: `squirrel-frontend/src/views/ScheduledTasks.vue`
- Modify: `squirrel-frontend/src/views/PluginManager.vue`
- Modify: `squirrel-frontend/src/views/LogViewer.vue`
- Modify: `squirrel-frontend/src/views/Settings.vue`

**Step 1: Apply a shared operational page structure**

Each operational page should use:

- compact page header
- predictable action row
- compact cards and tables
- shared status badges
- restrained spacing

**Step 2: Favor tables and structured panels over oversized cards**

Where pages currently use thick wrappers or inconsistent section blocks, rewrite them toward tighter operational surfaces.

**Step 3: Preserve page-specific workflows**

Do not break the existing logic for:

- sync actions and detail panels
- metrics display
- scheduled task controls
- plugin actions
- log filtering and display
- theme and preference settings

**Step 4: Verify**

```powershell
cd D:\Code\init\squirrel\squirrel-frontend
npm run typecheck
npm run build
```

Manual:

- `/sync-center`
- `/monitoring`
- `/scheduled-tasks`
- `/plugins`
- `/logs`
- `/settings`

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/views/SyncCenter.vue squirrel-frontend/src/views/Monitoring.vue squirrel-frontend/src/views/ScheduledTasks.vue squirrel-frontend/src/views/PluginManager.vue squirrel-frontend/src/views/LogViewer.vue squirrel-frontend/src/views/Settings.vue
git commit -m "feat(frontend): compact operational dashboard pages"
```

---

## Task 8: Simplify Auth Surfaces

**Files:**
- Modify: `squirrel-frontend/src/views/Login.vue`
- Modify: `squirrel-frontend/src/views/Register.vue`
- Modify: `squirrel-frontend/src/styles/views/auth-entry.css`

**Step 1: Reduce auth-page visual separation**

Keep brand identity, but align auth with the main app:

- smaller panel sizing
- tighter form fields
- less decorative hero treatment
- restrained supporting copy

**Step 2: Use shared primitives consistently**

Ensure `Card`, `Input`, `Button`, `Alert`, and `Label` drive the form contract with the same compact sizing used in the main shell.

**Step 3: Preserve auth behavior**

Do not regress:

- validation behavior
- loading states
- login/register routing
- error rendering

**Step 4: Verify**

```powershell
cd D:\Code\init\squirrel\squirrel-frontend
npm run typecheck
npm run build
```

Manual:

- `/login`
- `/register`

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/views/Login.vue squirrel-frontend/src/views/Register.vue squirrel-frontend/src/styles/views/auth-entry.css
git commit -m "feat(frontend): simplify compact auth surfaces"
```

---

## Task 9: Final Polish And Regression Pass

**Files:**
- Modify: only files touched by final polish findings

**Step 1: Run full verification**

```powershell
cd D:\Code\init\squirrel\squirrel-frontend
npm run typecheck
npm run build
```

Expected: both commands pass.

**Step 2: Manual walkthrough**

Run:

```powershell
npm run dev
```

Check:

- `/videos/all`
- `/subscribed`
- `/history`
- `/video/:id`
- `/sync-center`
- `/monitoring`
- `/settings`
- `/login`
- `/register`

Review:

- compact density
- header consistency
- sidebar and mobile nav behavior
- dialog/dropdown layering
- table/list readability
- content-page browsing efficiency

**Step 3: Make minimal fixes only**

Limit changes to:

- spacing regressions
- unreadable density issues
- inconsistent component sizing
- broken route-specific layouts

No unrelated refactor.

**Step 4: Commit**

```powershell
git add -A
git commit -m "fix(frontend): polish compact shadcn dashboard redesign"
```
